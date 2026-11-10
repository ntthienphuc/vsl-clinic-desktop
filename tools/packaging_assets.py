"""Select weights declared by the active deployment; retain research files locally."""
import json
from pathlib import Path


def inactive_multimodal_weights(assets: Path) -> set[Path]:
    root = assets / 'multimodal100'
    deployment_path = root / 'DEPLOYMENT.json'
    if not deployment_path.is_file():
        return set()
    deployment = json.loads(deployment_path.read_text('utf8'))
    if deployment.get('profile') != 'slgcn-avhubert':
        return set()
    manifest = json.loads((root / 'models/MODEL_MANIFEST.json').read_text('utf8'))
    active = set(deployment['foundations'].values())
    active.update(head['checkpoint'] for head in manifest['heads'].values())
    declared = {row['path'] for row in deployment['files']}
    for relative in active:
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root.resolve()) or relative not in declared:
            raise ValueError('Active multimodal weight is not declared: ' + relative)
    inactive = {p for p in root.rglob('*') if p.is_file()
                and p.suffix.lower() in {'.pt', '.safetensors'}
                and p.relative_to(root).as_posix() not in active}
    stale = [p.relative_to(root).as_posix() for p in inactive
             if p.relative_to(root).as_posix() in declared]
    if stale:
        raise ValueError('Deployment still requires inactive historical weights: ' + ', '.join(stale))
    return inactive
