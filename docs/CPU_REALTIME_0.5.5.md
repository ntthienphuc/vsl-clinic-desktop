# Clinic 0.5.5 CPU INT8 — candidate under verification

The installed Desktop app remains the verified 0.5.3 baseline until the final
acceptance record in `Organization/CPURealtime_2026-11-10/v055` says otherwise.
Do not infer acceptance from the version number or a successful build.

0.5.4 was rejected after an installed full-flow test produced a wrong green
word (Học W082 became W021). The original installer is retained in
`Archive/Rejected/0.5.4`; installed 0.5.3 was restored and every payload file
verified. The user's profile was not changed.

## Current implementation

- Keep the frozen SL-GCN + AV-HuBERT fusion head and the original label order,
  mouth crops and 25-fps model resampling. The independently saved INT8
  artifact quantizes 144 transformer Linear layers; CNN, SL-GCN and head stay
  FP32. Source FP32 weights and baseline app remain available for rollback.
- Keep passive Torch waiting. PoseHands uses two bounded XNNPACK kernel
  threads (graph scheduler two); FacePoints remains one kernel thread. Retain
  the 25-fps observation schedule and use a twelve-frame queue to absorb up to
  480 ms of scheduled video during short CPU bursts. Sustained overload drops
  old frames instead of accumulating an unbounded backlog.
- Assign sequence numbers before enqueue. Missing scheduled observations in
  a word force yellow review, even if the uncalibrated softmax is high. This
  also requires enough observed frames for the 25-fps model timeline (with
  one frame of endpoint rounding tolerance), so a slower camera cannot pass
  merely because its queue never overflowed. This never changes the label.
  Normal 0.75 score/0.20 margin and
  visibility/boundary gates still apply.
- Preview remains on its independent 30-fps branch; it does not supply
  interpolated or JPEG-decoded frames to recognition. Yellow words still beep
  once, speak immediately and show three candidates. Green words speak
  normally. Speaking a word does not confirm it.

## Preserved rejected attempts

The proposed modality-mask agreement check failed on an exact reconstruction
of the rejected input (all logits reproduced with zero error). All three views
agreed on the wrong word. It was removed from production source.

A 20-fps detector candidate also produced a wrong green word despite a complete
sampling sequence. It was rejected; there is no lower detector cadence in the
candidate. `v055/DECISIONS.md` and the preserved failed reports explain the
change without modifying their expected labels or tuning a per-class rule.

## Verification boundary

All app measurements use reused VSL100 videos with visible mouth pixels, fixed
hashes and the same twelve inputs as the old FP32 app. This is a bounded
regression check, not independent accuracy validation across all 100 words or
new signers. Software audio-playing timestamps are not microphone/physical
speaker measurements. Preview frame arrivals are not a photon measurement.

Full EXE/installed UI flow, portable and installed byte parity, CPU speed
comparison, overload/recovery and lifecycle evidence must pass before Desktop
replacement. Actual results are recorded outside the payload, so that a later
installer hash does not require changing its own packaged documentation.

The twelve-frame source trial passed its focused 12-video flow: 11/12 top-1
correct, 9 green/3 yellow, no wrong green and all 12 spoken. Preview transport
was 30.21 fps; last-active-frame to speech p50/p95 was 1754/1913 ms (maximum
2076 ms), and shutdown took 1696 ms. This run omitted the separate mode/UX
block; the final EXE must still pass all 23 checks. The six-frame EXE attempt
failed the useful-green requirement and is preserved rather than accepted.

No live webcam/hospital pilot, training, broad benchmark, push, publication or
board deployment is part of this verification. The models execute on Windows
x64 CPU; avatar WebGL still uses the laptop renderer. Raspberry Pi/Jetson and a
machine with no GPU have not been validated.
