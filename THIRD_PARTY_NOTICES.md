# Third-party notices — local demo

This project includes third-party software and locally inherited research assets. The Git source snapshot excludes the local recognition/speech weights, source videos and practice recordings listed in `local-assets-manifest.json`; an authorized local copy is required to restore them. Git synchronization does not create new redistribution rights for inherited or derived research assets. The local portable demo and Git source snapshot have different payloads; see `docs/GIT_SETUP.md`.

## Software

### Optional offline language assistant (0.4.0)

- **Qwen3-0.6B-GGUF Q8_0**, official Qwen distribution, Apache-2.0. Pinned revision `23749fefcc72300e3a2ad315e1317431b06b590a`; SHA-256 and original download URL are in `assets/language/manifest.json`. License: `assets/language/QWEN_LICENSE`.
- **llama.cpp b12034**, official Windows CPU build from ggml-org, MIT. Archive hash and runtime file hashes are in the same manifest. Retain `assets/language/LLAMA_CPP_LICENSE` and `runtime/LICENSE-LLVM-OpenMP`.
- The local portable package includes these files. Git excludes the large binaries; `tools/prepare_language_model.py` restores the pinned official assets with SHA-256 validation. No runtime download is required.
- This model only selects an existing phrase for explicit doctor review. It does not diagnose, generate sign motion, rewrite recognized patient words, or authorize automatic clinical interpretation.

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

## Patient word readout audio

Version 0.3.5 includes 400 fixed Vietnamese label WAVs and one uncertainty cue, prepared using Google Translate TTS at build time. Only the public label dictionary and fixed cue were submitted; no microphone input, conversation, or patient data was sent. `assets/patient-voice/manifest.json` records the requested texts, source URLs, original MP3 hashes and delivered WAV hashes. The clips are decoded to mono PCM with short leading/trailing silence guards. Runtime playback is local and needs no voice download, network service, or TTS model. These generated clips are included for the authorized local demo; no new public license or general redistribution right over service-generated audio is asserted. The rejected Piper experiment remains outside the shipped package in the local research cache.

## Sentence and regional references

Official Ministry of Education and Training QIPEDC materials informed the controlled sentence catalogue (58 templates in 0.3.0). Nine QIPEDC videos were downloaded on the user's request for local reference extraction: W00362, W03090, W03008, W02400N, W01227, W01298, W00884, W03305 and W00248. Their derived motion files are included in this local demo; the original QIPEDC videos are excluded from the desktop package. `assets/qipedc-provenance.json` records URLs, hashes, source windows and descriptions. A missing download timestamp remains null rather than being invented. `research/qipedc-sources.json` retains development provenance and original paths. No new license or general redistribution permission is asserted by this import.

Each imported motion is derived from one reference, not a multi-signer consensus. W00248 uses only the reviewed front-facing take at 1.5–4.2 seconds, excluding the later side-view repetition. The original file remains unchanged. QIPEDC IDs have null model IDs and never become recognition classes. `research/qipedc-crosswalk.json` records dictionary ambiguity; no accent-stripped fuzzy match is accepted as sign equivalence. The motions and sentence templates still require fluent VSL review and are not certified as a regional standard.

## Inherited VSL assets

SL-GCN weights, the 400-label mapping, MediaPipe task files and the 56 demonstration recordings originate from the user's existing local Translator project. The expanded local bank selects 278 recordings (4–5 declared signers per word) from 546 reference candidates in All_cam1. The signer codes are 024–028. Provenance and hashes are recorded in `research/asset-provenance.json`, `research/source-manifest.json`, and the motion manifest. Original bank files for the earlier 20 local words are retained to preserve reviewed sentence join profiles. Demo recordings are excluded from each word's reference selection, but this is not a signer-disjoint or model-training-disjoint evaluation.

The patient practice kit in `demo/benh_nhan` contains 13 unchanged copies of eight of these existing demonstration recordings, ordered within eight scenarios. `demo/demo-script.json` records each model ID, original video ID/path, SHA-256 and decode metadata. No QIPEDC video or label outside the 400 recognition classes is included in this patient kit.

These local files are included for the authorized local development demo. This project does not establish new ownership, consent, dataset/model redistribution rights, or a public license for them. Verify those rights before distributing recordings or trained weights outside the project. No original source video was modified.

The inherited preprocessing/graph files remain byte-identical copies of the original project, with provenance checked by backend tests. Research papers and local Signova/reference-toolkit repositories informed the design; their published accuracy or motion quality is not claimed as this application's result.
# Avatar narration added in local 0.4.1

The local demonstration includes fixed Vietnamese speech generated using Microsoft Edge online TTS through the build-only `edge-tts` tool (LGPL-3.0 project), with voice `vi-VN-NamMinhNeural` at -10% rate. Only public dictionary labels and reviewed generic doctor templates were submitted. No patient conversation is uploaded and runtime narration is offline.

Audio provenance, exact texts, durations, word boundaries and checksums are in `assets/avatar-voice/manifest.json`; original compressed audio is retained in the local build cache. These local demo assets are not offered under a newly asserted public redistribution license. Mouth animation uses locally computed energy and approximate vowel shapes, not a phoneme-alignment model.



## Local multimodal100 integration (0.5.0)

The original VSL100 r3 fold01/seed17 heads, label order and foundation hashes are retained in assets/multimodal100/models/MODEL_MANIFEST.json. DEPLOYMENT.json maps these assets to portable paths. The source Android application is not modified.

SPOTER and Auto-AVSR upstream Apache-2.0 license texts are included in licenses/multimodal100 (retrieved 2026-11-09 from https://github.com/matyasbohacek/spoter/blob/main/LICENSE and https://github.com/mpc001/auto_avsr/blob/main/LICENSE). Torch, torchvision, MediaPipe, OpenCV, NumPy and Python licenses/metadata are preserved in the bundled runtime and its RUNTIME_MANIFEST.json. Local research checkpoints and recorded examples retain their original provenance; this local review build does not assert new public redistribution permissions.

Eighteen additional patient voice clips contain only fixed public Vietnamese vocabulary labels, generated using the existing build-time label-voice tool. URLs, source/audio hashes and text are recorded in assets/patient-voice/manifest.json. No patient conversations or images are sent to a voice service. Normal runtime is offline.

## VSL100 R3 fusion upgrade (0.5.1 local research demo)

The active recognizer uses the frozen SL-GCN + AV-HuBERT cross-attention head,
VSL100 R3 fold01/seed17. The 100 ordered labels and all patient/doctor voice
assets are retained. The source research checkpoint, its artifact hashes and
strict encoder manifests are included under assets/multimodal100/r3.

AV-HuBERT is licensed under the AV-HuBERT license, Copyright (c) Meta
Platforms, Inc. All Rights Reserved. The original AV-HuBERT LICENSE and
Fairseq MIT LICENSE are included under licenses/multimodal100 and alongside
the staged original inference sources. AV-HuBERT is restricted to
non-commercial research, with commercial/production and other restrictions;
this local research demo does not grant production or redistribution rights.
Source: https://github.com/facebookresearch/av_hubert/blob/main/LICENSE.

The adapter loads unchanged eager inference definitions and strict frozen
weights without importing Fairseq training registries. Pose-format0.15.0
source and distribution metadata/license are retained with the model.
SL-GCN derives from the same inherited local foundation; exact configuration,
transforms, weight hash and research head provenance are retained. No original
research file or weight is changed.
