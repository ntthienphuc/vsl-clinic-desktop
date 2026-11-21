"""Stage a separate CPU-only Python runtime; never mutate the CUDA baseline."""
import hashlib
import json
import os
from pathlib import Path
import shutil
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'build/multimodal-runtime'
destination=ROOT/'build/multimodal-runtime-cpu'
wheel=ROOT/'build/cpu-wheel/torch-2.6.0+cpu-cp311-cp311-win_amd64.whl'
if destination.exists():
    raise RuntimeError('CPU candidate exists; inspect it before replacing anything')
destination.mkdir()
excluded={'torch','torchgen','functorch','torchvision','torchaudio'}
for file in source.rglob('*'):
    if not file.is_file() or '__pycache__' in file.parts or file.name=='RUNTIME_MANIFEST.json':
        continue
    relative=file.relative_to(source)
    if any(part==name or part.startswith(name+'-') for part in relative.parts for name in excluded):
        continue
    target=destination/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if file.suffix.lower() in {'.dll','.pyd','.exe','.lib'}:
        os.link(file,target)
    else:
        shutil.copy2(file,target)
with ZipFile(wheel) as archive:
    for entry in archive.infolist():
        target=(destination/'Lib/site-packages'/entry.filename).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError('Wheel member outside target')
        if entry.is_dir():
            target.mkdir(parents=True,exist_ok=True)
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(entry) as src,target.open('wb') as dst:
                shutil.copyfileobj(src,dst)
def digest(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
files=[dict(path=p.relative_to(destination).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
       for p in sorted(destination.rglob('*')) if p.is_file()]
assert not any(p.name=='torch_cuda.dll' for p in destination.rglob('*.dll'))
report=dict(schema='clinic-mm100-python-runtime-v1',python='3.11.9',torch='2.6.0+cpu',
            source_wheel_url='https://download.pytorch.org/whl/cpu',source_wheel_sha256=digest(wheel),
            runtime_resolution='python311._pth; fully relative; no site import',files=files)
(destination/'RUNTIME_MANIFEST.json').write_text(json.dumps(report,indent=2),'utf8')
print(json.dumps(dict(files=len(files),bytes=sum(r['bytes'] for r in files),wheel_sha256=report['source_wheel_sha256'])))
