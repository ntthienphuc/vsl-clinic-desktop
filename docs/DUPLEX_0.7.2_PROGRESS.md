# Doctor interruption update — 15 November 2026

A new doctor message (typed, quick phrase or accepted automatic speech) now interrupts the previous avatar and its narration. Patient signing remains independent. Unsent ASR drafts do not interrupt. Replaced playback IDs reject late callbacks; text-only delivery clears narration. Candidate and installed evidence must use the updated `probe_duplex.mjs`; older queue-based probe results below are historical.

# Final source update — 15 November 2026

This checkpoint is superseded by [PROJECT_STATE](../PROJECT_STATE.md). Source review now includes all 96 new medoids (12 chronological samples each), 800 actual rendered images for 200 words and a separate 16-word recapture after handshape correction. Elbow accumulation, forehead/cheek anchors and coat hem penetration were corrected. Current JS suite: 35 passed; numerical rig: 266 cases, zero failures, zero persistent neutral drift. EXE/install/cleanup state is recorded only in `../../Organization/AvatarReview_2026-11-15/ACCEPTANCE.json`.

The historical checkpoint below remains for provenance; its remaining-work list describes the earlier state.

# VSL Clinic 0.7.2 — source checkpoint, 15 November 2026

This is active work, not an installed release. The user's revised vocabulary target is **200 total avatar words**, replacing the earlier 500–600 suggestion. The previous installed app and rollback remain until candidate EXE/install acceptance.

## Completed in this checkpoint

- Patient capture, word recognition and correction no longer pause the doctor's avatar. Removed the automatic patient handover state machine. Manual playback pause/stop and patient-window disconnect handling remain explicit controls.
- The doctor's microphone stays open during both avatar narration and patient word readout. Removed the audio gate, its polling timer and automatic recording cancellation. Browser echo cancellation and noise suppression remain enabled; the offline VAD/ASR quality filters remain active.
- One click on a doctor quick phrase sends it. Synchronous duplicate clicks are guarded, the modal closes after a successful request, and unrelated composer text is preserved. Practice instructions now allow patient signing at any time.
- Sleeve displacement uses continuous spatial coordinates instead of inherited skin weights, removing the severe serrated sleeve artifacts seen previously. Broadened jaw, reduced eye opening and adjusted hairline. The coat retains GPU skinning and has no per-frame cloth simulation. Visual polish and source-motion comparisons remain in progress.
- Compact motion files now work with sentence-join annotations without requiring the source JSON in the installed payload. A bounded metadata reader validates format, timing, identity and SHA-256; a regression runs using only packed motions and rejects corrupted data.
- Source provenance explicitly records three signer references for the 96 additions. The original 104 retain their previous reference requirements. The 96 new clips are from local VSL400 references, not newly downloaded QIPEDC videos.

## Current evidence

Evidence folder: `../../Organization/AvatarReview_2026-11-15/`.

- `duplex-source/duplex-probe.json`: actual Electron windows; VSL100 W068 mouth video recognized/read as Sốt while doctor avatar kept playing; synthetic Vietnamese PCM passed through the browser microphone and normal ASR delivery, queued while the first avatar sentence played, then started automatically. Microphone opened once with zero stops during overlap. End cleared both streams. Also checks direct phrase send and duplicate-click protection.
- `duplex-dictionary/dictionary-probe.json`: 200-word dictionary, 375/570/754/1440 px layouts, preview playback/pause, accent-free search, VI/EN, append/disposal, and passive patient screen.
- `duplex-ui/ui-report.json`: doctor/patient layout, phrase library, keyboard focus/Escape, language sync, reduced motion, doctor-only recognition modes and phrase planning. Five viewport sizes.
- `duplex-python-regression.log`: **793 passed** after correcting the old tests' JSON-only assumptions and the packed-runtime dependency. The earlier full run failed 200 hash comparisons; those failures were investigated, not waived.
- JavaScript suite: **32 passed**; TypeScript/Vite build passed. The version bump to 0.7.2 happened after this build, so rebuild before packaging to refresh the frontend version string.
- `voice-integrity.json`: all 169 prior voice manifest entries unchanged; all 265 current WAV entries match their SHA-256. All 200 avatar labels have word-level voice entries.
- `research/motion-storage-evidence.json`: 72,164,680 bytes source JSON → 6,613,972 bytes runtime motion payload, maximum coordinate error 0.000063336 shoulder units. This is motion-storage reduction, not an installer-size measurement or recognition-model accuracy result.
- `avatar200-current/`: current actual-app capture audit is still running, four timed images per word. Inspect the final `avatar-frames.json` and all failures before treating it as complete. Captures alone do not establish semantic sign correctness.

## Remaining before release

1. Complete source-video temporal and avatar comparisons. Existing `visual-notes.json` has 104 detail reviews but only 14 full sampled timeline reviews; `expansion-visual-notes.json` currently has 16 of the 96 new source reviews. Inspect ambiguous fingers at larger scale before changing them. Do not claim all 200 have been fully reviewed.
2. Finish appearance/contact corrections based on these comparisons and review them in actual playback. Bụng and Bác sĩ current renders were visually inspected this checkpoint; the flexed sleeve still deserves a close geometry pass.
3. Rebuild source frontend/engine, package 0.7.2, inspect EXE with both runtime choices and verify source/package hashes and offline assets. Build one CPU/GPU installer, install, verify the canonical desktop shortcut and final installed parity, then remove superseded generated packages/installers per the user's existing cleanup authorization while keeping the immediate rollback.
4. Update root status/release documents and local Git only after the release's actual state is established.

Physical speaker/microphone echo cancellation, live signing, hospital pilot usability and fluent VSL intelligibility are not established by synthetic input or frame captures. No recognition training, large model benchmark, push, publish or deploy was performed.

Geometry references consulted: [Three.js SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html) and [custom BufferGeometry](https://threejs.org/manual/pages/custom-buffergeometry.html). The sleeve change follows shared continuous geometry and normalized joint weights; smooth normals alone do not repair discontinuous displacement.
