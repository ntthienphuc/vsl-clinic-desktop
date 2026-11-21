# VSL Clinic 0.5.3 — giọng từng từ, preview và thử INT8

Ngày 10/11/2026. Bản chính tiếp tục dùng SL-GCN + AV-HuBERT cross-attention, chọn GPU khi có. Bản thử CPU/INT8 được lưu riêng, không thay checkpoint FP32 hoặc baseline 0.5.2. Baseline Git `e1a105510fca68471e6f68e460450a969df4c910`, tag `baseline/clinic-0.5.2-before-voice-preview`; công việc mới trên `work/voice-preview-cpu-053`.

## Hành vi sử dụng

- **Bác sĩ → người bệnh:** mỗi clip giọng bắt đầu cùng ký hiệu tương ứng. Ví dụ nhập “Bác sĩ đo nhiệt độ.”, avatar ký và đọc **Bác sĩ → Nhiệt độ → Đo**. Nội dung chữ vẫn giữ câu gốc. Dùng clip từng từ sẵn có; không sinh lời mới. Nếu clip dài hơn động tác, giữ tư thế cuối đến hết tiếng. Pause, replay, nhường lượt và End dùng chung đồng hồ.
- **Người bệnh → bác sĩ:** đọc ngay cả từ xanh và từ vàng, theo yêu cầu chủ ứng dụng. **Xanh** là app nhận rõ hoặc đã xác nhận; **vàng + ?** là chưa chắc. Trước mỗi từ vàng có một beep nhỏ 120 ms (biên độ đỉnh 5% toàn thang), rồi đọc từ; ba gợi ý hiện để bác sĩ chọn hoặc sửa và xác nhận. Từ xanh đọc bình thường, không beep. Việc đọc không tự xác nhận từ. Sửa sang từ khác phát lại lời sửa; xác nhận cùng một từ không đọc trùng. Hai lần ký cùng một từ vẫn đọc hai lần. Bản tạm/lịch sử không tự phát lại.
- **Ngưỡng:** score 0.80→0.75 và chênh lệch top-1/top-2 0.25→0.20. Đây là điều chỉnh theo yêu cầu, không phải xác suất đã hiệu chuẩn. Các điều kiện có tay, mặt, môi, mật độ frame và ranh giới từ giữ nguyên. Từ xanh vẫn có thể sai; từ vàng có thể được đọc sai và cần đối chiếu.
- **Preview:** nhánh riêng giữ tối đa một frame mới nhất, mục tiêu 30 fps, JPEG cạnh tối đa 640, chất lượng 75. Không nội suy frame giả; không đưa preview/JPEG vào model. Nhánh nhận dạng giữ frame gốc, timestamp và preprocessing. Nếu máy bận, preview bỏ frame cũ để không tích trễ.

## Kiểm source đã đo

408 kiểm Python, 26 kiểm JavaScript và build TypeScript/Vite đạt. Source Electron trước thay đổi beep qua 22 kiểm luồng bằng 12 clip VSL100 có hình môi và fixture bộ400; không có người/camera/phòng khám thật ở lượt này. Báo cáo đầy đủ: project-root `Organization/MultimodalIntegration_2026-11-09/source-ui-final-voice-preview-053-source3/REPORT.json`.

Trong lượt source này, 12 từ đều có giọng, top-1 khớp 11/12: 8 xanh đúng, 4 vàng (3 đúng, 1 sai). Không được mô tả “0 từ đọc sai”: từ vàng sai cũng phát tiếng theo hành vi đã chọn. Thao tác sửa qua UI là QA, không tính thành model nhận đúng. Ngưỡng thấp hơn không thay đổi quyết định trên chính 12 logits ở lượt này; không tuyên bố accuracy tăng.

Ba sự kiện phát giọng Bác sĩ/Nhiệt độ/Đo lệch thời điểm bắt đầu ký hiệu lần lượt 16.7/1.7/31.7 ms trên đồng hồ phần mềm. Preview thực nhận 26.82 fps, 71 JPEG khác nhau, khoảng cách frame p95 64.8 ms. Đây là thời điểm vận chuyển ảnh và sự kiện audio của Electron, không phải đo màn hình/âm thanh vật lý. Detector thực xử lý khoảng 13–16 fps. Kiểm bao gồm hai chế độ, từ điển, 24 câu nhanh, sửa nội dung, mic guard, nhiễu tổng hợp, ASR, lặp từ, tạm dừng, End và thoát sạch.

Các lỗi source trước khi sửa khung đối chiếu vẫn ở `Organization/VoicePreviewCPU_2026-11-10/source-ui*.log`. Khung xác nhận từng bị khuất ở 720p; bản sửa đưa hành động đối chiếu trước danh sách tích lũy. Các kiểm EXE, cài đặt và CPU cuối được lưu riêng trong cùng hồ sơ; chỉ các report `passed: true` mới là bằng chứng đạt.

## EXE có beep và ba gợi ý

Lượt `packaged-ui-12-voice-preview-053-exe2/REPORT.json` đạt 23 kiểm (gồm thoát sạch). Trên 12 clip cố định: 7 xanh đúng, 5 vàng (4 đúng, 1 sai), cả 12 từ đều được đọc. Mỗi từ vàng có đúng một beep kết thúc trước lời đọc; từ xanh không beep. Ba gợi ý hiển thị trong vùng đối chiếu ở 1280×720; chọn gợi ý cập nhật ô xác nhận. Đã kiểm sửa sang từ khác dùng đúng clip giọng, từ lặp đọc mỗi lần một lần, mic ngừng thu khi app đọc, giọng bác sĩ theo ba nhịp avatar và End chặn kết quả cũ.

Preview nhận 26.19 fps với 71 ảnh khác nhau. Từ frame tay hoạt động cuối đến chữ p50/p95 900/1031 ms; đến giọng 1038/1163 ms, tính cả beep của 5 từ vàng. Inference p50/p95 343/434 ms. Toàn EXE/backend/worker thoát sạch trong 2.384 s. Đây là clock phần mềm trong 12 fixture dùng lại, không đo loa/màn hình vật lý và không đại diện accuracy bệnh viện. Source3 và EXE1 là evidence trước beep; EXE2 mới là kiểm hành vi cuối.

Bản thử CPU cùng giao diện mới ở `Experiments/CPU-INT8-0.5.3-beep/VSL Clinic.exe`; bản `CPU-INT8-0.5.3` trước beep được giữ nguyên để đối chiếu. Chạy nguyên thư mục ứng dụng, không chỉ chép EXE. Bản CPU không thay shortcut chính. Các báo cáo cuối nằm ngoài payload để tránh tự thay hash gói sau khi cài: `Organization/VoicePreviewCPU_2026-11-10/SUMMARY.json`, `PRESERVATION.json`, `HANDOFF.md` và `Organization/Installer_0.5.3`. Báo cáo CPU và installed có trường `available`/`passed`; không suy ra chúng đạt chỉ từ kết quả portable ở trên.

## Vì sao thử dynamic INT8

So sánh nhỏ trên cùng ba tensor pixel VSL100 có môi đã khóa SHA-256, hai lần chạy ấm, hai luồng CPU, Intel i7-10750H. Không training và không chạy lại tập900 video. Lượng tử hóa lớp Linear của transformer (FFN, Q/K/V/output) giữ CNN môi, SL-GCN và fusion head ở FP32. Dynamic quantization tránh đổi preprocessing hoặc cần fit calibration. Đây là phép thử thực dụng trong Torch2.6 đã pin; không nâng toàn bộ dependency chỉ để dùng API mới.

| Biến thể | Median xử lý một đoạn, 3 mẫu | File encoder |
| --- | ---: | ---: |
| FP32 nguyên bản | 844.83 ms | 1,300,757,315 byte |
| FP32 nhánh attention tường minh | 853.50 ms | như trên |
| INT8 FFN | 725.42 ms | 696,840,090 byte |
| INT8 FFN + Q/K/V/output | 718.88 ms | 394,933,626 byte |

INT8 đầy đủ transformer giảm file encoder khoảng 69.6%, nhanh hơn FP32 nguyên bản khoảng 14.9% trong phép đo nhỏ. Ba top-1 giữ nguyên, độ lệch xác suất lớn nhất 0.001311 (khoảng 0.131 điểm phần trăm); đây không phải độ lệch accuracy toàn bộ100 nhãn. Bản nạp trực tiếp bằng runtime CPU cho logits giống hệt bản lượng tử hóa trong RAM trên ba input (max delta0); working set1076.7MiB, peak1083.0MiB. Baseline eager FP32 working set1807MiB, peak2925.9MiB. Peak FP32 gồm giai đoạn nạp trọng số; phép thử nạp trực tiếp tránh dựng lại toàn bộ FP32 trước khi chuyển INT8. Báo cáo FP32 đầu có bộ nhớ0 do lỗi phép đo, không dùng con số đó.

Evidence: `Organization/VoicePreviewCPU_2026-11-10/cpu-*/REPORT.json`, `CPU_DIRECT_LOAD.json`, `CPU_INITIAL_COMPARISON.json`. Bản thử dùng Torch2.6.0+cpu và artifact riêng có manifest/hash; source runtime CUDA và encoder gốc giữ nguyên. Bản chính vẫn tận dụng GPU của máy này vì ~0.7 giây CPU cho mỗi đoạn chưa nhanh hơn GPU. Dung lượng toàn app vẫn gồm avatar, giọng, ASR, bộ400 và UI; giảm encoder không đồng nghĩa toàn app giảm69.6%.

Tài liệu phương pháp: [ONNX Runtime quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html), [PyTorch quantize_dynamic](https://docs.pytorch.org/docs/main/generated/torch.ao.quantization.quantize_dynamic.html). Tài liệu hiện tại ưu tiên API TorchAO mới; phép thử này giữ runtime Torch2.6 đã kiểm để giảm thay đổi phạm vi.

## Raspberry Pi / Jetson — phase sau

Chưa chạy trên ARM hoặc Jetson. Windows x64 EXE/runtime không dùng trực tiếp trên các máy đó. Cần dựng Linux/ARM64 runtime, kiểm MediaPipe/ASR/Electron hoặc renderer trình duyệt và đo toàn pipeline trên camera thật. Raspberry Pi5 dùng Arm Cortex-A76; số đo i7 không dự báo được fps trên Pi. Jetson Nano đời cũ (Maxwell) khác Orin Nano; phải chốt đúng board/JetPack rồi chọn FP16/INT8 theo hỗ trợ phần cứng. Không coi file CPU INT8 hiện tại là TensorRT engine.

Tham chiếu: [Raspberry Pi processors](https://www.raspberrypi.com/documentation/computers/processors.html), [NVIDIA TensorRT support matrix](https://docs.nvidia.com/deeplearning/tensorrt/archives/tensorrt-843/pdf/TensorRT-Support-Matrix-Guide.pdf). Mốc cho phase sau: giữ nhãn/preprocessing, đối chiếu cùng pixels, latency từng từ + preview + RAM + nhiệt khi chạy lâu; không training nếu chưa có quyết định mới.
