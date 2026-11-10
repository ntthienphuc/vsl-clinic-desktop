# Doctor workspace and ending a conversation — 0.3.7

The doctor can follow the patient's signing avatar without looking at the other monitor. Conversation history has approximately twice the width of the left input column on supported desktop layouts.

## Playback progress

The bar above conversation history shows the current sign, sign number, percentage, approximate remaining time and number of queued sentences. It reads the same authoritative timeline as the patient renderer. Loading stays at zero; pauses freeze progress; speed changes adjust remaining time; replay starts again; completion reaches 100%. A disconnected patient window pauses the avatar and progress together. This change adds visual progress, not an extra avatar voice.

## Compact speech review

Unsent or unsupported speech appears as one compact panel with the number of drafts and a short preview. **Kiểm tra** opens the full review dialog with a draft selector. Incoming drafts do not change the draft being edited in an open dialog. The text composer remains available. Missing sign coverage still blocks sign sending; review, rephrasing and an explicit text-only send remain available.

## End and optionally retain a copy

**Kết thúc** stops capture, speech input and avatar playback and clears messages, drafts, input, camera preview, pending signs and current recognition on both windows. Session IDs, capture generations and speech epochs fence late callbacks. Mode and source preferences remain selected.

**Lưu tạm** is unchecked by default. When checked before End, it retains one read-only copy of messages and unsent drafts in backend memory. The doctor can open **Bản tạm** or delete it with **Xóa bản tạm**. Viewing it does not restore playback or show old content to the patient. Closing the app discards it. Ending another conversation replaces it if checked or deletes it if unchecked. It is not a file export or a permanent patient record.

## Verification

- 334 Python tests and 17 JavaScript tests passed. TypeScript/Vite build passed.
- Actual Electron windows with a prerecorded model input and synthetic Vietnamese speech: nine real review drafts remained in a roughly 76 CSS-pixel panel; the full review dialog still blocked unsupported sign sending.
- Both windows fit 1280×720 and 1920×1080 with no page overflow. Individual histories and editors can scroll. Screenshots were inspected visually.
- Source runtime passed pause, resume, speed change, patient-window disconnect/reconnect, completion, replay, End, optional read-only copy, copy deletion and default discard checks.
- The actual 0.3.7 portable EXE and bundled engine passed progress, queue, End clearing both windows, temporary-copy view/delete and late-event checks. The runtime reported version 0.3.7.
- The same EXE played four recognized words from prerecorded video in order, before waiting for the patient turn to finish. The local bank contained 401 clips (400 labels plus the uncertainty cue); automatic microphone pause/resume and deliberate mute were preserved. See [packaged readout regression](evidence/workspace-037-packaged-voice.json).

Evidence: [source UI checks](evidence/workspace-037-source.json), [packaged EXE checks](evidence/workspace-037-packaged.json), [doctor screenshot at 1280×720](evidence/workspace-037-doctor-1280.png), [patient screenshot](evidence/workspace-037-patient-1280.png).

Early QA harness runs are retained alongside the passing reports. The initial source harness opened a second speech connection while the UI already owned the microphone; it was corrected to mute the UI first. Initial packaged probes used an incorrect health route and queue property; the corrected probe uses `/healthcheck` and `pending_count`.

These checks use prerecorded video, synthetic speech and a silent test microphone. They do not establish new-signer accuracy, microphone quality, sign-language comprehension or compatibility on a clean Windows installation. Recognition remains a 400-class isolated-word model. The avatar bank remains 67 signs with 65 controlled sentence patterns.
