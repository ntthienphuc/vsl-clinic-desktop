"""Frozen pretrained encoders with per-clip source/pixel/feature receipts."""
import os,ast,copy,hashlib,importlib.util,json,sys,time,argparse
from pathlib import Path
from typing import Optional
os.environ.setdefault('OMP_NUM_THREADS','2')
import numpy as np,torch
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(p,x):
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
    for attempt in range(40):
        try:tmp.replace(p);return
        except PermissionError:
            if attempt==39:raise
            time.sleep(.1)
def build(role,device):
    if role=='lip':
        source=ASSETS/'auto_avsr';checkpoint=ASSETS/'vlr_pretrained.pt'
        sys.path.insert(0,str(source))
        from espnet.nets.pytorch_backend.e2e_asr_conformer import E2E
        state=torch.load(checkpoint,map_location='cpu',weights_only=True,mmap=True)
        model=E2E(state['ctc.ctc_lo.weight'].shape[0],'video',ctc_weight=.1)
        model.load_state_dict(state,strict=True);del state
        model.eval().requires_grad_(False).to(device)
        def forward(data):
            frames=data['mouth'];assert frames.dtype==np.uint8 and frames.shape[1:]==(96,96)
            x=torch.from_numpy(frames[:,4:92,4:92].copy()).float().to(device)
            x=((x/255-.421)/.165)[None,:,None]
            return model.encoder(model.proj_encoder(model.frontend(x)),None)[0][0].float().cpu().numpy()
        return forward,dict(checkpoint_sha256=sha(checkpoint),sha256=sha(checkpoint),encoder_dimension=768,strict_load=True,state_field='raw',pixel_format='uint8 grayscale 25fps 96x96; center88; (x/255-.421)/.165',source_e2e_sha256=sha(source/'espnet/nets/pytorch_backend/e2e_asr_conformer.py'))
    from safetensors.torch import load_file
    source=ASSETS/'spoter_modelling.py';checkpoint=ASSETS/'spoter.safetensors';transforms=ASSETS/'sign_transforms.py'
    tree=ast.parse(source.read_text(encoding='utf8'))
    nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in ['SPOTER','SPOTERTransformerDecoderLayer']]
    scope=dict(torch=torch,nn=torch.nn,copy=copy,Optional=Optional)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
    weights={k.removeprefix('model.'):v for k,v in load_file(str(checkpoint)).items()}
    model=scope['SPOTER'](weights['linear_class.weight'].shape[0],108)
    model.load_state_dict(weights,strict=True);model.eval().requires_grad_(False)
    spec=importlib.util.spec_from_file_location('historical_pose_tools',transforms)
    tr=importlib.util.module_from_spec(spec);sys.modules[spec.name]=tr;spec.loader.exec_module(tr)
    output=[];model.linear_class.register_forward_pre_hook(lambda m,x:output.append(x[0].detach()))
    def forward(data):
        pts=data['keypoints']
        if len(pts)>70:pts=pts[np.linspace(0,len(pts)-1,70).round().astype(int)]
        x=tr.make_spoter_input(pts,70);assert x.shape==(70,54,2) and torch.isfinite(x).all()
        output.clear();model(x[None]);return output[0].reshape(1,108).numpy()
    return forward,dict(checkpoint_sha256=sha(checkpoint),strict_load=True,feature_dimension=108,temporal_tokens=1,model_source_sha256=sha(source),transforms_sha256=sha(transforms),legacy_hand_order_retained=True,pose_input='75 landmarks -> legacy54x2; whole-clip uniform sampling >70, repeat pad shorter')

def main(a):
    global ASSETS
    ASSETS=a.assets
    if a.vendor:sys.path.insert(0,str(a.vendor))
    torch.set_num_threads(2)
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cuda.matmul.allow_tf32=False
    rows=json.loads(a.manifest.read_text(encoding='utf8'))
    assert len(rows)==len({r['clip_id'] for r in rows})
    a.output.mkdir(parents=True,exist_ok=True)
    infer,meta=build(a.role,a.device)
    meta.update(cudnn_tf32=False,matmul_tf32=False,precision_policy='uniform_fp32_all_population',role=a.role,device=a.device,torch_version=str(torch.__version__),processor_sha256=sha(Path(__file__)),manifest_sha256=sha(a.manifest),expected_clips=len(rows))
    identity={k:meta[k] for k in ['role','checkpoint_sha256','processor_sha256','manifest_sha256']}
    identity_path=a.output/'identity.json'
    if identity_path.exists():assert json.loads(identity_path.read_text(encoding='utf8'))==identity,'Resume identity changed'
    else:
        assert not list(a.output.glob('*.npy')),'Outputs without an identity receipt'
        atomic(identity_path,identity)
    records=[];start=time.monotonic()
    for r in rows:
        cid=r['clip_id'];pix=a.pixels/(cid+'.npz');info=json.loads(pix.with_suffix('.json').read_text(encoding='utf8'))
        psha=sha(pix)
        assert info['source_sha256']==r['sha256'] and info['pixel_file_sha256']==psha
        assert info['status'].startswith('PASS'),(cid,'QA not accepted')
        dest=a.output/(cid+'.npy');rec=a.output/(cid+'.record.json')
        if dest.exists() or rec.exists():
            assert dest.exists() and rec.exists(),('partial output requires review',cid)
            item=json.loads(rec.read_text(encoding='utf8'));assert item['pixel_sha256']==psha and item['sha256']==sha(dest)
        else:
            begin=time.monotonic()
            with np.load(pix,allow_pickle=False) as data,torch.inference_mode():
                assert float(data['fps'])==25.
                feat=infer(data)
            assert feat.ndim==2 and feat.shape[1]==(768 if a.role=='lip' else 108) and np.isfinite(feat).all()
            tmp=dest.with_suffix('.npy.tmp')
            with tmp.open('wb') as f:np.save(f,feat)
            tmp.replace(dest)
            item=dict(clip_id=cid,shape=list(feat.shape),sha256=sha(dest),pixel_sha256=psha,source_sha256=r['sha256'],seconds=time.monotonic()-begin)
            atomic(rec,item)
        records.append(item)
        if len(records)%25==0:
            atomic(a.output/'receipt.json',dict(meta,records=records,clips=len(records),status='RUNNING_PARTIAL'))
            print(a.role,len(records),len(rows),round(time.monotonic()-start,1),flush=True)
    atomic(a.output/'receipt.json',dict(meta,records=records,clips=len(records),status='COMPLETE_FROZEN_FEATURES',elapsed_seconds=time.monotonic()-start))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ['assets','manifest','pixels','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--vendor',type=Path);p.add_argument('--role',choices=['sign','lip'],required=True);p.add_argument('--device',default='cpu');main(p.parse_args())
