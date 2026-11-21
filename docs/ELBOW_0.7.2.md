# Elbow deformation correction — 15 November 2026

Status: fixed and verified in the 0.7.2 source candidate. Final EXE/install state is recorded separately in `../../Organization/AvatarReview_2026-11-15/ACCEPTANCE.json`.

## Reproduction and cause

In the actual Electron renderer, run Bụng, Sốt, Đo, Nhiệt độ, Bác sĩ, Y tá, Bệnh viện, Khám bệnh and Đau three times, then return to neutral. The previous solver independently transported the upper-arm and forearm frames from their previous frames. Closed movement paths accumulated different axial rotations on the two bones. The sleeve therefore twisted into a pinched elbow even when both hands were resting. `elbow-cycled-before.png` reproduces the user's reported silhouette.

`src/avatar/retarget.ts` now anchors each upper arm at a stable hanging bind reference; each forearm inherits its upper arm's axial orientation and bends toward the solved wrist. The exact overhead antipode retains a previous-frame fallback. Static bind directions and references are cached once. Bone lengths, source motion files and the independently solved hands are retained.

The technical review also considered volume-preserving [dual quaternion skinning](https://users.cs.utah.edu/~ladislav/kavan07skinning/kavan07skinning.html). The observed defect was reproduced as accumulated frame rotation, so this change corrects the arm solver. No new shader, cloth simulation, model or texture is added.

## Evidence

Evidence root: `E:\Project\VSL Clinic\Organization\AvatarReview_2026-11-15`.

- `elbow-cycled-before.png`, `elbow-cycled-fixed.png`: the same 27-sign history before/after correction.
- `elbow-raised-fixed.png`, `elbow-side-fixed.png`: additional bent-arm and oblique rendered views.
- `elbow-fixed-actual/avatar-frames.json`: 10 words, four timed screenshots per word from the real Clinic Electron patient page; all capture runs succeeded. `elbow-actual-neutral.png` shows its final neutral silhouette.
- `elbow-final-motion-audit.json`: actual VRM hierarchy, 200 words and 66 sentence fixtures at 30 Hz, zero numerical failures and zero local bone turns above 90 degrees in a frame. An additional persistent rig traversed all 200 words and returned to the original arm orientations after every word: maximum neutral drift **0 degrees** at the fixed breathing phase.
- `elbow-final-js-regression.log`: **33/33** JavaScript tests passed, including the real-rig regression for closed movement histories and absence of axial elbow twist.
- `elbow-fixed-build.log`: TypeScript and Vite build passed; `git diff --check` passed.

`tools/avatar_rig.mjs` shares the actual GLB hierarchy loader between tests and numerical audits. The persistent-rig audit is essential: creating a new rig for every word would miss this history-dependent failure.

These checks establish the reported elbow correction, not semantic acceptance of every sign. During the image review, Sốt still placed the palm too low relative to the source forehead contact, and Bác sĩ still showed incorrect finger crossing/contact near the forehead. Both were subsequently corrected, followed by the Mẹ cheek anchor and 16 additional handshape corrections. Current evidence: `release-motion-audit.json`, `avatar200-final/`, `hand-final-actual/`, and `hand-final-tests.log` (35 tests). See PROJECT_STATE for the exact review scope and limits.
