# Windows package contents

[← Project overview](../README.md) · [Source setup](GIT_SETUP.md) · [Usage guide](USAGE.md)

The 0.3.4 distribution is a **portable folder**, approximately **1.27 GB** uncompressed. Copy the complete `win-unpacked` folder and launch `VSL Clinic.exe`. The EXE alone is not sufficient. There is currently no installation wizard.

## What the end user receives

| Component | Included in the audited portable folder |
| --- | --- |
| Desktop runtime | Electron, Chromium, frontend bundles, fonts and audio worklet. |
| Backend runtime | Frozen `ClinicEngine.exe`, Python 3.11 DLL, libraries and native dependencies. |
| Patient-side recognition | SL-GCN ONNX model, **400** contiguous gloss IDs, MediaPipe hand and pose models. |
| Signing avatar | Male `ClinicMale.vrm`, **65** motion files with matching vocabulary entries, join profiles and semantic metadata. |
| Doctor-side language | **58** controlled templates plus reviewed aliases. |
| Vietnamese speech | **PhoWhisper base INT8** weights, config, tokenizer, vocabulary and preprocessing config. |
| Speech activity | Bundled **Silero VAD v6 ONNX** and runtime. |
| Runtime sample videos | **56 MP4s** under `resources/assets/samples`. |
| Patient practice/demo kit | **37 MP4 files** under `demo`, including numbered practice videos and concatenated rehearsal clips. This count includes repeated source clips. |
| Notices and provenance | Bundled notices, model metadata, manifests, demo documentation and build receipt. |

No separate Python, Node, PhoWhisper or model download is part of the normal end-user launch flow. The speech model is opened from its packaged local directory with `local_files_only=True`.

## What is not in this package

- **A complete 400-word reference-video library.** The recognizer has 400 labels, while the app's selectable runtime sample set contains 56 videos. The inherited 400-entry catalog includes old `/videos/...` metadata URLs; those are not bundled video resources or a current video library endpoint.
- **Raw QIPEDC source videos.** Nine avatar signs were extracted from separate QIPEDC references. Their motion data and provenance are included, but `assets/reference-source` is explicitly excluded from the desktop package.
- **The complete reference/training corpus.** Bank-building metadata can retain source paths as provenance. End-user playback uses baked motion files and does not need those original paths. Rebuilding or expanding the bank requires the original research inputs.
- **Development-only speech fixtures or the Git checkout.** Neither is required to run the packaged app.

The package therefore contains the assets needed by the current **65-sign avatar demo**, not a full 400-sign avatar/video product. This distinction is independent of whether the recognition model can classify 400 labels.

## Verification on 2026-11-01

- **1,990 receipt-listed payload files**, the launcher and `app.asar` matched their recorded SHA-256 hashes.
- All 65 motion files matched the bank manifest; PhoWhisper's six pinned files and Silero's ONNX asset were present.
- The complete folder was copied to a different drive/path containing spaces and tested there.
- The frozen engine started with Python/Node development paths removed, Python environment overrides removed, an empty Hugging Face cache and offline model-loading flags.
- All **93 packaged MP4 files** decoded fully. The packaged detector/recognizer returned **Đau** for its sample clip.
- PhoWhisper and Silero loaded and transcribed a local Vietnamese development fixture; the isolated model cache remained empty. This checks availability, not speech-recognition accuracy.
- The relocated desktop opened both connected windows. Sending **Uống nước.** through the doctor UI reached the patient UI as **Nước → Uống**, and playback reached **Đã kết thúc** (Finished).

Evidence: [inventory](evidence/portable-inventory-2026-11-01.json), [frozen runtime](evidence/portable-runtime-2026-11-01.json), [desktop UI check](evidence/portable-desktop-2026-11-01.json).

These checks used the same Windows PC with an isolated copy, not a clean Windows VM or a different physical machine. They do not validate live microphone/webcam behavior or signer comprehension.

## Repeat the inventory audit

From a development checkout with Python available:

```powershell
py -3.11 tools/audit_portable.py --package "D:\VSL Clinic\win-unpacked" --output "build\portable-audit.json"
```

The audit is read-only with respect to the package. It verifies bundled runtime inputs against the receipt and reports reference-video omissions separately; those omissions are not silently counted as a complete dictionary.
