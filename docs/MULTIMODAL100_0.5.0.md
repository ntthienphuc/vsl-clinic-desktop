# Multimodal100 — 0.5.0 local fixture candidate

Reviewed 9 November 2026. Actual multimodal integration and EXE engineering checks
are complete. **Full product robustness is not accepted:** 7/12 EXE clips needed
review in the first complete sweep and 5/12 in the repeat after Lip was closed;
the synthetic mouth cover was not rejected; real incidental-action and mask
fixtures are missing. Three existing out-of-vocabulary clips were subsequently
tested and all stayed in review; general OOV robustness remains unproven.
This is a local candidate, not a validated
clinical release. The user explicitly chose fixture-only verification.
The 0.4.1 portable folder and original `Open Clinic.lnk` remain unchanged.

## Architecture and why

The main patient path uses original contract
`vsl100-r3-spoter-vlr-f01-s17-v2.0`: frozen SPOTER sign encoder plus VLR/Auto-AVSR
mouth encoder and the actual feature-fusion head, with the exact 100 ordered
classes. A private stdio child owns camera/video capture, preprocessing, the
original elbow boundary and inference. Clinic starts and joins this worker;
users do not manage servers or choose between sign/lip/fusion answers.
The independent frozen Clinic engine keeps ASR, avatar planning and sessions
responsive during recognition. Loading the worker does not open the camera.

`multimodal/runtime.py` verifies an immutable staged copy of the original assets.
`DEPLOYMENT.json` resolves all foundations inside the package; the original
manifest remains provenance. `multimodal/preprocessing.py` preserves RGB1080
letterboxing without mirroring, timestamp-nearest 25 fps, the original face
geometry, gray96 mouth crop, center88 normalization, full lip encoding before
96-token selection, sign landmark selection/normalization and FP32 with TF32 off.
Sign runs on CPU while mouth runs on CUDA, following the source schedule.

Optimization removed Holistic's unused terminal face-mesh calculation; the
original separate face detector still provides the crop anchors. Graph execution
uses two threads and each XNNPACK kernel one. Face and pose/hands execute on the
same RGB frame concurrently and both join before advancing. Final numerical
parity is exact on 172 fixed frames, including all features and head logits.
This preserves the model's mathematics; it does not prove recognition quality.

`multimodal/capture.py` keeps one newest-frame slot, two queued segments and one
inference owner. The rolling window is bounded at 270 gray1080 frames or 10.4 s,
with the original 8 s maximum gesture. Snapshots share immutable frame buffers.
There is no five-minute timeout. `backend/multimodal_provider.py` fences old
generations before publishing; End clears session state before in-flight work
drains. Parent EOF and ordinary exit join the child. Failure exposes a short
retry message while the doctor's text/avatar direction remains available.

Auto mode holds avatar playback when the source boundary sees signing with
face and hands. This gives the patient the floor and releases rendering load
before the word result. If no clear word arrives, it resumes after activity and
queued work settle for 1.2 s. A committed/confirmed word converts this into
`patient_reply`, requiring **Tiếp tục** as before. Explicit stop, manual mode
and patient-window disconnect are not overridden. Activity alone creates no word.
Chromium selects the NVIDIA adapter for the actual WebGL avatar; the final EXE
reported GTX 1650 Ti via ANGLE. No OS power setting or unrelated process was changed.

## Words, voice and quality

Each segment has a unique identity, so deliberate repetition differs from a
duplicate callback. W-ID, class index, original gloss, canonical concept,
optional equal-name legacy candidate and voice key remain separate. Multimodal
results use `model_id: null`; they are never presented as legacy400 predictions.
The 82 equal names are lexical candidates, not proof of equivalent signs.

The main path uses fusion only. Missing a branch gives a short retry/text prompt;
it never silently substitutes the old400 model or labels sign-only as fusion.
Internal rollback is retained through `CLINIC_RECOGNITION_PROVIDER=legacy400`,
without a user-facing model selector.

Policy `clinic-fusion-quality-v1` requires a natural completed-word boundary,
both inputs, hand and single-face fractions >=0.6, >=10 observed fps with no gap
over 300 ms, and fusion top score/margin >=0.8/0.25. These prespecified engineering
gates were not relaxed to pass tests. They are uncalibrated closed-set scores,
not a learned sign/non-sign, mask or OOV detector. A low-confidence word is shown
with uncertainty and stays silent until confirmed. The 1.5 s conversation pause
groups already-visible words once; it does not delay per-word display or voice.
Corrections use the corrected text's voice, never a stale original voice key.

All 100 exact display labels have offline WAVs: 82 reuse the equal-text bank and
18 new clips were made from fixed public dictionary labels. Total patient bank:
419 clips, including the retained401. Runtime sends no patient data to TTS.
Doctor narration still has132 clips; the avatar still has67 signs and65 controlled
templates. Adding100 recognition classes does not add100 avatar animations.

## Measured evidence

Canonical run root: `E:\Project\VSL Clinic\Organization\MultimodalIntegration_2026-11-09`.
Selected raw receipts, including failed UI attempts, are copied into
`docs/evidence/multimodal-050-*` and into the portable folder.

| Check/protocol | Final observation | Limit |
| --- | --- | --- |
| Numerical parity, `parity/PARITY.json` | First3 predeclared build16 intervals,172 identical frames: pose, face, gray, boundary, sampling, features and3 head logits max absolute difference0 | Same frames/timestamps/intervals; three heads executed for QA only |
| Regression | 397 Python +23 JavaScript tests passed | Software cases, not human validation |
| Actual EXE, `packaged-ui-12/REPORT.json` | 10 functional checks passed; clean exit0 | Actual WebGL/model/audio with prerecorded video and synthetic/silent mic |
| First complete EXE sweep,12 fixed clips | 5 automatic words,0 wrong among these5;7 review;11/12 first labels match;12/12 clips produce a result | Only6 words ×2 signers; review58.3%; no population accuracy claim |
| EXE repeat after user closed Lip, same12 clips | 7 automatic words,0 wrong among these7;5 review;11/12 first labels match;all10 functional checks pass;exit0 | Review41.7%; repeated inputs, not12 additional independent examples |
| Direct worker, same12 fixed inputs | 7 automatic, all matching;5 review, no omitted clip | Separate protocol without full UI load; do not merge with EXE numbers |
| Same-stream repetition | Two copies of Sốt each shown/read once before stream/turn ends | Same clip twice, not2 independent accuracy trials |
| Long packaged worker |312 s composed video,8 distinct results,5 automatic,3 review; same stream crosses300 s | Synthetic composition; most idle time repeats one neutral frame |
| CPU with CUDA hidden | Actual packaged worker recognizes Sốt;1,051 ms inference,1,520 ms last-active-frame→result | One functional case, no sustained CPU realtime/clean-machine claim |
| Three existing OOV clips, packaged worker | Buổi chiều / Chú ý / Đọc all produced review;0 automatic commits,0 omitted clips | Three prescribed labels outside100; no full UI, incidental-action or general OOV claim |
| Preservation |69 fingerprinted original research inputs unchanged; baseline EXE/asar/shortcut unchanged;3,306 baseline receipt payloads verified | Original dirty work remains preserved; no Git reset/clean |

The12 fixed clips are Học validation + Huy test, take1/camera1, for Mệt, Sốt,
Buồn nôn, Bụng, Nhà vệ sinh and Cần. They were specified before inference and
their source hashes were checked. In the first complete EXE run, the two Học Sốt/Cần clips
needed review solely because EOF arrived without a natural completed boundary.
The other five review cases failed confidence/margin. Huy Mệt's first label was
Ăn and stayed silent. Five automatic outputs matched the fixture labels; this
is **not 100% accuracy**, and the high review rate remains a product limitation.
No comparative improvement over legacy400 has been established.

First complete EXE sweep timing on this i7-10750H/GTX1650Ti machine:

| Interval | n | p50 | p95 |
| --- | ---: | ---: | ---: |
| Inference wall time |12|279 ms|355 ms|
| Backend receives event → UI paint marker |12|28 ms|61 ms|
| Last active sampled frame → UI paint marker |12|744 ms|886 ms|
| Last active sampled frame → audio playing event |5|770 ms|876 ms|
| Frontend audio queue → playing event |5|40 ms|62 ms|

Observed input sampling:15.7–20.1 fps. The longer intervals include the
word boundary wait, preprocessing/queue/inference/IPC and frontend handling.
Paint uses React plus two animation frames; audio uses `Audio.onplaying`.
These are same-host software timestamps, not photon/acoustic measurements.
p95 is descriptive for tiny n; review words do not contribute automatic audio.
Worker model load was7.65 s including2.67 s warm-up, excluding earlier process
startup/import/hash checks; this is not a complete app-start latency.

After the user explicitly reported closing Lip, the same EXE, checkpoints,
thresholds and12 source hashes were tested again. No application code changed.
The repeat passed all10 functional checks and exited normally. Học Sốt/Cần now
had completed boundaries and committed; the other10 dispositions stayed the
same. Sampling16.29–19.29fps; last-active-frame→paint797/935ms p50/p95 (n=12),
→audio861/951ms (n=7). Latency was not lower than the earlier run. Before this
repeat, the process check found no Clinic/VietLip match and the NVIDIA compute
query was empty. This is a load snapshot, not a controlled causal comparison;
the previous sweep was not proven to have Lip active. Do not attribute every
difference to closing Lip. Full comparison and pair identities:
`docs/evidence/multimodal-050-AFTER_LIP_CLOSED_COMPARISON.json`.

The long run observed worker RSS1.189–1.660 GB, max217 buffered frames and no
queued backlog at sampled points. Coded queue/frame limits remain independent
of those observations. Source replacement mid-sign, actual child kill/restart,
and End while signing joined the child without late words. Full EXE End tests
also fenced queued recognition/audio and cleared both windows.

The EXE check covered supported doctor text, real avatar and narration/mouth,
manual pause/resume, microphone guards, a real bundled ASR model with synthesized
speech, patient handover, review correction, repetition and session End.
Both windows fit1280×720 and1920×1080. No physical microphone or acoustic echo
cancellation was tested; the application guards its microphone around playback.

Earlier full-UI attempts under other local GPU/runtime/install load dropped to
5–9 fps and rejected all6 samples. Later GPU/scheduling changes and activity
handover addressed the measured resource contention. Those failures remain in
evidence; final results do not guarantee the same speed under arbitrary load.

## Explicit failed or unverified requirements

- **Covered mouth:** the final synthetic tracking rectangle still produced one
  committed Sốt at0.956. It matched the source positive clip but fails an
  occlusion-rejection expectation. Face geometry can look valid through an
  obstruction. There is no proven automatic mask/usable-mouth detector.
- **Other synthetic cases:** no-face produced unavailable/no speech; lower-body
  blackout produced a review candidate/no speech; translated static rest
  produced no word. These are pixel transformations, not real masks/actions.
- **Non-sign:**0 emitted words in4.35 min of repeated static rest, plus no word
  for translated rest. This is0/min on those synthetic rests only. There is no
  defensible rate for adjusting glasses, scratching, drinking or natural camera
  motion. No annotated real negative fixtures were available.
- **OOV and continuous signing:** three additional packaged legacy samples were
  selected before inference: `003.mp4` Buổi chiều, `043.mp4` Chú ý, `391.mp4` Đọc.
  Catalog IDs/labels were cross-checked and all are outside the100 label mapping.
  The actual packaged worker returned Sốt(0.359), Tiếp tục(0.142) and Cười(0.606),
  respectively; all3 remained review solely for ambiguous classification.
  Both modalities and natural boundaries were available; no clip was omitted.
  Plan/source SHA-256 and raw outputs: `oov3/PLAN.json`, `oov3/REPORT.json` under
  the canonical evidence root, copied as `docs/evidence/multimodal-050-oov3-*`.
  These are3 deliberate signs, not incidental movements. A closed-set classifier can assign a high
  score to an out-of-vocabulary movement. Individual-word boundaries remain
  necessary. Continuous sentence translation, calibrated abstention and general
  non-sign rejection are not solved by this integration.
- **Review rate:**58.3%, then41.7% on the same small EXE set needed review; this does not meet a
  claim of effortless automatic conversation. Do not hide this behind0/5 wrong
  automatic outputs or select only the easy Sốt demonstration.
- **Live scope:** the user chose fixtures only. Webcam unplug/reconnect,
  new live signers, real masks, physical mic/speaker echo, comprehension and
  clinical outcomes remain untested. Software lifecycle simulation does not
  establish physical device behavior. No clean Windows machine was available.

The engineering integration is concrete and reviewable. Full acceptance of the
natural-conversation requirements remains open pending appropriate negative
fixtures and measured robustness, not another generic confidence threshold.

## Package, data and repeatable checks

New EXE: `E:\Project\VSL Clinic\App\0.5.0\win-unpacked\VSL Clinic.exe`.
Keep the complete portable folder. It contains the frozen engine, isolated
CPython3.11.9/Torch2.6.0+cu124/MediaPipe0.10.21/OpenCV4.11 runtime, every pinned
multimodal foundation/head/label,419 patient WAVs,132 avatar WAVs, PhoWhisper,
Silero, avatar assets, six main sample videos, notices and receipts.
`python311._pth` is relative and isolated. Actual EXE tests removed development
Python/FFmpeg from PATH; no research source path was needed by model resolution.

Large immutable files use ordinary NTFS hardlinks where possible, not symlinks.
They remain usable if an original directory is removed. Do not overwrite linked
weights/DLLs in place; replace paths on future updates. Camera RGB, keypoints and
mouth pixels stay in bounded RAM. Explicit fixture QA writes to Organization;
manual video opening uses the existing local temporary-file mechanism. No
patient recording/upload, training, large benchmark or remote deployment occurred.

`npm.cmd run package` rebuilds the frozen backend and its `ENGINE_BUILD_INFO.json`,
frontend and Electron payload, then stages all runtime assets. After final docs,
`tools/release_receipt.py` verifies backend source/build hashes, desktop asar and
production manifest, frontend, runtime/model/voice payload hashes and copies
the evidence/docs. It writes `docs/evidence/release-receipt.json` and packaged
`BUILD_RECEIPT.json`. `tools/audit_portable.py` independently checks that receipt
and manifests; its final output is `Organization/.../PORTABLE_FINAL.json`.

## Demo ngắn bằng fixture

1. Đóng phiên Clinic khác. Mở EXE0.5.0 trong đường dẫn trên, giữ nguyên shortcut
   `Open Clinic.lnk` của baseline0.4.1. Hai cửa sổ bác sĩ/người bệnh tự mở;
   chờ phần nhận dạng chuẩn bị xong, không chạy server riêng.
2. Trong **Camera / video**, chọn ví dụ **Sốt** rồi **Bắt đầu cuộc trao đổi**.
   Từ đủ rõ xuất hiện và được đọc ngay sau động tác, không đợi gom hết câu.
   Thử cả Mệt/Buồn nôn/Bụng/Nhà vệ sinh/Cần để thấy các trường hợp cần đối chiếu.
3. Gửi câu hỗ trợ **Bác sĩ đo nhiệt độ.** hoặc **Bạn có đau bụng không?**.
   Kiểm avatar3D, giọng nam và miệng; thử tạm dừng/**Tiếp tục**. Khi người bệnh
   bắt đầu ký ở Auto, avatar nhường lượt; từ đã xác nhận được đọc một lần.
4. Với từ có dấu chưa chắc, dùng **Đối chiếu từ vừa nhận**, sửa/xác nhận; giọng
   phải đọc nội dung đã sửa. Không dùng điểm số làm bằng chứng cho khẩu trang/OOV.
5. Nhấn **Kết thúc** khi đang phát: hai màn hình, camera, lời nói và hàng đợi
   phải dừng/xóa; từ phiên cũ không quay lại. Đóng cả hai cửa sổ để thoát.

Các kết quả nêu trên là kiểm phần mềm bằng fixture trên máy này. Bản0.5.0 vẫn là
candidate vì các mục còn mở ở trên; không thay thế baseline hoặc tuyên bố hoàn
thành100% yêu cầu chất lượng tự nhiên.
