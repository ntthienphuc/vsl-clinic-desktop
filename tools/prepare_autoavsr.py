"""Stage the fixed VSL100 R3 SL-GCN/VLR deployment from pinned local inputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import torch

ROOT = Path(__file__).resolve().parents[1] / 'assets/multimodal100'
CONTRACT = 'vsl100-r3-slgcn-autoavsr-xattn-f01-s17-clinic-v1'
RUN = 'primary__r3_loso_01__slgcn_replication_fp32__vlr_uniform_fp32__cross_attention__s17'


def read(path):
    return json.loads(path.read_text('utf8'))


def write(path, value):
    target = path.with_suffix('.tmp')
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', 'utf8')
    target.replace(path)


def record(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=digest, bytes=path.stat().st_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    source = ROOT / 'models/foundations/vlr_pretrained.pt'
    origin = record(source)
    if origin['sha256'] != 'b38177ae98f1f3cbea1a4c183c2bca804cf0a576e99abd23aab85ae56f413280':
        raise ValueError('Unexpected VLR foundation')
    staged = ROOT / 'r3/vlr'
    staged.mkdir(exist_ok=True)
    weights = torch.load(source, weights_only=True, map_location='cpu', mmap=True)
    visual = {k:v for k,v in weights.items() if k.startswith(('frontend.', 'encoder.', 'proj_encoder.'))}
    target = staged / 'visual.pt'
    with target.with_suffix('.tmp').open('wb') as stream:
        torch.save(visual, stream)
    target.with_suffix('.tmp').replace(target)
    run = args.results / RUN
    hashes = read(run / 'ARTIFACT_HASHES.json')
    if hashes['best.pt'] != 'a29e4a4a0e34d4fe5dba733c375171ce5fbb2cf8e303edca50f93e903d540ccb':
        raise ValueError('Unexpected R3 head')
    for name in ('best.pt','config_and_provenance.json'):
        dest = staged / name
        shutil.copyfile(run / name, dest.with_suffix('.tmp'))
        if record(dest.with_suffix('.tmp'))['sha256'] != hashes[name]:
            raise ValueError(name)
        dest.with_suffix('.tmp').replace(dest)
    paths = [ROOT / f for f in ('models/classes.json','models/assets/mean_face.npy','label_mapping.json',
        'server/engine.py','server/__init__.py','server/preprocess.py','server/segmentation.py','server/vendor/crop_geometry.py','server/vendor/legacy_arm_utils.py',
        'server/vendor/model.py','server/vendor/legacy_fusion.py','r3/code/sign_backbones.py','r3/vendor/pose_transforms.py',
        'r3/assets/slgcn/model.safetensors')]
    for directory in ['r3/vendor/slgcn','r3/deps','server/vendor/auto_avsr','r3/vlr']:
        paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    rows=[record(p) for p in sorted(set(paths))]
    by_path={r['path']:r for r in rows}
    foundations={k:by_path[v] for k,v in [('slgcn.safetensors','r3/assets/slgcn/model.safetensors'),('vlr_visual.pt','r3/vlr/visual.pt')]}
    manifest=dict(contract=CONTRACT,profile='slgcn-autoavsr',fold='r3_loso_01',seed=17,label_count=100,
        label_sha256=by_path['models/classes.json']['sha256'], foundations=foundations,
        feature_contract=dict(sign_dim=256,lip_dim=768,lip_max_tokens=96),source_vlr=origin,
        heads=dict(fusion=dict(run_id=RUN,checkpoint='r3/vlr/best.pt',sha256=hashes['best.pt'],
            config_sha256=hashes['config_and_provenance.json'])))
    mp=ROOT/'models/MODEL_MANIFEST.json'
    write(mp,manifest)
    write(ROOT/'DEPLOYMENT.json',dict(schema='clinic-mm100-deployment-v1',contract=CONTRACT,profile=manifest['profile'],
        foundations={k:v['path'] for k,v in foundations.items()},files=rows+[record(mp)],
        inference=dict(device='auto',cpu_precision='ffn-int8',gpu_precision='fp32')))
    print('Visual tensors:', len(visual), 'bytes:', target.stat().st_size, 'head:', hashes['best.pt'])

if __name__ == '__main__':
    main()
