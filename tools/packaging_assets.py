"""Select weights declared by the active deployment; retain research files locally."""
import json
from pathlib import Path


def multimodal_runtime(root: Path) -> Path:
    deployment = json.loads((root / 'assets/multimodal100/DEPLOYMENT.json').read_text('utf8'))
    inference = deployment.get('inference', {})
    name = 'multimodal-runtime-cpu' if inference.get('device') == 'cpu' else 'multimodal-runtime'
    return root / 'build' / name


def extra_multimodal_runtimes(root: Path) -> list[tuple[Path, str]]:
    deployment = json.loads((root / 'assets/multimodal100/DEPLOYMENT.json').read_text('utf8'))
    return [(root / 'build/multimodal-runtime-cpu', 'multimodal-runtime-cpu')] if deployment.get('inference', {}).get('device') == 'auto' else []


def inactive_multimodal_weights(assets: Path) -> set[Path]:
    root = assets / 'multimodal100'
    deployment_path = root / 'DEPLOYMENT.json'
    if not deployment_path.is_file():
        return set()
    deployment = json.loads(deployment_path.read_text('utf8'))
    if deployment.get('profile') == 'slgcn-autoavsr':
        active = {root / row['path'] for row in deployment['files']} | {deployment_path}
        return {p for p in root.rglob('*') if p.is_file() and p not in active}
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


def inactive_package_assets(assets: Path) -> set[Path]:
    inactive = inactive_multimodal_weights(assets)
    # The original JSON retains provenance/DTW diagnostics in the source tree.
    # Ship only active compact geometry; never duplicate both formats.
    motion_bank = assets / 'motions'
    motion_manifest = motion_bank / 'manifest.json'
    if motion_manifest.is_file():
        for entry in json.loads(motion_manifest.read_text('utf8'))['entries']:
            if entry['path'].endswith('.vslm'):
                packed = motion_bank / (entry['id'] + '.vslm')
                if not packed.is_file(): raise ValueError('Missing packed motion: ' + entry['id'])
                inactive.add(motion_bank / (entry['id'] + '.json'))
    # Keep previous pronunciations in source history, but ship only manifest
    # references. This also prevents audition candidates entering a release.
    for folder in ('avatar-voice', 'patient-voice'):
        bank = assets / folder
        manifest = bank / 'manifest.json'
        if not manifest.is_file():
            continue
        entries = json.loads(manifest.read_text('utf8'))['entries']
        active = {row['file'] for row in entries}
        active.update(row['warning']['file'] for row in entries if row.get('warning'))
        inactive.update(p for p in bank.glob('*.wav') if p.name not in active)
    return inactive
