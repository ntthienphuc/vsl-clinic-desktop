"""Reject mixed Electron/backend metadata before building a new release."""
import ast
import json
from pathlib import Path


def test_backend_and_desktop_release_version_match():
    root=Path(__file__).resolve().parents[1]
    desktop=json.loads((root/'package.json').read_text('utf8'))['version']
    tree=ast.parse((root/'backend/app.py').read_text('utf8'))
    backend=next(ast.literal_eval(node.value) for node in tree.body
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='APP_VERSION' for t in node.targets))
    assert backend==desktop
