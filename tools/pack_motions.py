"""Build compact runtime geometry while preserving original research JSON.

Int16 error is bounded and measured on every point. No recognizer weights or
input preprocessing change. Manifest publication is explicit (--activate).
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def pack(source: Path, target: Path):
    raw=source.read_bytes(); motion=json.loads(raw)
    xyz=np.asarray(motion['frames'],dtype=np.float64)
    if xyz.ndim!=3 or xyz.shape[1:]!=(75,3) or not np.isfinite(xyz).all(): raise ValueError('Invalid geometry')
    scale=min(10000.0, 32760.0/max(float(np.max(np.abs(xyz))),1))
    quantized=np.rint(xyz*scale).astype('<i2')
    decoded=quantized.astype(float)/scale
    error=float(np.max(np.abs(decoded-xyz)))
    if error>0.0001: raise ValueError(f'Excess motion quantization error {error}')
    header={k:motion[k] for k in ('id','label','duration_ms','source_hashes','coordinates','joint_layout')}
    header.update(schema='clinic-motion-packed-v1',frame_count=len(xyz),joint_count=75,scale=scale,original_sha256=hashlib.sha256(raw).hexdigest())
    encoded=json.dumps(header,ensure_ascii=False,separators=(',',':')).encode('utf8')
    payload=b'VSLM1\0\0\0'+struct.pack('<I',len(encoded))+encoded+quantized.tobytes()
    temporary=target.with_suffix('.tmp');temporary.write_bytes(payload);temporary.replace(target)
    return {'id':motion['id'],'original_bytes':len(raw),'packed_bytes':len(payload),'maximum_point_error_shoulder_units':error,'sha256':hashlib.sha256(payload).hexdigest(),'source_sha256':header['original_sha256']}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--activate',action='store_true');args=parser.parse_args()
    folder=ROOT/'assets/motions';manifest=json.loads((folder/'manifest.json').read_text('utf8'));rows=[]
    for entry in manifest['entries']:
        target=folder/(entry['id']+'.vslm');row=pack(folder/(entry['id']+'.json'),target);rows.append(row)
        if args.activate: entry.update(path='/assets/motions/'+target.name,sha256=row['sha256'],original_sha256=row['source_sha256'])
    report={'schema':'clinic-motion-storage-evidence-v1','words':len(rows),'original_bytes':sum(r['original_bytes'] for r in rows),'packed_bytes':sum(r['packed_bytes'] for r in rows),'maximum_point_error_shoulder_units':max(r['maximum_point_error_shoulder_units'] for r in rows),'activated':args.activate,'entries':rows}
    if args.activate:
        manifest['runtime_format']='VSLM1 int16, adaptive scale, 75 xyz points per frame'
        (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf8')
    (ROOT/'research/motion-storage-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='entries'}))

if __name__=='__main__':main()
