# Third-party notices — local demo

This project includes third-party software and locally inherited research assets. The Git source snapshot excludes the local recognition/speech weights, source videos and practice recordings listed in `local-assets-manifest.json`; an authorized local copy is required to restore them. Git synchronization does not create new redistribution rights for inherited or derived research assets. The local portable demo and Git source snapshot have different payloads; see `docs/GIT_SETUP.md`.

## Software

Exact installed versions, available license expressions, and copied license texts are indexed in `licenses/inventory.json`. Texts are retained under `licenses/javascript`, `licenses/python`, and `licenses/electron`. The Python inventory covers the build environment and includes development packages; it is an over-inclusive inventory, not a statement that every installed package is shipped.

- Electron and Chromium: retain `LICENSE.electron.txt` and `LICENSES.chromium.html` provided by Electron, plus the copied notices.
- React, Three.js, three-vrm and its pixiv components: MIT license texts are preserved.
- Lucide: retain the installed package license covering Lucide and Feather-derived icons.
- Python runtime, FastAPI, Uvicorn, MediaPipe, ONNX Runtime, OpenCV, NumPy, SciPy and dependencies: consult the individual copied texts. Binary packages can contain additional bundled library notices.
- Offline speech runtime: faster-whisper, CTranslate2, tokenizers, PyAV/FFmpeg, huggingface-hub and webrtcvad-wheels. Their installed distribution metadata and available license texts are included in the same inventory. The runtime does not bundle PyTorch or download speech weights at startup.
- Nunito: SIL Open Font License; `licenses/fonts/Nunito-OFL.txt` was obtained from the official Google Fonts repository. Font files were copied from the existing Translator project.

Recreate the inventory using `.venv/Scripts/python.exe tools/collect_notices.py` after changing dependencies. Keep the `licenses` directory with a portable build.

## Active male avatar (0.3.4)

Model: **Sakurada Fumiriya**, the VRoid Studio beta male sample by pixiv. The official model-specific page declares **CC0**, consistent with the embedded `licenseName: CC0` metadata: https://vroid.pixiv.help/hc/en-us/articles/360014788554-Sakurada-Fumiriya (checked 22 October 2026).

Downloaded copy: https://raw.githubusercontent.com/madjin/vrm-samples/master/vroid/beta/Sakurada_Fumiriya.vrm

Original SHA-256: `d8fb05f33e377df028cb6b9d58c441ce68326c41fa23f6c735d40c65ae3dc710`.

Runtime `ClinicMale.vrm` SHA-256: `942b21dfb4014ec5fd18bd47627a9f5658cda9d3e1d16bfeaad46501a13f6c2e`.

The conversion adds glTF mesh morph names for the current loader. Runtime code uses PBR materials, adjusts eye and jaw geometry with matching morph deltas, replaces the hair with a short continuous mesh, extends the skinned shirt hem and adds glasses, a stethoscope, buttons and a badge. The tie is navy. The original rig, hand geometry and skin weights are retained. Full embedded metadata, both hashes and modifications are recorded in `assets/avatar/provenance.json` and `licenses/inventory.json`. This character is not a certified sign-language interpreter.

## Retained earlier avatar

Model: **VRM1_Constraint_Twist_Sample**, author **pixiv Inc.**, copyright **2022 pixiv Inc.**

Source: https://github.com/pixiv/three-vrm/tree/release/packages/three-vrm/examples/models

SHA256: `12c2b97e95e700783a6a550dc0eee2d7880aeedccef9ae67bc4c5a2f0f2631a2`

The embedded VRM metadata is copied verbatim into `licenses/inventory.json`. It declares VRM Public License 1.0, redistribution allowed, modification/redistribution allowed, and corporate commercial usage. The authoritative license is https://vrm.dev/licenses/1.0/. Retain the original embedded metadata and applicable terms. The application modifies clothing materials at runtime, adds a procedural clinical outfit, badge and stethoscope, binds an existing eyebrow morph for questions, and drives the normalized humanoid rig. The underlying asset is retained unchanged; the sample character is not a certified interpreter.

## Vietnamese speech model

**PhoWhisper-base**, VinAI Research, BSD 3-Clause license.

- Model source: https://huggingface.co/vinai/PhoWhisper-base
- Project: https://github.com/VinAIResearch/PhoWhisper
- Pinned upstream revision: `7ebdb9e88f5cc5271fb88f4d642c82ff9388650e`.
- Local conversion: CTranslate2 4.6.2, INT8 weights, CPU inference. Conversion details and individual file hashes are retained in `assets/speech/phowhisper-base-int8/provenance.json`.
- Converted `model.bin` SHA256: `8b039b26e4e640942900d93f1094ee83a2d71c0245e398bc83b02494e868e588`.
- The upstream license text is retained alongside the model and under `licenses/models/PhoWhisper-base-LICENSE.txt`.

Three public Vietnamese WAV examples from `dangnguyenngochai/demo_vietasr` were downloaded into the local, untracked research cache to test the speech path. That repository did not declare a license when inspected. These recordings are **not included in the desktop package**, and their outputs are not an accuracy benchmark.

**Silero VAD v6**, Silero Team, MIT: https://github.com/snakers4/silero-vad. The ONNX graph bundled with faster-whisper 1.2.1 is now used for streaming speech activity. Its SHA-256 and `licenses/models/Silero-VAD-LICENSE.txt` are recorded in `licenses/inventory.json`; state handling follows the installed faster-whisper `vad.py` contract.

Four fixed Vietnamese test phrases were synthesized using Google Translate TTS for development-only audio-path checks. `research/speech-samples/synthetic-vi/provenance.json` records their text, source and hash. These files are excluded from the portable build. They are synthetic fixtures, not recordings of a doctor, and do not establish microphone accuracy. Runtime audio never goes to this service.

## Sentence and regional references

Official Ministry of Education and Training QIPEDC materials informed the controlled sentence catalogue (58 templates in 0.3.0). Nine QIPEDC videos were downloaded on the user's request for local reference extraction: W00362, W03090, W03008, W02400N, W01227, W01298, W00884, W03305 and W00248. Their derived motion files are included in this local demo; the original QIPEDC videos are excluded from the desktop package. `assets/qipedc-provenance.json` records URLs, hashes, source windows and descriptions. A missing download timestamp remains null rather than being invented. `research/qipedc-sources.json` retains development provenance and original paths. No new license or general redistribution permission is asserted by this import.

Each imported motion is derived from one reference, not a multi-signer consensus. W00248 uses only the reviewed front-facing take at 1.5–4.2 seconds, excluding the later side-view repetition. The original file remains unchanged. QIPEDC IDs have null model IDs and never become recognition classes. `research/qipedc-crosswalk.json` records dictionary ambiguity; no accent-stripped fuzzy match is accepted as sign equivalence. The motions and sentence templates still require fluent VSL review and are not certified as a regional standard.

## Inherited VSL assets

SL-GCN weights, the 400-label mapping, MediaPipe task files and the 56 demonstration recordings originate from the user's existing local Translator project. The expanded local bank selects 278 recordings (4–5 declared signers per word) from 546 reference candidates in All_cam1. The signer codes are 024–028. Provenance and hashes are recorded in `research/asset-provenance.json`, `research/source-manifest.json`, and the motion manifest. Original bank files for the earlier 20 local words are retained to preserve reviewed sentence join profiles. Demo recordings are excluded from each word's reference selection, but this is not a signer-disjoint or model-training-disjoint evaluation.

The patient practice kit in `demo/benh_nhan` contains 13 unchanged copies of eight of these existing demonstration recordings, ordered within eight scenarios. `demo/demo-script.json` records each model ID, original video ID/path, SHA-256 and decode metadata. No QIPEDC video or label outside the 400 recognition classes is included in this patient kit.

These local files are included for the authorized local development demo. This project does not establish new ownership, consent, dataset/model redistribution rights, or a public license for them. Verify those rights before distributing recordings or trained weights outside the project. No original source video was modified.

The inherited preprocessing/graph files remain byte-identical copies of the original project, with provenance checked by backend tests. Research papers and local Signova/reference-toolkit repositories informed the design; their published accuracy or motion quality is not claimed as this application's result.
