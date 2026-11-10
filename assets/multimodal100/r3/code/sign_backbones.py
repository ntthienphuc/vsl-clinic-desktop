"""Strict foundation loaders with the archived pose-format preprocessing contract."""
from pathlib import Path
import sys,json,hashlib,ast,importlib.util
import numpy as np
import torch

JOINTS=[0,11,12,13,14,15,16,33,37,38,41,42,45,46,49,50,53,54,58,59,62,63,66,67,70,71,74]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_transform(source):
    from pose_format import Pose
    scope={'np':np,'torch':torch,'Pose':Pose}
    tree=ast.parse(source.read_text(encoding='utf8'))
    names={'SLGCNPad','SLGCNMotionStream','SLGCNBoneStream','SLGCNNormalize','NumPyToTensor'}
    nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in names]
    assert len(nodes)==len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
    return scope

def build(root,variant,device):
    from safetensors.torch import load_file
    from pose_format import Pose
    from pose_format.numpy import NumPyPoseBody
    sys.path.insert(0,str(root/'vendor'))
    cfg=json.loads((root/'vendor'/variant/'config.json').read_text(encoding='utf8'))
    weights_path=root/'assets'/variant/'model.safetensors'
    raw=load_file(str(weights_path))
    assert all(k.startswith('model.') for k in raw)
    weights={k[len('model.'):]:v for k,v in raw.items()}
    classes=int(weights['fc.weight'].shape[0])
    assert classes==400
    keys=['num_points','num_people','groups','block_size','in_channels','labeling_mode']
    if variant=='slgcn':
        from slgcn.decouple_gcn_attn import Model
    else:
        from dsta.fstgan import Model
        keys+=['graph','inner_dim','drop_layers','depth','s_num_heads','window_size']
    model=Model(num_classes=classes,**{k:cfg[k] for k in keys})
    model.load_state_dict(weights,strict=True)
    model.eval().requires_grad_(False).to(device)
    transforms_path=root/'vendor/pose_transforms.py'
    tr=load_transform(transforms_path)
    captured=[]
    model.fc.register_forward_pre_hook(lambda module,args:captured.append(args[0].detach()))
    def prepare(points):
        assert points.ndim==3 and points.shape[1:]==(75,4) and np.isfinite(points).all()
        pose=Pose(None,NumPyPoseBody(25.,points[:,None,:,:3].copy(),points[:,None,:,3].copy()))
        pose.normalize_distribution()
        selected=np.zeros((len(points),27,3),dtype=pose.body.data.dtype)
        for j,idx in enumerate(JOINTS):
            selected[:,j,:2]=pose.body.data[:,0,idx,:2].data
            selected[:,j,2]=pose.body.confidence[:,0,idx]
        assert len(selected)<=cfg['num_frames'],'No silent temporal truncation'
        data=tr['SLGCNPad'](cfg['num_frames'])(selected)
        if cfg['bone_stream']:
            data=tr['SLGCNBoneStream']()(data)
        if cfg['motion_stream']:
            data=tr['SLGCNMotionStream']()(data)
        data=tr['SLGCNNormalize'](cfg['is_vector'])(data)
        assert np.isfinite(data).all()
        return torch.from_numpy(data).float()
    def forward(batch):
        captured.clear()
        keep=torch.tensor([1.]) if variant=='dsta' else 1.
        model(batch.to(device),keep_prob=keep)
        assert len(captured)==1
        output=captured[0].float().cpu().numpy()
        assert output.shape==(len(batch),model.fc.in_features) and np.isfinite(output).all()
        return output[:,None,:]
    info=dict(variant=variant,checkpoint_sha256=sha(weights_path),strict_load=True,loaded_keys=len(weights),foundation_classes=classes,feature_dimension=int(model.fc.in_features),config=cfg,transform_sha256=sha(transforms_path),normalization='pose-format0.15.0 NumPyPoseBody confidence==0 mask; Pose.normalize_distribution default axes(0,1); archived 27-joint/bone/motion/pad/normalize transforms',raw_input='75 MediaPipe landmarks from verified pixels_v2; no new detection or crop',device=str(device))
    return prepare,forward,info
