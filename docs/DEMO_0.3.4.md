# VSL Clinic 0.3.4 — chuẩn bị demo ngày 31/10/2026

Mở `release/desktop-v0.3.4/win-unpacked/VSL Clinic.exe` hoặc shortcut **VSL Clinic 0.3.4**. Giữ nguyên thư mục portable. Các bản cũ được giữ riêng. Checkout Git cần khôi phục đầu vào cục bộ theo [GIT_SETUP.md](GIT_SETUP.md).

**Cập nhật sau khi người dùng tạm dừng xử lý Lip:** giữ nguyên EXE 0.3.4 và cấu hình, chạy hai kịch bản hai vòng liên tiếp: **20/20 lượt, 28/28 từ đúng thứ tự**, không có từ thừa; mỗi từ hiện trước khi gom lượt và avatar hoàn tất đủ 20 chuỗi. Keypoint 24,3–30 fps, không có cảnh báo thiếu nhịp. Hai kịch bản đã đạt kiểm thử bằng video trong điều kiện này. Các lần thử trước dưới tải vẫn có nhận sai; chưa bảo đảm người ký/giọng nói mới sẽ được nhận đúng.

| Vòng thử sau khi dừng Lip | Lượt đúng trọn vẹn | Từ đúng | Keypoint trung vị | Từ kết thúc ký hiệu đến kết quả trung vị |
|---|---|---|---|---|
| 1 | 10/10 | 14/14 | 27,6 fps | 624 ms |
| 2 | 10/10 | 14/14 | 27,5 fps | 612 ms |

Mốc kết thúc ký hiệu do bộ tách đoạn xác định; độ trễ trên kết thúc tại server, không phải phép đo từ động tác được người đánh dấu đến pixel màn hình. Đây là lặp lại cùng 14 lượt nhận từ trong bộ video, không phải đánh giá độ chính xác trên 28 mẫu độc lập.

## Thay đổi

- Avatar nam theo phong cách bác sĩ trang trọng hơn: tóc ngắn liền, kính mảnh, mắt bớt cách điệu, bỏ viền toon, ánh sáng mềm, áo blouse dài có cúc, bảng tên và ống nghe. Đây vẫn là nhân vật 3D cách điệu. Bộ xương bàn tay và dữ liệu chuyển động không đổi.
- Sửa lỗi semantic router dùng một alias khớp một phần để chặn nhầm đoạn nhiều câu đã được planner hỗ trợ đầy đủ. Ví dụ **Bác sĩ khám bệnh. Bạn có đau bụng không? Uống nước.** giữ đủ sáu ký hiệu; chỉ câu giữa dùng nét mặt hỏi.
- Mất WebGL sẽ dừng đồng hồ ký hiệu, hiện thông báo và chờ tiếp tục sau khi hình ảnh khôi phục. Có thống kê render trong diagnostics cục bộ.
- Bản cuối vẽ avatar tối đa 30 fps khi phát và 12 fps khi chờ, giữ nguyên độ phân giải. Đồng hồ phát vẫn theo thời gian thực, không làm chậm ký hiệu để bù máy bận. Mục đích là giảm tài nguyên vẽ dư thừa; không coi đây là cách bảo đảm nhận dạng đúng.
- Khi tốc độ quan sát thực dưới 12 fps hoặc khoảng trống giữa hai quan sát vượt 250 ms, kết quả bệnh nhân được đánh dấu chưa chắc dù classifier có điểm cao; hiện cảnh báo lấy lại ký hiệu. Từ gốc vẫn truyền ngay; không tự diễn đạt trơn tru một lượt chứa từ chưa chắc. Đây là ngưỡng bảo vệ chất lượng lấy mẫu, không phải bảo đảm đúng khi vượt ngưỡng.
- Thêm **Chọn câu / từ → 2 kịch bản demo**; chọn lượt để điền lời bác sĩ, không tạo sẵn kết quả nhận dạng bệnh nhân.

## Từ vựng thực tế

| Phần | Phạm vi |
|---|---|
| Bệnh nhân → bác sĩ | 400 nhãn từ rời, giữ nguyên ID/model |
| Bác sĩ → avatar | 65 từ: 56 bank local và 9 nguồn QIPEDC đơn |
| Nhóm từ avatar | 27 khám bệnh, 28 giao tiếp, 6 thời gian, 4 sinh hoạt |
| Mẫu câu | 58 mẫu, gồm 40 khai báo và 18 tổ hợp chủ thể/vị ngữ |
| Hai kịch bản | 10 lượt, 14 video từ gốc được sao chép theo lượt, 10 clip ghép để phát thử |

Đủ để trình diễn hai kịch bản được giới hạn rõ. Chưa phải từ điển y khoa đầy đủ: các câu thuốc/liều lượng hoặc nghĩa ngoài bank phải cảnh báo. Runtime chưa có LLM tự do; không dùng mô hình ngôn ngữ để đoán thêm triệu chứng hay đổi top-1 của bệnh nhân.

## Bộ tập và cách demo

[Mở hai kịch bản](../demo/HAI_KICH_BAN_2026-10-31/README.md). Bản 1 là tiếp đón/hỏi triệu chứng; bản 2 là nhu cầu/hỗ trợ. Trong từng lượt, `1.mp4`, `2.mp4`, `3.mp4` là video gốc để tập; `CAU_TRA_LOI.mp4` là clip ghép có nhịp nghỉ để mở trong app.

Để trình diễn lặp lại: chọn câu bác sĩ đã chuẩn bị → chờ avatar hoàn tất → mở clip bệnh nhân của lượt đó. Đây là nhận dạng thật trên video, không gán sẵn kết quả. Để demo người thật, tập lại với đúng micro/camera trước buổi trình bày, nghỉ 0,7–1 giây giữa các ký hiệu.

## Những giới hạn đã quan sát

- ASR trên giọng tổng hợp từng nghe “Y tá ơi, đo nhiệt độ nha” thành “y tá ơi đò nhiệt độ nhà”, và “Y tá đo nhiệt độ” thành “y tở đo nhiệt độ”. Cả hai bị chặn. Kịch bản cuối dùng **Bác sĩ đo nhiệt độ.**, đã qua phép thử âm thanh. Không tự thay từ nghe sai bằng từ gần nhất.
- Video kiểm thử là người ký có sẵn trong bộ demo. Kết quả này không đo khả năng tổng quát cho người mới; các clip ghép không phải câu ký tự nhiên.
- Thứ tự ký hiệu là mẫu demo. Chưa có đánh giá hiểu ký hiệu/ngữ pháp bởi người dùng VSL, thử micro/webcam người thật mới hoặc thử hai màn hình vật lý trong lượt này.
- Bản Windows chưa được ký bằng chứng thư code-signing. Khóa keystore Android không liên quan đến việc ký EXE.

## Bằng chứng

- `evidence/idle-retest-summary-2026-10-31.json`, `rehearsal-idle-exe-run1-2026-10-31.json`, `rehearsal-idle-exe-run2-2026-10-31.json`: kết quả mới nhất sau khi hai tác vụ Lip dừng; cả hai vòng đạt. Hash source runtime, app.asar và engine được đối chiếu để xác nhận không thay code giữa hai điều kiện thử.
- `evidence/build-v0.3.4-2026-10-31.log`: lần đóng gói trước guard. `evidence/build-v0.3.4-final-2026-10-31.log`: 296 test Python, 6 test JavaScript và audit motion sau khi thêm guard.
- `evidence/motion-audit.json`: 124 trường hợp rig, không vượt gate; không phải chứng minh mọi chuyển động đều được người ký hiểu đúng.
- `evidence/rehearsal-source-2026-10-31.json`: hai kịch bản trước khi rút gọn lời thoại nhiệt độ; cả 10 lượt nhập chữ/video đạt.
- `evidence/rehearsal-speech-2026-10-31.json` và `rehearsal-speech-retry-2026-10-31.json`: giữ các lần ASR thất bại.
- `evidence/rehearsal-speech-final-2026-10-31.json`: chạy lại lời thoại cuối bằng giọng tổng hợp qua VAD, ASR, Auto và avatar, có 6 giây im lặng sau mỗi câu.
- `evidence/rehearsal-packaged-2026-10-31.json`: lần đầu thử gói dưới tải chỉ đúng trọn vẹn 4/10 lượt bệnh nhân; không được tính là pass. Avatar hoàn tất cả 10 lượt, đo được 47,5–48,6 fps. Cả source và frozen sau đó đều chỉ đạt 2/4 clip đối chiếu ở khoảng 8–9 fps. Tăng ưu tiên tiến trình chỉ đạt 3/4 và đã được trả lại Normal; thay đổi đó không đưa vào app.
- `evidence/rehearsal-final-exe-2026-10-31.json`: chạy riêng EXE, đúng 9/10 lượt; lượt ba từ ở kịch bản 2 bị nhận thành “Mệt · Xin · Dơ” khi quan sát khoảng 15–16 fps. Đây là ví dụ nhận sai dù cao hơn ngưỡng guard 12 fps. Cả 10 lượt vẫn truyền từng từ trước khi gom câu; cả 10 chuỗi avatar hoàn tất.
- `evidence/rehearsal-render-budget-exe-2026-10-31.json`: EXE cuối, cửa sổ người bệnh phóng lớn từ đầu, avatar giữ 30 fps cả 10 lượt; bệnh nhân đúng trọn vẹn 8/10 lượt. Kịch bản 1/lượt 1: Đồng ý → Bác (9,8 fps, có guard). Kịch bản 2/lượt 1: Cần → Xin (21,5 fps, không có guard). Chuỗi ba từ Mệt → Cần → Nghỉ ngơi đạt ở lần này. Không rút gọn kịch bản để che sự không ổn định; lỗi không chỉ nằm ở chuỗi dài. Truyền từ ngay, gom lượt và chặn nghĩa ngoài bank đều đạt.
- `evidence/build-v0.3.4-render-budget-2026-10-31.log`: biên dịch TypeScript/Vite và gói Electron cuối sau thay đổi nhịp vẽ; engine giữ nguyên bản đã qua 296 test.
- `evidence/quality-guard-under-load-2026-10-31.json`: xác nhận clip bị lấy mẫu thưa hiển thị trạng thái chưa chắc, kể cả kết quả có điểm cao.
- `evidence/playback-controls-packaged-2026-10-31.json`: pause giữ đồng hồ, thay tốc độ giữ pause, resume hoàn tất 3 câu/6 ký hiệu, replay đổi iteration, câu mới vào hàng đợi và stop hủy hàng đợi.
- `evidence/playback-controls-final-exe-2026-10-31.json`: chạy lại cả sáu kiểm tra trên EXE cuối với nhịp vẽ 30/12 fps, tất cả đạt.
- `evidence/webgl-recovery-2026-10-31.json`: mất đồ họa dừng ở ký hiệu Bụng trong chuỗi 6 từ; khôi phục và tiếp tục tới hết.
- `evidence/native-doctor-034.png`, `evidence/native-patient-034.png`: hai cửa sổ EXE ở kích thước lớn, các thao tác chính nằm trong màn hình.

Hai tác vụ xử lý/hash dữ liệu Lip chạy đồng thời trong các lần nhận sai trước; người dùng đã tạm dừng chúng trước hai vòng kiểm thử mới. Sự cải thiện được quan sát trên cùng binary/cấu hình, nhưng không phải phép đo nhân quả cô lập mọi yếu tố. Khi demo, chỉ mở một phiên Clinic và tránh chạy đồng thời công việc xử lý nặng. Vẫn cần thử với đúng người diễn, micro và webcam trước khi chốt demo trực tiếp; các phép thử mới dùng video có sẵn. Nhãn sai và bằng chứng cũ đều được giữ.
