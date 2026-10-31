# Hai kịch bản demo — VSL Clinic 0.3.4

**Kết quả mới nhất:** sau khi người dùng tạm dừng hai tác vụ xử lý Lip, giữ nguyên EXE 0.3.4 và chạy hai vòng liên tiếp: **20/20 lượt, 28/28 từ đúng thứ tự**; avatar hoàn tất đủ 20 chuỗi, keypoint 24,3–30 fps. Đây là kiểm thử lặp lại bằng video có sẵn. Các lần trước dưới tải chỉ đạt 8/10 hoặc thấp hơn nên vẫn cần tránh công việc xử lý nặng khi demo. Thử thêm với đúng người diễn, webcam và micro trước buổi trình bày; không coi kết quả video là bảo đảm cho người mới. Chi tiết: `docs/DEMO_0.3.4.md` trong gói.

1. [Tiếp đón và hỏi triệu chứng](01_Tiep_don_va_hoi_trieu_chung/KICH_BAN.md): khám bệnh, hỏi đau/mệt, báo đo nhiệt độ và mời nghỉ.
2. [Nêu nhu cầu và hỗ trợ](02_Nhu_cau_va_ho_tro/KICH_BAN.md): cần giúp đỡ, cần nước, đồng ý, mệt và cần nghỉ.

Mỗi kịch bản có **5 lượt**. Lời bác sĩ cũng nằm trong app: **Chọn câu / từ → 2 kịch bản demo**. Bấm một lượt để điền câu, kiểm tra rồi **Gửi người bệnh**. Không phải gõ lại khi thuyết trình.

## Chuẩn bị trong 2 phút

1. Mở shortcut **VSL Clinic 0.3.4**. Đóng bản cũ trước. Hai màn hình: dùng **Bố trí màn hình → Tự bố trí hai cửa sổ**; kiểm tra chữ **Đã kết nối**.
2. Để demo lặp lại bằng video: bác sĩ chọn câu trong kịch bản và gửi. Khi avatar phát xong, mở **Camera / video → Mở video trên máy**, chọn `CAU_TRA_LOI.mp4` trong thư mục của lượt đó. Không cần micro/camera.
3. Để demo trực tiếp: chọn Camera, chọn chế độ Tự động hoặc Xác nhận trước khi gửi, rồi **Bắt đầu cuộc trao đổi**. Bác sĩ nói từng câu trong bảng, nghỉ khoảng một giây, đợi avatar phát xong mới để người bệnh trả lời.
4. Bệnh nhân học các file `1.mp4, 2.mp4, 3.mp4` theo đúng thứ tự, **0,7–1 giây nghỉ giữa các từ**, khoảng **1,5 giây nghỉ sau từ cuối**. Cần thấy mặt, vai, khuỷu tay và hai bàn tay. Đừng ký cả chuỗi liền không nghỉ: model hiện nhận từ rời.

## Quy ước video

- Các file số là video gốc đúng nhãn trong bộ **400 từ**, được giữ nguyên byte và kiểm tra SHA-256.
- `CAU_TRA_LOI.mp4` là clip ghép để thử phần mềm: thêm 800 ms giữ hình giữa các từ và 2 giây cuối. Đây không phải câu ký tự nhiên của một người. App vẫn chạy detector/model thật; không gán đáp án có sẵn.
- `HUONG_DAN.md` ở mỗi lượt cho biết file số nào là từ nào. `manifest.json` lưu nguồn, hash, thứ tự và lời thoại.
- Trả lời “Đau” sau câu hỏi đau bụng vẫn chỉ nhận ra **Đau**; bác sĩ đọc cùng ngữ cảnh câu hỏi. App không tự thêm vị trí bụng.

## Khi đang thuyết trình

- Với giọng nói, dùng **“Bác sĩ đo nhiệt độ.”** ở lượt 4 kịch bản 1. Trong thử giọng tổng hợp, “Y tá ơi, đo nhiệt độ nha” bị nghe sai; trường hợp đó đã được giữ trong bằng chứng, không tự sửa đoán. Câu y tá vẫn có thể nhập chữ.
- Khi có cảnh báo thiếu ký hiệu: chọn **Nói lại**, nói câu ngắn trong bảng hoặc chọn lại câu có sẵn. Không cố gửi phần câu bị thiếu nghĩa.
- Nếu người ký trực tiếp được nhận sai: dùng **Đối chiếu từ vừa nhận** và sửa/xác nhận công khai; hoặc mở clip dự phòng của chính lượt đó.
- Nếu clip cũng báo thiếu nhịp hoặc nhận sai khi máy bận, tạm dừng phần nhận dạng, đợi máy rảnh rồi thử lại. Clip dự phòng không khắc phục được thiếu tài nguyên xử lý. Có thể mở video gốc để giới thiệu ký hiệu, nhưng phải nói rõ đó là video minh họa.
- Muốn xem kỹ tay: chọn **0,75×** hoặc **Tạm dừng / Phát lại**. Với hai màn hình 16:9, mỗi cửa sổ nên được phóng to trên màn hình riêng.

Các phép thử phần mềm và video giúp giảm lỗi demo. Chúng không bảo đảm nhận đúng mọi giọng nói/người ký mới; nên tập một lượt với đúng micro, camera và người diễn trước buổi trình bày.
