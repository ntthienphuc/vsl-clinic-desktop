# Build with .venv/Scripts/python -m PyInstaller tools/clinic-engine.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

root = Path(SPECPATH).parent
datas = collect_data_files("mediapipe", include_py_files=False)
binaries = collect_dynamic_libs("mediapipe") + collect_dynamic_libs("onnxruntime")
hidden = collect_submodules("mediapipe", filter=lambda name: not name.endswith("_test"))
hidden += ["backend.app", "pipelines.slgcn_onnx_inference", "pipelines.spoter_onnx_inference", "data.utils", "utils.constants"]
for package in ["faster_whisper", "ctranslate2", "tokenizers", "av"]:
    datas += collect_data_files(package, include_py_files=False)
    binaries += collect_dynamic_libs(package)
    hidden += collect_submodules(package)
for distribution in ["faster-whisper", "ctranslate2", "tokenizers", "av", "huggingface-hub", "webrtcvad-wheels"]:
    datas += copy_metadata(distribution)
hidden += ["webrtcvad", "_webrtcvad"]
analysis = Analysis(
    [str(root / "backend/main.py")],
    pathex=[str(root), str(root / "backend/legacy")],
    hookspath=[str(root / "tools/hooks")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=["jax", "jaxlib", "tensorflow", "torch", "IPython", "notebook", "pytest"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ClinicEngine",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)
bundle = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    name="ClinicEngine",
    strip=False,
    upx=False,
)
