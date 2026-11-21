# VSL Clinic 0.6.2 — quieter incremental readout

Candidate date: 13 November 2026. Runtime, installer and installed acceptance are recorded separately in `Organization/RealtimeComfort_2026-11-13/ACCEPTANCE.json`.

## Patient flow

- Fusion commit score is 0.70 instead of 0.75, with a top-two margin of 0.15 instead of 0.20, per owner request. These are uncalibrated model scores, not percentages of accuracy.
- Missing mouth/hands, insufficient observation and incomplete temporal sampling still require review. The model, class order, original image preprocessing and INT8/FP32 runtime selection are unchanged.
- Every yellow word is still read immediately and stays yellow with three alternatives for the doctor. The first has the existing quiet 120 ms cue. Further yellow words within six seconds of the last actual cue play their normal voice directly; a later yellow word gets another cue. This interval is reset on End, source/session changes, mute and disconnect. Speaking never confirms a word.
- Cues and words remain one continuous WAV when a cue is due. No extra timers delay the audio. Cancellation, corrections, echo protection and duplicate suppression retain their existing lifecycle.
- Before shared image context is added, an elbow segment needs at least 300 ms between its first and last active observations. Brief return motions are recorded as `segment_ignored` and do not become guessed/spoken words. This is a generic temporal heuristic, not a trained non-sign detector. Very fast genuine signs below this duration are not emitted; broader signer testing remains necessary.

## Verification and preserved evidence

The original installed 0.6.1 nine-turn and focused failures remain in `Organization/ContinuousScenario_2026-11-13`. The unchanged 0.6.1 package and local tag `baseline/clinic-0.6.1-before-realtime-comfort` support rollback. Preserve 0.4.1 and 0.5.5 too.

Candidate tests reuse hash-locked VSL100 source clips with visible mouths at 1x realtime and synthetic Vietnamese audio through the real ASR socket. Concatenated isolated words do not prove free continuous signing, unseen-signer accuracy or real clinic microphone behavior. All failed attempts are retained.

Adding general clinical hotwords to PhoWhisper was tested on ten existing authored speech fixtures and rejected: it did not fix “Y tá giúp đỡ” and changed other phrases. No fixture-specific text repair or ASR hotword change ships. The short synthetic “y tá” failure remains an open limitation; speaking that unsupported transcript still requires review.

The earlier full scenario processed approximately 15–17.5 detector frames/s under that machine load. This release does not relabel lost samples as complete or claim a detector throughput fix. Compare actual preview, latency, warning counts and false additions in the external acceptance record.
