# VSL Clinic 0.4.0 — conversational input and bounded motion transitions

This local upgrade keeps the two-window, one-computer architecture. It does not change the 400-class patient recognition model or claim a larger avatar dictionary: there are still 67 avatar signs and 65 canonical phrase entries.

## Doctor input

Complete conversational variants now map to existing phrase plans, including forms of address, polite requests, symptom questions and open questions. Each sentence is planned separately. A known sentence cannot hide an unsupported second request. The original text, sentence order and question cues remain available.

Examples: `Chị có bị đau bụng không ạ?`, `Cho bác sĩ hỏi anh có sốt không?`, `Cô thấy trong người ra sao?`, and `Vui lòng ngồi nghỉ nhé.`. Modifiers such as side, dose, time, degree and negation remain blocking when the bank cannot express them. These are implementation-tested pilot mappings; a fluent signer's language review is still required.

The **Tìm cách diễn đạt** button appears for unsupported typed input and speech drafts. It runs official Qwen3 0.6B Q8_0 through llama.cpp on two CPU threads. It retrieves a small candidate list from existing phrases, applies protected-term filters, asks the model for a schema-constrained candidate ID, validates that ID and replans the result. The doctor must choose, inspect and send the proposed phrase. The model cannot create vocabulary IDs or send messages. Empty results ask the doctor to rephrase or explicitly send text.

The model loads on demand, never blocks ordinary deterministic planning, and uses neither a cloud API nor the GPU. Requests are serialized and bounded; an unavailable or busy model leaves ordinary conversation available. End/reset releases the model process, discards its context and rejects late results from an old session. The service listens only on loopback with a random session credential. Prompt/output bodies are not written to application logs.

This is deliberately a small retrieval assistant, not an unrestricted translator or medical reasoning system. Increasing candidate diversity still requires usable reference signs and signer review.

## Avatar

Transition-only quintic Bezier interpolation uses the outgoing/incoming motion velocities where compatible. Ordered control points constrain each coordinate between measured endpoints. Intro/outro easing has zero endpoint acceleration. The source sign strokes, annotated trim windows, joint limits and two-bone IK are preserved. Existing sign contacts are not extrapolated to make a transition look smoother.

Numerical continuity/joint checks do not establish linguistic intelligibility or perceived naturalness. A native-window playback review and a fluent signer's assessment remain distinct checks.

## Local assets and build

Run `.venv\Scripts\python.exe tools\prepare_language_model.py` to restore the pinned language model/runtime. The portable payload includes the model, runtime and licenses, but excludes the redundant downloaded archive. Model weights add approximately 610 MiB before runtime files. Source control excludes the binaries.

Standard validation: `python -m pytest -q`, `npm test`, `node tools/audit_motion.mjs`, `npm run build`, and `python tools/probe_language_upgrade.py`. Packaging uses the existing PyInstaller/Electron workflow and a full hash receipt. No cloud publish or Git push is part of this local upgrade.

Official references: [Qwen model card](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF), [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server), and [Connecting the Dots, IJCAI 2022](https://www.ijcai.org/proceedings/2022/852). The last paper motivates separating language planning from motion joining; this release does not implement its trained transition network or claim to reproduce AIVOS internals.

## Verification on 2 November 2026

- Final source suite: **372 Python tests and 18 JavaScript tests** passed. TypeScript/Vite and numerical checks of the actual avatar rig passed.
- Scripted offline-model probe: **12/12** cases matched the intended phrase or declined. One initial expected label for the fatigue question was corrected to the more precise existing feeling-fatigue template; the original probe is retained. This small development set is not an accuracy benchmark.
- Packaged runtime: all 12 concurrency/lifecycle checks passed, including a real model result, no automatic send from that result, unsupported-send rejection, actual patient-renderer completion, End cleanup and rejection of a stale model reply. While the model was busy, ordinary HTTP planning took **13.3 ms median, 26.7 ms maximum** across 12 requests. This is planning latency, not total speech-to-avatar latency.
- Packaged speech: three existing synthetic recordings through the paced live WebSocket. The two supported questions sent the correct gloss sequence and completed avatar playback; the unsupported duration question stayed in review. Each recording was followed by six seconds of silence, with one transcript and no extra utterances.
- Native source UI: retrieved a phrase, explicitly selected it, verified the chat stayed empty until Send, and observed the patient sequence. Maximized doctor/patient windows fit the observed **1536×816 logical work area** without page scrolling. The app's actual EXE was also launched with both windows.

**Patient recognition remains variable.** The first packaged composite-video run processed about **9.0 fps**, misclassified the first intended word `Đau` as `Con trai`, and showed the existing low-sampling warning. A repeat processed **17.3 fps**, correctly streamed `Đau → Mệt`, displayed both words before the turn ended and grouped them once. The unchanged 0.3.7 engine processed **20.3 fps** and recognized both words in a separate comparison. Capture/recognition source, MediaPipe/ONNX DLLs and the landmark model hashes are unchanged. These observations do not establish the cause of the first failure or prove absence of a performance regression. Do not replace the failed record with the successful repeat or promise a flawless live demo.

Evidence: `docs/evidence/upgrade-040-validation.json`, `upgrade-040-language.json`, `upgrade-040-packaged-runtime.json`, `upgrade-040-packaged-speech.json`, and the separate first/repeat/baseline patient-turn files. Tests used synthetic speech and recorded isolated signs, not the user's microphone, a live signer, or an independent clean Windows machine.
