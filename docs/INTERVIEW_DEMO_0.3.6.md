# Medical interview demo 0.3.6

Two fictional interviews replace the previous short scripts in the doctor picker. Each has 11 turns: abdominal pain with associated symptoms, and tiredness with sleep/appetite questions. The shipped practice kit contains 29 patient word occurrences from 17 of the unchanged 400 model classes, with 22 paced composite replies and the numbered original clips.

## Doctor vocabulary and planning

The bank now contains 67 motions and 65 supported sentence templates. QIPEDC `W03239N` (thế nào?) and `W00145N` (bao giờ?) provide two new question signs. The source videos were downloaded from the official QIPEDC URLs and reviewed visually before extraction. Single-source keypoints are cleaned/resampled by the existing reference pipeline and retargeted with the existing joint constraints. These are not multi-signer consensus estimates. Source IDs, URLs, hashes, download times and reviewed windows remain in `assets/qipedc-provenance.json` and `research/qipedc-sources.json`.

Seven explicit sentence templates add open feeling questions, pain/sleep/wake timing, appetite, wanting sleep and feeling weak. The written original stays visible. Timing questions do not substitute for onset or duration: “Bạn bắt đầu đau bụng khi nào?”, “Bạn đau bụng bao nhiêu ngày?”, sleep-hour questions, unsupported negation, numeric temperature and medication instructions remain blocked from automatic signing. Generic avatar question expression and word ordering still need fluent signer review.

## Runtime and packaging

The Electron/React UI and external vocabulary/phrase assets are updated. The recognition and speech engine binary is unchanged from the previous package (its internal health version still reports 0.3.4). All 400 local Vietnamese readout clips, the uncertainty cue, PhoWhisper, Silero, detection models and the male avatar remain bundled. There is no model retraining or expansion of patient recognition classes.

The application is a portable Windows folder, not a one-file installer. Use `VSL Clinic.exe` with the entire folder next to it. The central `Open Clinic.lnk` is updated only after package verification. Previous releases and previous scripts are retained.

## Rehearsal materials

- `demo/scenarios-v0.3.6.json`: canonical dialogue and patient label IDs.
- `demo/HOI_BENH_2026-11-01/`: 22 response folders, numbered unchanged reference clips, composite replays and provenance manifest.
- A five-page Word script is delivered in the central project `Demo` folder, with local links into the packaged practice kit.

Replays append 800 ms holds between isolated-word samples and a final two-second hold. This is a selected demonstration, not a continuous-signing dataset or an unbiased accuracy evaluation. Human microphone, webcam and fluent-signer comprehension validation are separate from the fixed-input checks.

## Failures retained and corrections

The first packaged replay recognized the original `Không cần` practice sample `021268` as `Đắng` at 27.55 observed fps with no frame-quality warning. An isolated replay reproduced it; source `021368` and `023920` also failed, while `022152` and `023036` produced `Không cần`. The final practice turn uses unchanged source `022152`, with its label and SHA-256 checked against the existing source manifest. The model and thresholds are unchanged. This is explicit reference selection for a demonstration, not an accuracy improvement. Original clips and first-run evidence are retained.

Synthetic speech produced `bản thức dậy vào lúc nào` for the scripted `Bạn thức dậy vào lúc nào?`. A narrowly scoped exact alias now accepts that spelling in this one template, retaining the original transcript. No generic word deletion or medical-content substitution is introduced. Initial ASR evidence is retained alongside the final rerun.

## Verification

- Python: 330 tests passed; JavaScript: 14 tests passed; TypeScript/Vite build passed.
- Actual VRM hierarchy audit: 133 full motion/sentence cases, zero numerical constraint failures. This does not certify skin contacts or signer comprehension.
- Final packaged video rehearsal: 22/22 turns, 29/29 word occurrences, streamed before turn completion, one finished turn per reply, avatar rendered/completed for every prompt.
- Four unsupported medical-content checks blocked dispatch without adding messages or changing playback.
- Both interfaces fit 1280×720 and 1920×1080 with no whole-page overflow; conversation history scrolls within its own panel.
- Final synthetic speech rehearsal: all 17 distinct scripted prompts dispatched exactly once and completed on the avatar; one unsupported duration question remained blocked. Six seconds of trailing silence per input produced no extra transcripts.
- Final EXE readout smoke check: four words spoken in order before turn completion; microphone echo gate, automatic resume and intentional mute all passed. The package contains all 401 audio entries.
- A metadata-only final rebuild preserved SHA-256 for all 154 recorded runtime inputs (frontend, motions, phrases, engine and interview kit).
