"""The Windows wheel exposes webrtcvad but has different distribution metadata."""
from PyInstaller.utils.hooks import copy_metadata

datas = copy_metadata("webrtcvad-wheels")
hiddenimports = ["_webrtcvad"]
