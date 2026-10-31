# Kịch bản demo VSL Clinic — bác sĩ và bệnh nhân

**Dùng cho lần demo hiện tại (0.3.4):** [Hai kịch bản đã chuẩn bị ngày 31/10/2026](HAI_KICH_BAN_2026-10-31/README.md). Mỗi kịch bản có 5 lượt; từng lượt có video gốc đánh số và clip phát thử cả câu. Trong app: **Chọn câu / từ → 2 kịch bản demo**. Phần dưới giữ kịch bản 0.3.3 cũ để tham khảo.

Demo giao tiếp khoảng 5–8 phút, trên một máy tính với hai cửa sổ. Các lời thoại dưới đây là tình huống diễn thử, không phải quy trình chẩn đoán/điều trị.

## Chuẩn bị

1. Đóng phiên Clinic cũ rồi mở bản 0.3.3: `release/desktop-v0.3.3/win-unpacked/VSL Clinic.exe` tính từ thư mục dự án, hoặc dùng shortcut **VSL Clinic 0.3.3** trên Desktop. Để nguyên cả thư mục portable.
2. Bác sĩ mở cửa sổ Bác sĩ; người diễn bệnh nhân mở cửa sổ Bệnh nhân. Khi có hai màn hình, đặt mỗi cửa sổ trên một màn hình.
3. Học video trong `benh_nhan/` trước. Bác sĩ mở Camera / video để chọn nguồn. Chưa có webcam: chọn Video mẫu và một nhãn. Chọn câu / từ mở danh sách 65 từ và 58 mẫu câu.
4. Bác sĩ chọn Tự động hoặc Xác nhận trước khi gửi, rồi Bắt đầu cuộc trao đổi. Camera theo dõi liên tục, micro bác sĩ mở nếu có thiết bị/quyền. Tự động: nói câu có sẵn rồi ngắt khoảng nửa giây, app gửi ngay khi nhận xong. Manual: đọc/sửa câu rồi Gửi ký hiệu. Câu thiếu từ/mẫu câu có cảnh báo Nói lại; bấm để bỏ bản nháp đó và nói câu ngắn hơn. Gửi chữ chỉ khi bác sĩ chủ động chọn.
5. Đợi avatar phát xong rồi bệnh nhân trả lời, không cần bấm nút. Giữ/hạ tay 0,7–1 giây giữa các từ; bác sĩ thấy từng từ ngay. Nghỉ khoảng 1,5 giây sau từ cuối để gom lượt vào lịch sử. Để thử từng MP4 khi chưa có webcam: bác sĩ chọn video và Bắt đầu trong hộp Camera / video.

## Lời thoại và thứ tự tập

| Lượt | Bác sĩ nói/nhập | Avatar theo thứ tự | Bệnh nhân thực hiện | Video học |
|---|---|---|---|---|
| 1 | Bác sĩ khám bệnh. | Bác sĩ → Khám bệnh | Đồng ý | [1.mp4 = Đồng ý](benh_nhan/01_Dong_y_kham_benh/1.mp4) |
| 2 | Bạn có đau bụng không? | Bụng → Đau | Đau | [1.mp4 = Đau](benh_nhan/02_Dau/1.mp4) |
| 3 | Bạn có mệt không? | Mệt | Mệt → Cần → Nghỉ ngơi | [1.mp4 = Mệt](benh_nhan/03_Met_Can_Nghi_ngoi/1.mp4), [2.mp4 = Cần](benh_nhan/03_Met_Can_Nghi_ngoi/2.mp4), [3.mp4 = Nghỉ ngơi](benh_nhan/03_Met_Can_Nghi_ngoi/3.mp4) |
| 4 | Y tá đo nhiệt độ. | Y tá → Nhiệt độ → Đo | Đồng ý | [1.mp4 = Đồng ý](benh_nhan/04_Dong_y_do_nhiet_do/1.mp4) |
| 5 | Y tá giúp đỡ. | Y tá → Giúp đỡ | Cần → Giúp đỡ | [1.mp4 = Cần](benh_nhan/05_Can_Giup_do/1.mp4), [2.mp4 = Giúp đỡ](benh_nhan/05_Can_Giup_do/2.mp4) |
| 6 | Ngồi nghỉ ngơi. | Ngồi → Nghỉ ngơi | Cần → Nước | [1.mp4 = Cần](benh_nhan/06_Can_Nuoc/1.mp4), [2.mp4 = Nước](benh_nhan/06_Can_Nuoc/2.mp4) |
| 7 | Uống nước. | Nước → Uống | Đồng ý → Cảm ơn | [1.mp4 = Đồng ý](benh_nhan/07_Dong_y_Cam_on/1.mp4), [2.mp4 = Cảm ơn](benh_nhan/07_Dong_y_Cam_on/2.mp4) |
| 8 | Cảm ơn. | Cảm ơn | Cảm ơn | [1.mp4 = Cảm ơn](benh_nhan/08_Cam_on/1.mp4) |

## Điểm cần thể hiện trong demo

- Lượt 3: bệnh nhân thực hiện **Mệt → Cần → Nghỉ ngơi**, khung Người bệnh đang nói hiện Mệt trước, rồi thêm Cần, rồi Nghỉ ngơi; không đợi hết lượt. Nghỉ lâu hơn thì gom thành một lượt trong Nội dung trao đổi. Thư mục có `1.mp4 = Mệt`, `2.mp4 = Cần`, `3.mp4 = Nghỉ ngơi`.
- Để xem phép thử hai từ đã chuẩn bị khi chưa có webcam: bác sĩ mở video `research/live-turn-379-204.mp4` từ mã nguồn. Đau phải hiện trước Mệt, cuối lượt có gợi ý Đau và mệt. Clip này ghép hai mẫu từ rời và thêm 800 ms nghỉ, không phải video câu ký tự nhiên; không nằm trong portable.
- Lượt 4: bác sĩ nói **Y tá đo nhiệt độ.** Avatar phát **Y tá → Nhiệt độ → Đo** trong một lượt, không cần bấm gửi từng từ.
- Muốn thử nhiều câu bác sĩ trong một lượt: nhập **Ngồi nghỉ ngơi. Uống nước.** Avatar lần lượt phát **Ngồi → Nghỉ ngơi**, ngắt câu ngắn, rồi **Nước → Uống**. Thử tạm dừng, tiếp tục, phát lại và tốc độ 0,75×.
- Thử ngoài phạm vi bằng **Không đau** hoặc **Uống 2 viên**: app phải giữ nguyên nội dung, không phát phần câu thiếu. Dùng Chỉ gửi chữ nếu muốn chuyển nguyên văn cho bệnh nhân.

## Phạm vi cần hiểu đúng

- Tất cả video bệnh nhân lấy từ dữ liệu local có nhãn đúng trong **400 lớp**; không có từ QIPEDC ngoài model trong thư mục này.
- Số video theo nhãn ký hiệu, không theo số tiếng Việt. “Nghỉ ngơi” là một nhãn, nên một video.
- Ví dụ “Tôi ăn cơm” chưa dùng cho phía bệnh nhân vì nhãn Tôi/Cơm không nằm trong bộ 400 hiện tại. Không thay bằng từ gần nghĩa rồi báo là model đã nhận câu.
- Ở phía bác sĩ, bank mở rộng có một số từ từ QIPEDC như Bụng, Nhiệt độ, Đo. Đây là chuyển động tham chiếu cho avatar; không làm tăng số lớp nhận dạng bệnh nhân.
- Câu hỏi về bụng chỉ được trả lời bằng ký hiệu **Đau** trong kịch bản này; hệ thống không tự thêm vị trí bụng vào kết quả model. Bác sĩ đọc cùng ngữ cảnh câu vừa hỏi.
- Thứ tự ký hiệu là mẫu câu demo đã khai báo. Người ký VSL cần thẩm định nghĩa, nét mặt và độ tự nhiên trước khi dùng cho giao tiếp y tế thực tế.
- Video là mẫu để học, không bảo đảm model luôn nhận đúng người diễn. Nếu sai: đối chiếu video, xem n-best và sửa/xác nhận; đừng giấu lỗi nhận dạng trong demo.

## Nguồn và kiểm tra file

`demo-script.json` lưu từng nhãn, model ID, video ID gốc, đường dẫn, SHA-256, số frame, fps và thứ tự. Script `tools/build_demo_kit.py` kiểm tra toàn bộ video, nhãn và câu bác sĩ khi tạo bộ này. Giữ video local để tập/demo; không tự công bố dữ liệu của người ký.
