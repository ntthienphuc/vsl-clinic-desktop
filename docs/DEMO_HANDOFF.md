# Bàn giao demo VSL Clinic 0.3.1 — 22/10/2026

**Bản đang chuẩn bị demo đã chuyển sang 0.3.4 (31/10/2026):** xem [DEMO_0.3.4.md](DEMO_0.3.4.md) và [hai kịch bản mới](../demo/HAI_KICH_BAN_2026-10-31/README.md). Nội dung bên dưới là hồ sơ 0.3.1 được giữ nguyên để truy vết.

## Sửa giọng nói 0.3.1

Xem [SPEECH_FIX_0.3.1.md](SPEECH_FIX_0.3.1.md) cho luồng mới và bằng chứng. Câu nói đủ ký hiệu tự gửi; câu thiếu từ/mẫu câu có cảnh báo **Nói lại**. Câu “Bạn cảm thấy thế nào?” hiện cảnh báo, không đổi nghĩa sang câu khác. Silero VAD ONNX thay WebRTC VAD để tránh nhiễu nền sinh bản nháp liên tục. Audio và hội thoại vẫn chỉ ở RAM.

Build `build-v0.3.1.log` hoàn tất: **270 pytest**, **6 test Node**, audit rig không vượt gate, **1.874 file payload** khớp nguồn build. Phần bằng chứng 0.3.0 bên dưới được giữ làm mốc trước sửa; không dùng số đo ASR cũ thay cho bản mới.

## Mở và sử dụng

Mở `release/desktop-v0.3.1/win-unpacked/VSL Clinic.exe` trong dự án, hoặc `VSL Clinic.exe` tại gốc portable. Giữ cả thư mục cùng nhau. Đóng phiên Clinic cũ trước; cơ chế một phiên desktop có thể đưa cửa sổ cũ lên nếu chưa đóng. Các bản trước được giữ nguyên.

Một app mở hai cửa sổ **Bác sĩ / Người bệnh**. Menu **Bố trí màn hình** có sắp lại, đổi bên, mở lại UI bệnh nhân và toàn màn hình. Bố cục ưu tiên 16:9; nội dung dài cuộn trong khung riêng.

1. Bác sĩ chọn nguồn ở **Camera / video**. Chưa có webcam: chọn **Video mẫu** và nhãn; có webcam: chọn camera phù hợp.
2. Chọn **Tự động** hoặc **Xác nhận trước khi gửi**, rồi **Bắt đầu cuộc trao đổi**. Camera và micro bắt đầu; lỗi thiết bị/quyền được hiển thị. Vẫn có thể nhập chữ khi không có micro.
3. Người bệnh làm ký hiệu, không phải bấm nút trước từng từ. **Mỗi từ hiện ngay** ở khung **Người bệnh đang nói** của bác sĩ. Ngắt nhẹ 0,7–1 giây giữa các từ để tạo ranh giới cho model từ rời.
4. Nghỉ khoảng 1,5 giây sau hoạt động/kết quả cuối thì gom lượt vào **Nội dung trao đổi**. App chờ từ đang xử lý xong trước khi chốt. Ví dụ Đau → Mệt: thấy Đau trước, sau đó Đau · Mệt, cuối lượt là gợi ý Đau và mệt. Từ gốc luôn giữ để đối chiếu.
5. Bác sĩ nói từng ý ngắn. Tự động gửi câu nghe rõ và có đủ ký hiệu sau nhịp ngừng. Manual giữ bản nháp để sửa/xác nhận. Câu chưa rõ, quá dài hoặc thiếu ký hiệu luôn chờ xem lại; chọn **Gửi chữ** để gửi nguyên văn.
6. **Kết thúc** dừng camera/micro/avatar, giữ lịch sử. **Cuộc trao đổi mới** xóa phiên RAM sau xác nhận. Đóng cả hai cửa sổ để thoát.

Người bệnh chỉ có preview, avatar, lời bác sĩ và các thao tác tùy chọn: **Tôi đã hiểu / Xin giải thích lại**, tạm dừng/phát lại/tốc độ/xem gần tay. Thiết lập nguồn do bác sĩ điều khiển.

## Kịch bản để tập

Đọc `demo/KICH_BAN_DEMO.md`. `demo/benh_nhan` gồm **8 lượt, 13 video MP4** và hướng dẫn từng folder. Ví dụ `03_Met_Can_Nghi_ngoi`: `1.mp4` Mệt, `2.mp4` Cần, `3.mp4` Nghỉ ngơi. Tất cả thuộc đúng bộ 400; video sao chép nguyên bản, có SHA-256 và decode metadata.

Khi chưa có webcam, mở từng video từ hộp nguồn bên bác sĩ; đổi video sẽ đóng lượt hiện tại. Trong mã nguồn còn có `research/live-turn-379-204.mp4` để thử hai từ trong một lượt: clip ghép hai mẫu, thêm 800 ms nghỉ và cuối video giữ hình để quan sát chốt lượt. Không gọi đây là video câu ký tự nhiên.

Thử phía bác sĩ: **Bạn có lạnh không?**, **Bạn muốn uống nước không?**, **Y tá đo nhiệt độ.**, **Ngồi nghỉ ngơi. Uống nước.**. Có thể gửi một chuỗi mệnh đề và xem avatar phát liên tiếp. **Không đau** hoặc **Uống 2 viên** chưa có đủ ký hiệu; app phải giữ toàn bộ nội dung để gửi chữ, không bỏ phủ định/con số.

## Nội dung bản mới

- Avatar nam, thân/tay áo có skin liền với bộ xương, giảm viền, render sắc hơn; nội suy liên tục và sửa lỗi xoắn cánh tay khi qua hướng đối diện T pose.
- **65 từ avatar:** 56 bank local + 9 QIPEDC. **58 mẫu câu:** 40 khai báo + 18 tổ hợp chủ thể/vị ngữ; tối đa 6 mệnh đề/24 ký hiệu mỗi lượt. Không tự suy rằng mọi chuỗi từ đều có ngữ pháp đúng.
- Recognizer bệnh nhân giữ **400 lớp** và ID gốc. Live word list có n-best, mức chưa rõ và đối chiếu từ mới; lịch sử gom từng lượt. Lượt rất dài chia sau 128 từ mà không mất từ.
- Gợi ý diễn đạt chỉ dùng quy tắc hẹp, không tự thêm triệu chứng/vị trí đau. N-best không bị LLM thay thế. PhoWhisper INT8 CPU chạy offline; không có dịch vụ cloud hoặc LLM trong runtime.

## Bằng chứng nền 0.3.0 (trước sửa giọng nói)

| Phép kiểm | Kết quả và phạm vi |
|---|---|
| Model/planner/live session | **256 test pytest đạt**, gồm hợp đồng 400 lớp, nhận từ trước khi hết lượt, câu dài, epoch, Auto/Manual, giữ phủ định/con số, sửa nhãn và hàng đợi |
| Avatar | **6 test Node đạt**, 124 case audit rig nam, 0 lỗi gate; kiểm tra IK, ngón tay, cổ tay, timeline, hướng đối diện T pose và nội suy không overshoot |
| Video theo clock thật | `runtime-v0.3-duplex.json`: 6/6 top-1 khớp, 0 lỗi capture; avatar đồng thời |
| Word → turn | `live-turn-v0.3.json`: Đau và Mệt đều gửi khi streaming, đúng thứ tự, cuối cùng một lượt; `live-turn-v0.3-no-pause.json` giữ trường hợp gộp từ khi không nghỉ |
| ASR thật | `speech-v0.3.json`: 3 WAV, 3 transcript, truyền PCM theo clock thật; không phải micro thật hay WER |
| Live ASR delivery | Test VAD/ASR fixture kiểm tra gửi trước khi socket kết thúc, không trùng câu, Auto gửi/Manual giữ; không trình bày fixture là giọng người thật |

Trên i7-10750H/16 GB, kết thúc đoạn ký hiệu → server có từ trung vị **579 ms**, p95 **722 ms**; server → WebSocket trung vị **2 ms**; gửi → frame đầu avatar trung vị **41 ms**. Ba WAV: endpoint 540 ms + queue + decode trung vị **1.692 ms**, p95 **1.875 ms**. Mốc phần mềm, không phải photon màn hình hoặc độ trễ hội thoại tự nhiên. Chưa đủ doctor-paint ở mọi video do tab nền nên không gọi số server là tổng độ trễ UI.

### Kiểm tra gói cuối

- `tools/build.ps1` đã hoàn tất mã 0; `build-v0.3-final.log` lưu các gate, đóng gói và đối chiếu **1.873 file payload**. Hai chỉnh sửa nhãn trạng thái UI sau QA được build/đóng gói lại; xem `package-v0.3-final.log` và receipt cuối.
- Frozen `ClinicEngine.exe` trong gói đã chạy trên cổng QA 8774: health **0.3.0, ok, model_loaded=true**; bootstrap đúng 400 lớp, 65 từ, 58 mẫu và avatar nam. `runtime-packaged-v0.3.json` ghi hash engine.
- `live-turn-packaged-v0.3.json`: Đau và Mệt đúng thứ tự, cùng một lượt, đều nhận khi streaming. `live-turn-dom-v0.3.json` ghi DOM thật: Đau hiện trước Mệt **3.174 ms**, rồi **1.538 ms** sau mới đổi sang lượt kết thúc và “Đau và mệt.”. Hai acknowledgment sau render lần lượt cách lúc nhận ở UI **9/10 ms**; đây là hai mẫu, không phải p95 hay benchmark người thật.
- `speech-packaged-v0.3.json`: **3/3 WAV** trả transcript trên frozen engine; giải mã trung vị **1.101 ms**, endpoint 540 ms + queue + decode trung vị **1.641 ms**, p95 **1.776 ms**. Không thử micro thật.
- Hai UI được đo đúng viewport CSS **1366×768** và **1920×1080**, không cuộn toàn trang ở trạng thái đã thử. `ui-layout-v0.3.json` lưu số đo và console. Không có error/warning từ trang gói 8774; một lỗi createRoot từ phiên Vite 5173 trước đó được giữ riêng, không gộp vào kết quả gói.
- Đã thử chọn nguồn, Start/End, chuyển chế độ, nhận video, tìm từ mới, gửi câu nhiều mệnh đề, pause/replay/tốc độ/resume. `avatar-frames-v0.3.json` ghi số frame tăng và cổ tay thay đổi; foreground khoảng **48 fps**, 113 draw call, 53.726 tam giác. Tab Chrome bị che có thể giảm fps; Electron cấu hình không throttle cửa sổ nền.
- Ảnh thật từ frontend của frozen engine: `ui-doctor-v0.3.jpg`, `ui-patient-1366-v0.3.jpg`, `ui-patient-gesture-v0.3.jpg`. Những ảnh này được chụp trước hai chỉnh sửa nhãn trạng thái nhỏ cuối cùng; bố cục, model và chuyển động giống bản cuối.
- **13/13 video học** khớp hash nguồn và giải mã đủ frame khi tạo lại bộ demo. Giữ nguyên video gốc.

Launcher cuối **đã mở thành công** từ `desktop-v0.3.0/win-unpacked/VSL Clinic.exe`, tự sinh engine trong cùng gói và **2 renderer**. Health trả **0.3.0, ok, model_loaded=true**; log khởi động không có lỗi engine/renderer tại lúc kiểm tra. `desktop-launch-v0.3.json` lưu đường dẫn tiến trình, health và log. Để app mở ở trạng thái chờ bác sĩ bắt đầu; camera/micro chưa bật. Kiểm tra trực quan dùng Chrome với frontend của frozen engine, chưa điều khiển/quan sát trực tiếp native Electron.

## Giới hạn cần giữ rõ

Model 400 từ riêng lẻ cần ranh giới giữa từ. Chuỗi ký không nghỉ có thể gộp thành một đoạn. Gom từ thành lượt không phải nhận dạng câu ký hiệu liên tục; câu diễn đạt là gợi ý để bác sĩ đối chiếu.

Audit hình học không xác nhận nghĩa/độ tự nhiên. Ngón tay ở một số từ cần correction lớn; tiếp xúc Sốt/Ngủ với mặt, Bệnh nhân và Ngồi còn cần người ký duyệt. Chưa có collision mesh toàn thân hoặc đầy đủ nét mặt/khẩu hình. Không gắn nhãn chuẩn Đồng Nai.

Chưa kiểm chứng webcam, micro trong hội thoại thực, hai monitor vật lý, máy Windows sạch hoặc mức hiểu của người điếc khi ẩn chữ. Công cụ kiểm tra UI dùng Chrome qua HTTP cục bộ; native Electron sẽ chỉ được mô tả đúng mức đã quan sát/kiểm tra.

## Xác nhận final 0.3.1 sau sửa luồng Auto

Các mục dưới đây là phép kiểm mới của bản `release/desktop-v0.3.1`, tách khỏi bảng mốc 0.3.0 ở trên:

- `npm run package` hoàn tất; receipt xác nhận **1.874 file payload** và hash engine trong gói trùng engine build.
- Mở đúng `release/desktop-v0.3.1/win-unpacked/VSL Clinic.exe` với `ELECTRON_RUN_AS_NODE` được bỏ riêng trong tiến trình kiểm thử: Electron tạo hai UI và `ClinicEngine.exe`; log ghi `ready ... model=400 words`.
- Nhập `Bạn cảm thấy thế nào?` cho thấy cảnh báo thiếu ký hiệu và liệt kê `Bạn, thế, nào`; không tự thay câu bằng nghĩa khác. Ảnh: `docs/evidence/ui-final-unsupported-v0.3.1.png`.
- Gửi `Uống nước.` qua luồng chữ → ký hiệu tạo thứ tự `Nước → Uống`; runtime diagnostics ghi playback `completed`, `pending_count=0`, hai client đã kết nối; avatar nam hiện trên UI người bệnh. Ảnh: `docs/evidence/ui-final-patient-v0.3.1.png`.
- Test tự động bằng audio fixture trên frozen engine: một câu + 40 giây nhiễu chỉ tạo một lượt; câu không có dictionary tạo cảnh báo; câu hỗ trợ tự gửi. Chi tiết: `docs/evidence/browser-unknown-v0.3.1.json`, `browser-auto-v0.3.1.json`, `speech-gate-after-v0.3.1.json`.
- Avatar QA ghi 37 mẫu khung, cổ tay thay đổi và sai số bám tay lớn nhất `4,65e-16`: `docs/evidence/browser-avatar-v0.3.1.json`.

Bản 0.3.0, dữ liệu gốc và thư mục portable cũ vẫn được giữ. Không commit, push hay publish.

Git cha và công việc cũ được giữ nguyên, không commit/push/publish/reset/clean. IDE có thể đặt `ELECTRON_RUN_AS_NODE=1`; mở EXE bằng Explorer hoặc bỏ biến này riêng trong tiến trình con. Không cần thay biến môi trường hệ thống.
