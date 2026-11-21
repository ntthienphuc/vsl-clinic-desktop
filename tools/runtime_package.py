"""Package inference runtimes without C++ SDK files; original runtimes stay intact."""
import hashlib
import json
from pathlib import Path


def development_file(relative: Path) -> bool:
    name = relative.as_posix().lower()
    return (name.startswith('lib/site-packages/torch/include/')
            or name.startswith('lib/site-packages/torch/lib/') and relative.suffix.lower() == '.lib')


def runtime_manifest(source: Path) -> dict:
    path = source / 'RUNTIME_MANIFEST.json'
    original = json.loads(path.read_text('utf8'))
    removed = [row for row in original['files'] if development_file(Path(row['path']))]
    return {**original,
            'files': [row for row in original['files'] if not development_file(Path(row['path']))],
            'packaging': {'policy': 'inference-without-cpp-sdk-v1',
                          'source_manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'omitted_files': len(removed), 'omitted_bytes': sum(row['bytes'] for row in removed),
                          'scope': 'Only Torch C++ headers and static/import .lib files omitted. Python, DLLs, weights and licenses preserved.'}}


def stage_runtime(source: Path, destination: Path, stage_tree):
    stage_tree(source, destination, skip=lambda p: development_file(p.relative_to(source)) or p.name == 'RUNTIME_MANIFEST.json')
    path = destination / 'RUNTIME_MANIFEST.json'
    # No mutation of the full source runtime or an old release's NTFS links.
    path.unlink(missing_ok=True)
    path.write_text(json.dumps(runtime_manifest(source), indent=2), 'utf8')
