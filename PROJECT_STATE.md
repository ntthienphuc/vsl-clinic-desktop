# VSL Clinic — current project state

Last reviewed: **2026-11-10 (Asia/Saigon)**. Active source **0.5.2** presents **Ký hiệu + khẩu hình (100 words, default)** and **Chỉ ký hiệu (400 words)**, synchronized dictionaries/voices/samples, 24 quick clinical phrases and independent per-utterance speech gating. Minimal UI keeps setup in **Camera và tùy chọn**, preserves explicit phrase review/send, and uses Vietnamese user-facing names rather than model terminology. [0.5.2 status and pilot UX](docs/CLINIC_0.5.2.md). The selected fusion weights/preprocessing remain the SL-GCN + AV-HuBERT cross-attention from [0.5.1 selection](docs/FUSION_SELECTION_0.5.1.md). Preserve **0.4.1**, its original shortcut, source, research and evidence. The owner approved removal of nine obsolete release folders (including 0.5.0/0.5.1) after the new installer passes real installation and app checks; the exact approval and cleanup receipt live in `Organization/CleanupInstaller_2026-11-10`. Historical preservation statements below describe their original checks. Verification scope is prerecorded VSL100/legacy sign videos and synthetic audio; no live camera/person or hospital-room noise. This is a non-commercial research demo under the AV-HuBERT license.

## Active locations

**Installer revision, 10 November:** the first installed run matched all payload files but failed the automatic-word gate (1 automatic / 11 review). Lazy detector startup took 235–265 ms at the first observation. Current capture prepares both CPU graphs on a blank image before opening the source; no synthetic frame enters recognition. On 16 paired frames, pose, face points and gray images were exactly equal. The revised source UI passed 20 checks with **8 automatic correct / 4 review / 0 wrong automatic**, repeated words spoken automatically, noise rejected, and clean exit in 1.699 s. These are the same fixed fixtures, not independent accuracy data. Final installed checks and cleanup receipts are outside the payload at project-root `Organization/Installer_0.5.2` and `Organization/CleanupInstaller_2026-11-10`. See [installer verification](docs/INSTALLER_0.5.2.md). The next paragraph records the earlier portable run, before this startup revision.

Final 0.5.2 packaged verification: **404 Python / 23 JS tests**, 12 fixed VSL100 clips, **7 automatic correct / 5 review / 0 wrong automatic / 11 top-1 agreement**; repeated Sốt automatically spoken twice without grouping duplication. Last active frame → paint p50/p95 **857/929 ms**; → automatic audio **898/962 ms**, using software clocks on a tiny sample. Synthetic negatives in the real EXE produce 0 transcripts; bundled speech produces 1 sent message. Modes, dictionary, phrase review/send, feedback, meaning preservation, voice/mouth, pause, yielding, End and temporary history pass. Final EXE, backend and worker exit cleanly in 2.45 s. Earlier 0.5.2 failures and load/sampling variability remain documented; do not generalize this to clinical accuracy. See project-root `Organization/ModesPilot_2026-11-10/SUMMARY.json`, `portable-final.json` and [0.5.2 status](docs/CLINIC_0.5.2.md).

- Project root: `E:\Project\VSL Clinic`
- Working source: `E:\Project\VSL Clinic\Source`
- Offline installer: `E:\Project\VSL Clinic\Installer\VSL-Clinic-Setup-0.5.2.exe`; installation defaults to `%LOCALAPPDATA%\Programs\VSL Clinic`. Setup creates the **VSL Clinic** Desktop shortcut and keeps its profile under `%LOCALAPPDATA%\VSL Clinic\UserData`. Build and installed-runtime evidence: `Organization/Installer_0.5.2`.
- Current portable candidate: `E:\Project\VSL Clinic\App\0.5.2\win-unpacked\VSL Clinic.exe`
- Preserved baseline: `E:\Project\VSL Clinic\App\0.4.1\win-unpacked\VSL Clinic.exe`
- Launcher: `E:\Project\VSL Clinic\Open Clinic.lnk`
- New-version launcher: `E:\Project\VSL Clinic\Open Clinic 0.5.2.lnk` (separate `UserData_0.5.2` profile).
- Electron profile: `E:\Project\VSL Clinic\UserData`
- Local Word rehearsal: `E:\Project\VSL Clinic\Demo\KICH_BAN_HOI_BENH_VSL_CLINIC_0.3.6.docx`
- Original research references and the 0.4.1 baseline remain preserved. Only the nine explicitly approved obsolete release folders are eligible for cleanup after installer verification. Keep the complete portable folder together when using the development copy.

## Architecture and vocabulary boundaries

Electron + React/TypeScript + Three.js/VRM provide two simultaneous windows on one PC. A local FastAPI engine runs the vision models, Vietnamese PhoWhisper ASR, speech segmentation, controlled language routing and the shared session/playback clock. The app is not Flutter; Android/Translator is a separate project.

**Patient → doctor (0.5.2):** one camera/video owner → selected **Fusion100** or **Sign-only400** → each sufficiently clear completed word appears and is read aloud → a longer pause groups words into a turn. Fusion uses original pose/hands and mouth preprocessing and SL-GCN + AV-HuBERT cross-attention. Sign only uses the original 400-class ONNX pipeline and a separate label space. The app manages both providers, permits one active capture, and fences old events on switches and End. This still requires individual-word boundaries.

**Doctor → patient:** Vietnamese speech or typed text → reviewed aliases/semantic checks → supported sign sequence → patient avatar and text. The current avatar bank has **67 signs** and **65 controlled sentence templates**. Extra QIPEDC signs have no recognizer class ID. Do not silently drop negation, quantities, time, symptoms or other unmatched meaning. Unsupported/uncertain speech must wait for review or rephrasing, with an explicit text-only option.

The 0.5.x portable folder adds an isolated Torch/CUDA/MediaPipe runtime and all pinned multimodal weights. It contains **419 patient voice clips**, covering all 100 multimodal labels while retaining the legacy bank, and **132 male avatar narration clips**, plus PhoWhisper, Silero, avatar/motions and sample videos. Uncertain patient words remain silent until confirmed. Patient voice defaults to 0.9× with pitch preserved; app audio guards the doctor microphone and respects deliberate mute.

## Verified integration: 0.5.1

- Selection: highest mean macro-F1 in the existing 20-configuration VSL100 R3 comparison, **97.3907%** over six folds and three seeds. Fixed fold01/seed17, no training or checkpoint search on Clinic inputs. This is prior research evidence. Three fixed VSL100 inputs match original R3 probabilities within **2.39e-7** absolute error; both image modalities affect fused logits.
- Actual packaged EXE passed ten conversation checks: word text/voice, review/correction, repetitions, turn grouping, avatar/voice/mouth, pause/resume, mic guard, synthetic ASR, interruption and End. Regression: **396 Python + 23 JavaScript tests** passed.
- Twelve fixed VSL100 clips, six words and two signers: **8 automatically spoken, all correct; 4 review; 11/12 top-1 matching; zero omitted clips**. Source run: 10 automatic/2 review on the same inputs. Original-pixel repeated Sốt fixture automatically displayed/spoke both occurrences once before turn end, with no QA confirmation. These are engineering checks, not independent accuracy validation.
- EXE last active frame to text: **803/895 ms p50/p95** (n=12); to audio playing: **819/939 ms** (n=8). Input sampling 15.84–19.09 fps. Software timestamps only. Packaged worker crossed five minutes with bounded buffers, passed source change, crash/restart and End. CPU-only probe recognized Sốt with 1.105-second inference; no sustained CPU realtime claim.
- Full inventory passed for 0.5.1 and both preserved packages; ordered 100-class voice coverage and pinned model/runtime hashes verified. All 190 tracked original inputs/snapshots were unchanged. Final source/package parity is recorded in portable `BUILD_RECEIPT.json`; evidence lives under `Organization/MultimodalIntegration_2026-11-09/release-051`.
- Three predeclared OOV clips produced three reviews and no automatic commits. Missing-face and static-rest/shaken-image fixtures suppressed speech. A synthetic mouth cover still allowed a correct Sốt commit; a detected face does not prove usable lips. Real mask, incidental-action and general OOV rejection remain unvalidated. No live webcam/person, physical acoustic echo or clean-machine check. No training, large benchmark, push, publish or deployment.

## Preserved integration history: 0.5.0

- Actual packaged EXE passed ten functional checks with the real multimodal worker, both windows, avatar/voice/mouth, synthetic ASR, per-word patient voice, repetition and End. Full regression: **397 Python + 23 JavaScript tests**.
- Twelve predeclared clips (six words, two signers): **5 automatic words, all matching the fixture labels; 7 review; 11/12 top labels matching**. No clip was omitted. The review rate is **58.3%**, too high to call general hands-free conversation solved. No thresholds were relaxed to pass the cases.
- Repeat after the user reported closing Lip: **7/12 automatic, all matching;5 review;11/12 top labels matching**, all10 EXE checks pass and exit0. These are the same12 inputs, not a larger independent dataset. Sampling16.29–19.29fps; last active frame→paint **797/935ms p50/p95**, →audio **861/951ms** (n=7). Latency did not improve, and Lip was not proven active in the earlier sweep; do not infer causality from this comparison. Evidence: `docs/evidence/multimodal-050-AFTER_LIP_CLOSED_COMPARISON.json`.
- Under the tested EXE load, sampling was **15.7–20.1 fps**. Last active sampled frame → displayed word: **744/886 ms p50/p95** (12 clips); → audio playing event: **770/876 ms** (five automatic words). These are software timestamps on a tiny fixed set, not photon/acoustic latency or webcam accuracy.
- Original vs Clinic preprocessing/features/logits matched exactly over 172 identical frames. The 312-second composed stream crossed five minutes without reset, emitted eight distinct results, kept observed worker RSS at 1.19–1.66 GB and at most 217 buffered frames. Source change, worker crash/restart and End fencing passed.
- Three additional prescribed OOV samples already in the portable legacy bank (Buổi chiều, Chú ý, Đọc) produced3 review candidates and0 automatic commits with the actual packaged worker; no clip was omitted. Both modalities and natural boundaries were available. This is a small OOV check, not general rejection accuracy; evidence `docs/evidence/multimodal-050-oov3-REPORT.json`.
- **Open robustness limits:** a synthetic mouth cover still committed a word; missing face correctly suppressed speech, but face detection is not mouth-visibility detection. No real mask/incidental-action negative set is available. General OOV and sign/non-sign rejection remain unvalidated despite the3 OOV cases above. Do not use a closed-set softmax score as proof of an intentional sign.
- All 69 fingerprinted research inputs and the 0.4.1 EXE/asar/original shortcut remain unchanged; the full baseline audit verified 3,306 receipt payloads. The new package has its own `BUILD_RECEIPT.json`; never replace the original launcher as part of this candidate handoff.
- Scope: local integration and fixture candidate only. No training, large benchmark, Git push, publication or deployment.

## Local upgrade: 0.4.1

- Supported doctor speech in Auto mode starts avatar signs, offline Vietnamese male narration and mouth animation driven by actual audio time and energy. Pause, mute, replay, speed, disconnect and End share lifecycle guards.
- All 65 canonical phrases and 67 avatar words have bundled narration, adding about 6.6 MB. Longer narration adds neutral time without accelerating recorded sign strokes.
- A clear patient word appears and is spoken immediately. In Auto mode it also pauses the avatar to yield; **Tiếp tục** resumes the remaining instruction. Uncertain words remain visible but are not read as facts.
- Microphone capture is guarded around voice intervals and echo tails, then resumes in quiet gaps while signing can continue. This is not full-duplex acoustic echo cancellation.
- Narrow, acoustic-score-gated ASR courtesy repair handles complete `cạm ơn`/`cám ơn` utterances, preserves raw text, and rejects extra meaning, truncation and uncertainty. General n-best repair, semantic endpointing and trained sign/non-sign rejection remain future work.
- Final checks: **383 Python + 22 JavaScript tests passed**. Source runtime passed ten checks; actual EXE passed eight, including bundled voice hashes, synthetic ASR sending once after silence, real reference-video recognition to voice, patient-reply interruption, microphone recovery and End cancellation. Guide: [avatar voice 0.4.1](docs/AVATAR_VOICE_0.4.1.md).
- Actual audiovisual simulation: `Demo/AVATAR_GIONG_NAM_0.4.1.webm` under the project root, 1280×720, about 15 seconds. Mouth motion is approximate, not validated phoneme-level lipreading or VSL facial grammar.
- Backup: `Organization/AvatarVoice041_2026-11-02`. Existing 0.4.0 release is preserved. No Git push, publish or deployment.

## Local upgrade: 0.4.0

- Added complete-clause conversational variants and composition without dropping unsupported clauses.
- Added **Tìm cách diễn đạt** in unsupported typed input and speech review. Official Qwen3 0.6B Q8_0 runs on demand through llama.cpp, using two CPU threads and no cloud service. It only selects an existing phrase and requires explicit doctor review. Protected-term and output-shape checks block unsafe/invented candidates.
- Added velocity-aware bounded quintic avatar bridges and smoother intro/outro easing; recorded strokes and joint constraints remain intact.
- The package includes the local model, runtime and licenses (about 610 MiB model weights). It releases the model/context at End/reset and rejects late responses.
- Final source tests: **372 Python + 18 JavaScript** passed; actual-rig audit and frontend build passed. Packaged concurrency checks passed; ordinary planning during model work measured **13.3 ms median / 26.7 ms max**. Three synthetic speech cases passed with six seconds of silence after each utterance.
- **Unresolved performance limit:** the first patient composite-video run was ~9 fps and misrecognized `Đau`; a repeat at ~17 fps correctly streamed `Đau → Mệt`. The unchanged old engine reached ~20 fps in a separate comparison. Keep both failure and repeat evidence. Do not claim stable recognition or live-person validation.
- See [upgrade decisions and evidence](docs/UPGRADE_0.4.0.md). Backup of pre-upgrade changed files/diff: `Organization/Upgrade040_2026-11-02`. No Git push/deploy was performed.

## Research follow-up: natural conversation and pilot robustness

On 2 November 2026, the user reported good realtime behavior and requested robustness research. The [research and proposed design](docs/NATURAL_CONVERSATION_RESEARCH_2026-11-02.md) compares current source with online sign recognition/translation, acoustic ASR correction and realtime turn-taking literature. Priorities are bounded ASR alternatives and meaning-preserving repair, learned sign/non-sign rejection, provisional versus committed words, and echo-aware interruption. These are **proposals, not implemented 0.4.0 features**.

A [six-input planner/retrieval probe](docs/evidence/natural-conversation-audit-2026-11-02.json) recorded that `cảm ơn` was supported but `cạm ơn` had no repair candidate in 0.4.0. It also records source hashes and supported n-best capability in the installed CTranslate2 API. That was a research-only probe. The later 0.4.1 implementation above adds only narrow ASR courtesy repair and guarded handover, not the full research proposal.

## Retained behavior from 0.3.7

- The doctor's chat column is approximately twice the width of the input column on desktop layouts.
- Unsent speech occupies one compact panel; **Kiểm tra** opens the full review dialog.
- A progress bar above chat shows the patient's current avatar sign, percentage, estimated remaining time and queue. Pause, speed, replay and patient-window disconnect use the same timeline.
- **Kết thúc** stops capture, microphone and avatar and clears both screens, drafts, pending playback and input. Generation/session/epoch guards reject late callbacks.
- **Lưu tạm**, unchecked by default, keeps one read-only in-memory copy for the doctor. Open **Bản tạm** or **Xóa bản tạm**. Closing the app discards it; ending another session replaces or discards it. Mode/source preferences remain selected.
- See [workspace behavior and verification](docs/WORKSPACE_0.3.7.md) and [usage](docs/USAGE.md).

## Git state and authorization

Public repository: https://github.com/ntthienphuc/vsl-clinic-desktop

The working source HEAD is `2436e7a9e9e80b805c08e6834a3029b75c4cbed6`, with substantial intentional uncommitted changes from 0.3.5–0.4.1. Preserve them. Do not reset, clean, or overwrite the checkout.

Public `main` was updated separately with documentation-only commit `86fb9cbafb5461a25e77b76cca3a3e09f12d64d5`: remove the Demo scenarios promotion and links from README/documentation index. The local app changes through 0.4.0 have not been pushed. The isolated worktree is `E:\Project\VSL Clinic\Organization\GitHubDocs_0.3.7`. Reconcile the dirty working tree deliberately before any future sync. **No new push, publish or deploy without explicit user request.**

## Verified evidence and limits

On 2026-11-01: **334 Python tests**, **17 JavaScript tests**, TypeScript/Vite build, actual source Electron UI and actual portable 0.3.7 EXE checks passed. Both windows fit 1280×720 and 1920×1080 without page overflow; individual panels can scroll. Nine real synthetic-speech drafts were exercised. Playback pause/speed/replay/disconnect, End/temporary history, late-event rejection and packaged voice regression were tested.

- [Source UI evidence](docs/evidence/workspace-037-source.json)
- [Actual EXE evidence](docs/evidence/workspace-037-packaged.json)
- [Packaged voice evidence](docs/evidence/workspace-037-packaged-voice.json)
- [Build receipt](docs/evidence/release-receipt.json), copied to the portable folder as `BUILD_RECEIPT.json`
- Portable inventory: `E:\Project\VSL Clinic\Organization\WorkspaceQA037\portable-audit-final.json` — **3,081 payload files** verified, no reported problems.

These are prerecorded-video/synthetic-speech software checks, not new-signer accuracy, microphone, comprehension, clinical or clean-machine validation. Heavy unrelated processing previously reduced landmark sampling and recognition quality. Retest with the same inputs and comparable workload before attributing differences to a model/code change.

## Resume/build checklist

1. Read this file, relevant docs/evidence and `git diff`; inspect actual paths/version before editing.
2. Preserve original data and separate derived outputs. Keep recording order, displayed label, recognizer ID and QIPEDC ID distinct.
3. Work in `Source`; use `.venv\Scripts\python.exe`, `npm.cmd test`, `npm.cmd run build`, and meaningful targeted/runtime tests for changed behavior.
4. `npm.cmd run package` now delegates to `tools/package_multimodal.py`, which rebuilds the frozen engine, writes its source build stamp, builds the frontend/Electron app and stages the complete multimodal runtime. Do not run two packagers concurrently.
5. Run `tools/release_receipt.py` and `tools/audit_portable.py` against the new package; check the actual EXE. Keep `Open Clinic.lnk` pointing at 0.4.1 while 0.5.0 remains a candidate. Preserve previous releases and evidence, including failed attempts.

## Related task completed 2026-11-02: 100-word recording references

Extend the user's **60 core multi** Canva reference deck with **40 distinct medical/daily-life words**. First inventory all 60 original labels. Prefer the user's existing 400-class video dataset when a term belongs to it; use QIPEDC references for other words. Preserve original media and record source IDs/paths/URLs and hashes. New recording prompts do **not** automatically expand the app's trained recognizer or its motion bank.

Original Canva: https://www.canva.com/design/DAHJsormPZQ/vl7JOOLY5deJug6JEtU2sA/edit

Delivered Canva copy: https://www.canva.com/design/DAHZuXIgbDw/sR6ueOIj_P_pGZQttfkKDw/edit

Task files: `E:\Project\VSL Clinic\DataCollection\Core100_2026-11-02`. The [recording README](../DataCollection/Core100_2026-11-02/README.md), CSV and manifest contain the selection and exact provenance. The 40 additions use 24 original 400-class dataset videos and 16 official QIPEDC videos. All 40 files fully decoded; all 40 new page labels/video filenames and all 60 old labels/displayed IDs were checked in the Canva copy. Grid layout and two representative video playbacks were checked. The original 60-page design was preserved. This did not change the app, trained vocabulary, motion bank, EXE or GitHub.
