# VSL Clinic 0.5.4 — CPU INT8

**Rejected release.** The later installed full-flow check produced a wrong
green W021 for Học W082. Desktop was rolled back to verified 0.5.3. The passing
measurements below are historical attempts, not final acceptance. See
[0.5.5 candidate and current verification](CPU_REALTIME_0.5.5.md) and
`Organization/CPURealtime_2026-11-10/v055/DECISIONS.md`.

Build source ngày10/11/2026. Bản này dùng artifact INT8 đã đo ở0.5.3, tối ưu lịch xử lý CPU; không training hoặc đổi head/nhãn/ngưỡng nhận dạng. Thông tin kiểm EXE/cài đặt cuối cùng được ghi bên ngoài payload tại `E:\\Project\VSL Clinic\Organization\CPURealtime_2026-11-10` và `Organization\Installer_0.5.4`; đọc các receipt đó trước khi xác nhận bản đang cài.

## Thay đổi đã kiểm ở source

- PoseHands dùng2luồng XNNPACK có giới hạn, graph2luồng; FacePoints vẫn1luồng. Paired3clip validation: detector44–48ms xuống32–37ms, keypoints/pixels môi/logits khớp tuyệt đối. Giữ ảnh1080 và preprocessing model gốc.
- Native Torch2luồng nghỉ ngay sau việc tính toán (OMP_WAIT_POLICY=PASSIVE, KMP_BLOCKTIME=0) để nhường CPU cho detector/UI.
- Ảnh RGB chuyển cho detector là read-only; camera/preview/inference tiếp tục riêng, queue có giới hạn. Bộ400 warmup detector trước clock capture để giảm bỏ khung hình đầu.
- Source tự chọn `build/multimodal-runtime-cpu` theo deployment, package dùng cùng runtime. Có144Linear INT8 trong transformer; CNN môi, SL-GCN và fusion FP32. Các thử giảm ảnh và gộpCNN không được chọn vì lợi ích/tính tương đương chưa đạt.
- Giữ hai lựa chọn end-user **Ký hiệu + khẩu hình**100từ mặc định và **Chỉ ký hiệu**400từ. Giọng bác sĩ theo từng ký hiệu, từ bệnh nhân đọc ngay; vàng beep nhẹ rồi đọc và top3, xanh đọc bình thường. Giữ ngưỡng0,75/0,20.

408Python checks qua. SourceUI1 dùng12clip VSL100 có môi qua23checks: bộ400, default100/mode switch, câu nhanh, voice/avatar/mouth, yellow beep/top3, sửa/lặp từ, noise/ASR, End, history và shutdown. Có10xanh đúng+2vàng, top1đúng11/12,12/12đọc; một từ vàng sai vẫn phát theo lựa chọn chủ ứng dụng. HaiSốt trong stream đều xanh và đọc riêng. Preview26,76fps; last-active→voice p50/p951254/1493ms; inference p50768ms; exit1,551s. Đây là đo bằng software clocks trên fixture dùng lại; chưa có webcam/người/phòng khám/board thật.

Baseline source `c7eb45a`, tag `baseline/clinic-0.5.3-before-cpu-realtime`. App0.5.3, CPU-INT8-0.5.3-beep và các baseline0.5.2/0.4.1 tiếp tục giữ. Manifest FP32 source trước đổi được lưu ở `Organization/CPURealtime_2026-11-10/source-fp32-manifests`; file trọng sốFP32 nguồn không thay đổi.

## Cài đặt và kiểm cuối

EXE CPU trước cập nhật footer qua đủ 23 checks: 11/12 top-1, 9 xanh + 3 vàng, 0 xanh sai, 12/12 đọc; cả hai Sốt trong luồng đều xanh. Preview 27,97 fps; cuối động tác đến giọng p50/p95 1670/2037 ms. FP32 cũ trên GPU qua cùng luồng: 11/12, 8 xanh + 4 vàng, preview 27,61 fps, giọng 971/1114 ms. CPU nhẹ hơn nhưng chưa nhanh bằng GPU. Fixture 312 giây qua 5 checks về bộ đệm/hàng đợi, đổi nguồn, crash/restart và End; 8 kết quả đúng thứ tự gồm hai Sốt sau mốc 5 phút.

Paired CPU: cùng 12 tensor có môi, 2 lượt mỗi clip, luân phiên FP32/INT8 trung vị 1220/991 ms (giảm 18,75%); chạy đồng thời 1417/1193 ms (giảm 15,75%). Top-1 giống nhau 48/48 cặp, cả hai đúng 11/12 clip; max probability delta 0,005536. Xem `paired-speed-054/REPORT.json`. Các lần lỗi version/observer được giữ trong `EXE_ATTEMPTS.md`. Footer nay lấy phiên bản trực tiếp từ package.json; cần kiểm bản cài sau build cuối. Những kết quả này không phải benchmark toàn VSL100.

`npm run package` tạo `App/0.5.4/win-unpacked` từ deployment CPU active và runtime CPU. Chạy `tools/release_receipt.py`, audit portable, kiểm EXE, rồi `npm run installer`. Setup chỉ thay các runtime riêng trong thư mục app đã cài và bỏ encoderFP32 cũ trong bản cài; profile người dùng nằm ngoài app. Baseline trong project giữ nguyên. Chỉ thay Desktop sau khi candidate và đối chiếu cũ đạt; kết quả cuối tham chiếu các report ngoài payload phía trên.

CPU inference không đồng nghĩa avatar WebGL được kiểm trên máy không có GPU. Raspberry Pi/Jetson là phase thiết bị sau. Chưa chứng minh accuracy toàn100/người ký mới.

Tham khảo quyết định scheduling: [PyTorch CPU tuning](https://docs.pytorch.org/tutorials/recipes/recipes/tuning_guide), [LLVM OpenMP](https://openmp.llvm.org/design/Runtimes.html). Số đo địa phương và tất cả failed/rejected attempts nằm trong `Organization/CPURealtime_2026-11-10`.
