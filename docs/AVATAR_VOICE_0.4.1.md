# Avatar voice and automatic conversation — 0.4.1

Local demonstration build, 2 November 2026. This extends 0.4.0; it does not retrain the 400-class patient recognizer or implement unrestricted continuous VSL.

## User-visible behavior

- Doctor speech in Auto mode uses the existing whole-meaning planner and automatically starts supported avatar messages.
- The male clinician avatar now speaks Vietnamese using **vi-VN-NamMinhNeural** audio prepared from the 65 canonical phrases and 67 avatar words. All **132 WAV clips** are bundled, about **6.6 MB** combined. No runtime speech service or additional voice installation is needed.
- Mouth motion uses the actual audio cursor, locally computed energy and approximate vowel shapes. Silence, pause, mute, disconnect and End close the mouth. Question brows remain separate.
- Each clause has one shared sign/audio schedule. The complete Vietnamese clause is spoken naturally; individual phonemes are not stretched to individual signs. Longer narration adds neutral time after the sign, preserving recorded strokes.
- Both windows can toggle avatar voice. Pause, resume, speed and replay apply to narration; pitch is preserved.
- In Auto mode, a clear patient recognition result pauses the avatar and shows that it yielded to the patient. The doctor can continue the remaining instruction with **Tiếp tục**. Ordinary camera movement alone does not trigger this handover.
- Patient words still appear immediately. Clear words are read without waiting for the full turn. An uncertain word remains visible with a question mark and is only spoken after confirmation; confirmation of the same ID speaks once.
- The microphone is protected around actual avatar speech intervals and patient-word audio, including an echo tail. It automatically resumes in quiet gaps while the avatar can continue signing. This remains a guarded half-duplex arrangement, not a validated full-duplex echo canceller.
- A narrow ASR-only repair accepts complete courtesy expressions such as `cạm ơn` when segment acoustic scores pass its checks. It preserves the original transcript in the chat. Unclear/truncated audio, extra meaningful words and clinical concepts do not use this rule. General n-best reranking and semantic endpointing remain research work.

## Implementation

- `backend/avatar_voice.py` attaches allowlisted audio cues and preserves sign-source timing.
- `src/avatar/narration.ts` owns one bounded set of audio elements per playback iteration. Mouth animation stops on failed playback; stale callbacks cannot restart old audio.
- `src/api.ts` applies the doctor microphone guard before scheduled voice onset. Multiple sound sources cannot release one another's guard.
- Existing session epochs, capture generations and playback iterations remain authoritative.
- `tools/build_avatar_voice.py` synthesizes only the fixed public vocabulary/templates, then checks exact textual correspondence at word boundaries before splitting the batch. Original compressed audio, word timings and hashes remain in the local build cache.

The mouth animation is an audiovisual prototype. It is not validated phoneme-level lipreading, VSL grammatical mouthing or a replacement for fluent-signer comprehension review. The existing simple question face is not a complete facial grammar.

## Verification and evidence

Use [source runtime evidence](evidence/avatar-041-source.json), [actual EXE evidence](evidence/avatar-041-packaged.json), [video stream inspection](evidence/avatar-041-video.json) and the final package receipt for the exact tested scope. Source tests cover audio cancellation, stale callbacks, speed, mute, meaningful-content guards, immediate word voice and shared timing. The first runtime probe sampled the silent audio lead-in too early; that failed assertion is retained as `avatar-041-source-attempt1.json`, and the probe now waits for an actual voiced mouth frame.

The actual 0.4.1 EXE passed eight runtime checks: all 132 bundled voice hashes, real video recognition to immediate word voice, microphone protection during narration, automatic microphone recovery during silent signing, patient-reply interruption, stopping interrupted narration, a single automatically sent synthetic ASR utterance followed by six seconds of silence, and End cancellation. In this run, word audio began 54 ms after the recognized word arrived at the renderer; that is not end-to-end sign recognition latency. The synthetic utterance used 576 ms of endpoint silence and about 988 ms of decoding; real voices and room acoustics remain untested.

Local recording: `E:\Project\VSL Clinic\Demo\AVATAR_GIONG_NAM_0.4.1.webm` (1280×720, about 15 seconds, with actual audio). It presents three supported clauses: **Bạn có đau bụng không? Vui lòng ngồi nghỉ nhé. Cảm ơn.**

Runtime checks use prerecorded sign video and synthetic speech, including silence after one utterance. They are not new-signer, real microphone, acoustic-room or clinical-pilot validation. No learned non-sign rejection model or larger vocabulary was added in this release.

The recording is generated from the actual avatar canvas and actual audio playback. Its presentation background/caption are for viewing the simulation; the app retains its two-window UI.

## Try it

1. Open the complete 0.4.1 portable folder through the project launcher.
2. Choose **Tự động**, select a camera or existing reference video and start the conversation.
3. Say **Bạn có đau bụng không?** or **Y tá ơi, đo nhiệt độ nha.** A supported, clear utterance starts signs and narration.
4. Test pause/resume, voice toggle and replay from either screen.
5. Have the patient sign a supported word, or use the reference video. The doctor gets incremental text and clear-word speech; a clear reply pauses the avatar.
6. End clears both windows and cancels pending audio. Unsupported meaning still prompts rephrasing/review.

No Git push, public asset upload or deployment is part of this change.
