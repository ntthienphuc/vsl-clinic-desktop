"""Derive a separate runnable CPU experiment from an audited standard build.

The regular package, original weights, and installer are never changed.
Only the private runtime and AV-HuBERT precision differ; labels/head/UX stay equal.
"""
import argparse
import json
from pathlib import Path
import shutil

from audit_portable import audit
from package_multimodal import digest, stage_tree

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT.parent / 'Organization/VoicePreviewCPU_2026-11-10'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suffix', default='', help='Unique suffix for a preserved candidate (letters/digits/hyphens).')
    args = parser.parse_args()
    if args.suffix and not all(c.isascii() and (c.isalnum() or c == '-') for c in args.suffix):
        raise ValueError('Candidate suffix must use ASCII letters, digits or hyphens')
    suffix = ('-' + args.suffix) if args.suffix else ''
    config = json.loads((ROOT / 'package.json').read_text('utf8'))
    source = (ROOT / config['build']['directories']['output'] / 'win-unpacked').resolve()
    destination = ROOT.parent / 'Experiments' / ('CPU-INT8-' + config['version'] + suffix)
    if destination.exists():
        raise RuntimeError('CPU experiment already exists; inspect before replacing it')
    inventory = audit(source)
    if not inventory['passed']:
        raise RuntimeError('Standard package must pass its inventory first')
    quant_source = EVIDENCE / 'cpu-transformer-int8'
    quant_manifest = json.loads((quant_source / 'QUANTIZED_ENCODER.json').read_text('utf8'))
    quant_weight = quant_source / quant_manifest['file']
    if digest(quant_weight) != quant_manifest['sha256']:
        raise RuntimeError('Measured quantized artifact changed')
    old_encoder = Path('resources/assets/multimodal100/r3/assets/avhubert/encoder_state.pt')
    runtime = source / 'resources/multimodal-runtime'
    stage_tree(source, destination, skip=lambda p: p.is_relative_to(runtime)
               or p.relative_to(source) in {old_encoder, Path('BUILD_RECEIPT.json')})
    stage_tree(ROOT / 'build/multimodal-runtime-cpu', destination / 'resources/multimodal-runtime')
    assets = destination / 'resources/assets/multimodal100'
    quant_dir = assets / 'r3/assets/avhubert/int8'
    quant_dir.mkdir(parents=True)
    for file in (quant_source / 'QUANTIZED_ENCODER.json', quant_weight):
        shutil.copy2(file, quant_dir / file.name)
    manifest_path = assets / 'models/MODEL_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text('utf8'))
    original = manifest['foundations'].pop('avhubert_encoder.pt')
    assert original['sha256'] == quant_manifest['source_sha256']
    quant_relative = (quant_dir / quant_weight.name).relative_to(assets).as_posix()
    manifest['foundations']['avhubert_transformer_int8.pt'] = dict(
        path=quant_relative, sha256=quant_manifest['sha256'], bytes=quant_weight.stat().st_size,
        original_fp32=original)
    manifest['precision'] = 'transformer_dynamic_int8_cpu'
    manifest['source_manifest_sha256'] = digest(source / 'resources/assets/multimodal100/models/MODEL_MANIFEST.json')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), 'utf8')
    deployment_path = assets / 'DEPLOYMENT.json'
    deployment = json.loads(deployment_path.read_text('utf8'))
    old_relative = deployment['foundations'].pop('avhubert_encoder.pt')
    deployment['foundations']['avhubert_transformer_int8.pt'] = quant_relative
    deployment['inference'] = dict(device='cpu', quantized_encoder=(quant_dir / 'QUANTIZED_ENCODER.json').relative_to(assets).as_posix())
    deployment['source_deployment_sha256'] = digest(source / 'resources/assets/multimodal100/DEPLOYMENT.json')
    overrides = {manifest_path.relative_to(assets).as_posix(), quant_relative, deployment['inference']['quantized_encoder']}
    deployment['files'] = [row for row in deployment['files'] if row['path'] != old_relative and row['path'] not in overrides]
    for relative in sorted(overrides):
        path = assets / relative
        deployment['files'].append(dict(path=relative, bytes=path.stat().st_size, sha256=digest(path)))
    deployment_path.write_text(json.dumps(deployment, ensure_ascii=False, indent=2), 'utf8')
    # All unmodified files must be byte-identical to the audited main package.
    changed = {'resources/assets/multimodal100/' + p for p in overrides | {'DEPLOYMENT.json'}}
    records, identical = [], 0
    for path in sorted(destination.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(destination).as_posix()
        checksum = digest(path)
        if relative not in changed and not relative.startswith('resources/multimodal-runtime/'):
            if checksum != digest(source / relative):
                raise RuntimeError('Unexpected CPU candidate difference: ' + relative)
            identical += 1
        records.append(dict(path=relative, bytes=path.stat().st_size, sha256=checksum))
    receipt = json.loads((source / 'BUILD_RECEIPT.json').read_text('utf8'))
    receipt.update(package=str(destination), payload=records, payload_files_verified=len(records),
        scope='Separate experimental CPU INT8 package; same source/EXE/frontend as standard release.',
        derivation=dict(standard_receipt_sha256=digest(source / 'BUILD_RECEIPT.json'),
            identical_files=identical, changed_manifests_and_weights=sorted(changed),
            removed_fp32_weight=old_encoder.as_posix(), original_fp32_sha256=original['sha256'],
            quantized_sha256=quant_manifest['sha256'], runtime='torch2.6.0+cpu'))
    (destination / 'BUILD_RECEIPT.json').write_text(json.dumps(receipt, indent=2), 'utf8')
    result = audit(destination)
    (EVIDENCE / ('CPU_PACKAGE' + suffix + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps(dict(package=str(destination), passed=result['passed'], bytes=result['package_bytes'], files=result['package_files'], identical_files=identical)))
    if not result['passed']:
        raise RuntimeError(result['problems'])


if __name__ == '__main__':
    main()
