"""Read-only eager adapter to the archived AV-HuBERT encoder definitions.

No Fairseq trainer/task registry is imported. The original tensor forward
definitions are compiled unchanged from the archived source; registration is
omitted. Use only with strict tensor loading and paired cached-feature replay.
"""
import ast
import copy
import dataclasses
import hashlib
import json
import logging
import math
import sys
import types
import typing
import uuid
from pathlib import Path
import numpy as np
import torch
from torch import nn, Tensor
from torch.nn import Parameter
from torch.nn import functional as F


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024**2),b''):h.update(chunk)
    return h.hexdigest()


def definitions(path,scope,names=None,strip_model_registration=False,drop_activation_import=False):
    tree=ast.parse(Path(path).read_text('utf8'))
    nodes=[]
    for node in tree.body:
        if not isinstance(node,(ast.FunctionDef,ast.ClassDef)):continue
        if names is not None and node.name not in names:continue
        if strip_model_registration and node.name=='AVHubertModel':node.decorator_list=[]
        if drop_activation_import and node.name=='get_activation_fn':
            node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
        nodes.append(node)
    if names is not None:assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),scope)


def load(source,asset,preset_json,device='cuda'):
    source,asset=Path(source),Path(asset)
    proof=json.loads((asset/'EXPORT_RECEIPT.json').read_text('utf8'))
    assert digest(asset/'encoder_state.pt')==proof['encoder_sha256']
    assert digest(asset/'saved_config.json')==proof['saved_config_sha256']
    module=types.ModuleType('_clinic_avh_inference_definitions')
    sys.modules[module.__name__]=module
    scope=module.__dict__
    scope.update(torch=torch,nn=nn,Tensor=Tensor,Parameter=Parameter,F=F,np=np,math=math,
        uuid=uuid,deepcopy=copy.deepcopy,dataclass=dataclasses.dataclass,field=dataclasses.field,
        logger=logging.getLogger('clinic.avh'),FairseqDataclass=object,BaseFairseqModel=nn.Module,
        AVHubertPretrainingConfig=object,AVHubertPretrainingTask=object,Dictionary=list,
        II=lambda x:x,ChoiceEnum=lambda x:str,EXTRACTOR_MODE_CHOICES=str,MASKING_DISTRIBUTION_CHOICES=str,
        LayerNorm=nn.LayerNorm,OrderedDict=__import__('collections').OrderedDict)
    scope.update({name:getattr(typing,name) for name in ['Dict','List','Optional','Tuple','Callable']})
    fairseq=source/'fairseq/fairseq'
    for file,names in [
        ('incremental_decoding_utils.py',{'FairseqIncrementalState','with_incremental_state'}),
        ('modules/gelu.py',{'gelu','gelu_accurate'}),
        ('modules/quant_noise.py',{'quant_noise'}),
        ('modules/fairseq_dropout.py',{'FairseqDropout'}),
        ('modules/grad_multiply.py',{'GradMultiply'}),
        ('modules/same_pad.py',{'SamePad'}),
        ('modules/transpose_last.py',{'TransposeLast'})]:definitions(fairseq/file,scope,names)
    definitions(fairseq/'utils.py',scope,{'get_available_activation_fns','get_activation_fn','softmax','is_xla_tensor','index_put'},drop_activation_import=True)
    scope['utils']=types.SimpleNamespace(**{name:scope[name] for name in ['get_available_activation_fns','get_activation_fn','softmax','is_xla_tensor','index_put']})
    definitions(fairseq/'modules/multihead_attention.py',scope,{'MultiheadAttention'})
    definitions(fairseq/'modules/transformer_sentence_encoder.py',scope,{'init_bert_params'})
    definitions(fairseq/'models/wav2vec/wav2vec2.py',scope,{'TransformerEncoder','TransformerSentenceEncoderLayer'})
    definitions(source/'avhubert/resnet.py',scope)
    definitions(source/'avhubert/hubert.py',scope,{'AVHubertConfig','SubModel','AVHubertModel'},strip_model_registration=True)
    cfg=scope['AVHubertConfig']()
    preset=json.loads(Path(preset_json).read_text('utf8'))
    assert preset.pop('wav_input') is False
    for k,v in preset.items():
        if k!='_name':setattr(cfg,k,v)
    cfg.label_rate=25;cfg.input_modality='image'
    fine=json.loads((asset/'saved_config.json').read_text('utf8'))['model']
    assert Path(fine['w2v_path']).name=='large_vox_iter5.pt'
    for key in ['dropout','activation_dropout','dropout_input','attention_dropout','feature_grad_mult']:
        if key in fine:setattr(cfg,key,fine[key])
    cfg.encoder_layerdrop=fine['layerdrop']
    model=scope['AVHubertModel'](cfg,types.SimpleNamespace(sample_rate=25,normalize=True),[range(2004)])
    model.remove_pretraining_modules()
    state=torch.load(asset/'encoder_state.pt',map_location='cpu',weights_only=True,mmap=True)
    assert len(state)==536 and tuple(state['label_embs_concat'].shape)==(2004,256)
    model.load_state_dict(state,strict=True)
    del state
    model.eval().requires_grad_(False).to(device)
    @torch.inference_mode()
    def infer(mouth):
        assert mouth.dtype==np.uint8 and mouth.shape[1:]==(96,96)
        x=torch.from_numpy(mouth[:,4:92,4:92].copy()).float().to(device)
        x=((x/255-.421)/.165)[None,None]
        return model.extract_finetune({'audio':None,'video':x},padding_mask=None,mask=False)[0][0].float().cpu().numpy()
    return model,infer,dict(strict_load_keys=536,encoder_sha256=proof['encoder_sha256'],precision='fp32_tf32_off',
        adaptation='Original eager inference definitions; omit task/training registries only. Numerical replay required.',
        parameter_count=sum(p.numel() for p in model.parameters()))
