# Hai kịch bản hỏi bệnh · 0.3.6

Mỗi kịch bản có 11 lượt. Bác sĩ hỏi từng câu, avatar phát xong thì người bệnh trả lời. Mọi nhãn người bệnh đều thuộc bộ 400 lớp hiện có.

1. [Đau bụng và triệu chứng kèm theo](01_Dau_bung_va_trieu_chung_kem_theo/KICH_BAN.md): hỏi mở, làm rõ vị trí và thời điểm, lạnh/yếu/sốt, đo nhiệt độ và nhu cầu hỗ trợ.
2. [Mệt mỏi, giấc ngủ và ăn uống](02_Met_moi_giac_ngu_va_an_uong/KICH_BAN.md): hỏi cảm giác, lúc ngủ và thức dậy, muốn ngủ, ngon miệng, từ chối hỗ trợ, uống nước và nghỉ ngơi.

Trong mỗi thư mục `01_Tra_loi`, `02_Tra_loi`…: `1.mp4` là ký hiệu thứ nhất, `2.mp4` là ký hiệu thứ hai; `HUONG_DAN.md` ghi thứ tự và câu bác sĩ. `CAU_TRA_LOI.mp4` ghép cả lượt để chạy qua **Camera / video → Mở video trên máy** khi không có webcam. Clip có nhịp nghỉ nhân tạo; không phải câu ký tự nhiên.

Bác sĩ mở **Chọn câu / từ → 2 kịch bản demo** để chọn đúng câu. Có thể nói một câu rồi ngừng; kiểm tra chữ nhận được trước khi tiếp tục. Câu chưa đủ ký hiệu cần nói lại hoặc sửa, không tự bỏ nội dung quan trọng.

Hai video QIPEDC mới chỉ mở rộng phía bác sĩ: “Thế nào” và “Bao giờ”. Câu trả lời `Có` luôn cần đọc cùng câu hỏi trước đó; `Không cần` là một lớp nguyên vẹn, không phải lớp `Không`. `Buổi sáng` nêu thời điểm, không có nghĩa đã đau một ngày. Các tình huống mô phỏng không đưa ra chẩn đoán hoặc đơn thuốc.

`manifest.json` lưu từng câu, model ID, clip gốc và SHA-256. Bộ kiểm thử chạy detector và model thật trên video, đối chiếu nhãn riêng sau nhận dạng; không nạp đáp án vào inference. Kết quả tập bằng video không bảo đảm mọi người ký mới đều được nhận đúng.
