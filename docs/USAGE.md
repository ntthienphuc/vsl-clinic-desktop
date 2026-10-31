# Using the two-screen app

[← Project overview](../README.md) · [Documentation](README.md) · [Demo scripts, Vietnamese](../demo/HAI_KICH_BAN_2026-10-31/README.md)

The interface is Vietnamese. This guide includes exact UI labels alongside English explanations.

## Prepare

Open `VSL Clinic.exe` from the complete portable folder, or run `npm start` after [source setup](GIT_SETUP.md). Use one Clinic session at a time. **Bố trí màn hình** (Screen layout) supports arrangement, swapping roles and full-screen mode. On one monitor, the two windows share the display.

For a webcam, keep the face, shoulders, elbows and both hands visible. Without a webcam, use **Camera / video → Mở video trên máy** (Open local video) after restoring the demo assets. Concatenated rehearsal clips include pauses and are software fixtures, not natural signed sentences.

## The doctor starts

1. Select the camera/video source.
2. Choose **Tự động** (Automatic) or **Xác nhận trước khi gửi** (Review before sending).
3. Press **Bắt đầu cuộc trao đổi** (Start conversation). Capture starts and the microphone opens when a device and permission are available. Typing remains available without a microphone.
4. Speak one short idea or select an entry in **Chọn câu / từ** (Choose phrase/word).
5. Wait for the avatar to finish, then let the patient respond.

| Mode | Sending behavior |
| --- | --- |
| **Automatic** | Clearly recognized content with supported meaning and complete sign coverage is sent after a pause. |
| **Review before sending** | The doctor checks/edits and explicitly sends each utterance. |

Unclear speech, a length-limited utterance or missing coverage stays in a draft. Choose **Nói lại** (Say it again), select a supported template, or explicitly send the complete text. Unsupported meaning is not silently removed.

Typed example: **“Y tá ơi, đo nhiệt độ nha”** uses reviewed aliases and plays **Y tá → Nhiệt độ → Đo**. For the voice rehearsal, use **“Bác sĩ đo nhiệt độ.”** as scripted; the nurse wording was misrecognized and blocked in an earlier audio test. Negation and dosage are not filler words.

## The patient responds

The patient watches the message and avatar. Capture remains active during the session; there is no per-word start button.

- Each recognized word is sent immediately to **Người bệnh đang nói** (Patient is speaking) on the doctor's screen.
- Hold or lower the hands for roughly **0.7–1 second between words** so the isolated-word model can detect boundaries.
- Pause roughly **1.5 seconds after the final word** to group a turn into history. A pending next-word inference is allowed to finish first.
- **Tôi đã hiểu / Xin giải thích lại** (I understand / Please explain again) are optional feedback buttons.

For example, **Đau → Mệt** (Pain → Tired) appears incrementally, then becomes **Đau và mệt.** after a pause. Original labels remain available. The app does not invent a pain location or symptoms from the doctor's question.

Multiple signs without boundaries may be merged into one movement. Grouping words into history does not turn the 400-word model into a continuous sign-language translator.

## Review, replay and finish

The avatar supports pause, replay and speed changes on the same timeline as text. A lost WebGL context pauses playback until rendering recovers.

For a wrong prediction or low sampling-rate warning, use **Đối chiếu từ vừa nhận** (Review recognized word), reduce heavy processing elsewhere on the PC, and retry. Sample videos can also be misrecognized when resources are constrained.

**Kết thúc** (End) stops capture, microphone and avatar while keeping session history. **Cuộc trao đổi mới** (New conversation) clears in-memory content and invalidates old results. Close both windows to exit the app and engine.

Before presenting, rehearse with the actual signer, webcam and microphone. Fixed-video results do not guarantee recognition of a new voice or signer. See [0.3.4 evidence and limitations, Vietnamese](DEMO_0.3.4.md).
