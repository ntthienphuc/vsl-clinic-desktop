# Windows package contents

[← Project overview](../README.md) · [Source setup](GIT_SETUP.md) · [Usage guide](USAGE.md)

End users receive one **VSL-Clinic-Setup-0.5.2.exe** containing the full offline payload. Setup creates a Desktop shortcut and a Windows uninstall entry. The development payload remains a **portable folder** at `App/0.5.2/win-unpacked`; its application EXE alone is insufficient. `App/0.4.1` remains the preserved baseline. Older package copies approved for cleanup are removable after the new installation passes verification; their historical evidence is retained. Current checks and compatibility limits are in [0.5.2 verification](CLINIC_0.5.2.md).

## What the end user receives

| Component | Included in the audited portable folder |
| --- | --- |
| Desktop runtime | Electron, Chromium, frontend bundles, fonts and audio worklet. |
| Backend runtime | Frozen `ClinicEngine.exe`, Python 3.11 DLL, libraries and native dependencies. |
| Patient-side recognition | Default **100-class SL-GCN + AV-HuBERT cross-attention fusion**, original ordered labels and pinned heads/foundations, crop geometry and MediaPipe resources. **400-class SL-GCN ONNX** is the explicit Sign only option, with its own dictionary. |
| Multimodal runtime | Private stdio worker and isolated relative-path Python 3.11.9, Torch 2.6/CUDA 12.4 runtime, MediaPipe and OpenCV. No external Python/venv or model server. |
| Signing avatar | Male `ClinicMale.vrm`, **67** motion files with matching vocabulary entries, join profiles and semantic metadata. |
| Doctor-side language | **65** controlled templates plus reviewed aliases; optional bundled Qwen3 0.6B Q8_0/llama.cpp suggestion workflow with doctor review. |
| Offline avatar voice | **132** Vietnamese male clips, exact word timing and mouth energy envelopes, about **6.6 MB** of WAV files. |
| Offline patient word voice | **419** clips; all 100 exact multimodal display labels covered. Uncertain words stay silent until confirmed. |
| Vietnamese speech | **PhoWhisper base INT8** weights, config, tokenizer, vocabulary and preprocessing config. |
| Speech activity | Bundled **Silero VAD v6 ONNX** and runtime. |
| Runtime sample videos | Six multimodal examples in `resources/assets/multimodal-samples`; 56 legacy examples in `resources/assets/samples`. The source selector exposes only available files for the selected recognition mode. |
| Patient practice/demo kit | **88 MP4 files** under `demo`, including numbered practice videos and concatenated rehearsal clips. This count includes repeated source clips. |
| Notices and provenance | Bundled notices, model metadata, manifests, demo documentation and build receipt. |

No separate Python, Node, PhoWhisper or model download is part of the normal end-user launch flow. The speech model is opened from its packaged local directory with `local_files_only=True`.

The 0.5.1 inventory passed with **20,400 isolated runtime files**, all 100 class-to-voice mappings, **419 patient clips**, **132 avatar narration clips** and a logical portable size of about **9.62 GB**. The payload is verified against source/build inputs in `BUILD_RECEIPT.json`. Large immutable binaries use ordinary NTFS hardlinks on this development drive; copying the entire folder produces a self-contained copy, and no research-directory path is required at runtime. AV-HuBERT restricts this artifact to non-commercial research; its original license is bundled.

## What is not in this package

- **A complete 100- or 400-word reference-video library.** The dictionary contains all labels; the sample selector contains only six Fusion or 56 Sign-only examples. The inherited catalog URLs remain metadata and are not a complete bundled video library.
- **Raw QIPEDC source videos.** Their motion data and provenance are included, but `assets/reference-source` is explicitly excluded from the desktop package.
- **The complete reference/training corpus.** Bank-building metadata can retain source paths as provenance. End-user playback uses baked motion files and does not need those original paths. Rebuilding or expanding the bank requires the original research inputs.
- **Development-only speech fixtures or the Git checkout.** Neither is required to run the packaged app.

The package contains the assets needed by the current **67-sign avatar demo**. It is not a full 400-sign avatar/video product. This distinction is independent of whether the recognition model can classify 400 labels.

## Historical 0.3.4 verification on 2026-11-01

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
