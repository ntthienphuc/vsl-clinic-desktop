# Cách dùng VSL Clinic 0.7.3

## Cài ứng dụng

1. Mở `VSL-Clinic-Setup-0.7.3.exe` trong thư mục `01_Cai_dat`.
2. Chọn nơi cài hoặc giữ đường dẫn có sẵn.
3. Chọn GPU NVIDIA nếu máy có NVIDIA; bộ cài chọn sẵn khi phát hiện. Chọn CPU nếu không có NVIDIA hoặc cần dùng ít dung lượng hơn.
4. Bấm **Cài đặt**, chờ xong rồi mở **VSL Clinic** trên Desktop.

Bộ cài R2 không có trang yêu cầu đồng ý giấy phép. Đọc file Word `Giay_phep_VSL_Clinic.docx` nằm cạnh Setup; bản sao được cài trong thư mục `Tai_lieu`. Các giấy phép gốc vẫn đi kèm ứng dụng.

Máy cần Windows 10 2004+/11 64 bit và CPU có AVX2. Khuyến nghị RAM 16 GB, camera, micro, loa và màn hình thứ hai. Không cần cài Python hoặc CUDA Toolkit trước.

## Bắt đầu

1. Bác sĩ mở **Tùy chọn**, chọn **Camera**, chọn đúng camera rồi bấm **Mở thử camera**.
2. Chọn **Ký hiệu + khẩu hình** khi nhìn rõ miệng; chọn **Chỉ ký hiệu** nếu không nhìn rõ miệng. Bấm **Xem 100 từ** hoặc **Xem 400 từ** để xem các từ nhận được.
3. Đóng Tùy chọn rồi bấm **Bắt đầu**. Chỉ bác sĩ bấm nút; người bệnh nhìn màn hình và ký.

## Bác sĩ nói với người bệnh

- **Nói:** khi thấy **Đang nghe bác sĩ**, nói một câu ngắn rồi nghỉ. Câu đủ từ ký hiệu sẽ tự gửi theo chế độ đang dùng.
- **Gõ:** nhập câu, chọn **Ký hiệu** hoặc **Chỉ gửi chữ**, rồi bấm **Gửi** hoặc Ctrl + Enter.
- **Chọn câu:** bấm **Câu mẫu**, chọn nhóm hoặc tìm câu. Bấm câu là gửi ngay.
- **Câu chưa gửi:** bấm **Nói lại** hoặc **Sửa hoặc gửi chữ**. Chỉ chọn gợi ý nếu đúng ý, rồi gửi. Không có gợi ý phù hợp thì giữ nguyên ý và gửi chữ.

Ví dụ “Bác sĩ đo nhiệt độ” được đọc cùng từng ký hiệu Bác sĩ → Nhiệt độ → Đo. Gửi câu mới sẽ chuyển nhân vật và giọng sang câu mới.

## Người bệnh trả lời

Giữ mặt, vai và hai tay trong hình rồi ký từng từ. Với **Ký hiệu + khẩu hình**, đưa tay về nghỉ một nhịp giữa các từ. Với **Chỉ ký hiệu**, có thể giữ tay yên một nhịp sau động tác rồi ký tiếp. Đây là nhịp giúp bản hiện tại tách từ, không phải quy tắc bắt buộc của ngôn ngữ ký hiệu.

Từ đứng đầu hiện trong khung trao đổi và được đọc ngay. Bác sĩ thấy từ số 1 màu xanh, số 2 và 3 màu vàng. Xanh chỉ là thứ hạng đầu; nếu nhận sai, nhờ người bệnh ký lại. Người bệnh có thể ký khi nhân vật vẫn đang diễn.

## Kết thúc

Bấm **Kết thúc** khi xong lượt. Kiểm hai màn hình đã sạch và không còn tiếng trước khi bắt đầu lượt tiếp theo.

**Lưu tạm** chỉ giữ nội dung trong bộ nhớ, mất khi đóng ứng dụng. **VI / EN** đổi giao diện; lời trao đổi và giọng vẫn tiếng Việt. Kho **Từ điển ký hiệu** có 200 từ để xem trước, dùng riêng cho chiều bác sĩ tới người bệnh.

## Nếu gặp khó khăn

- Không có hình: vào Tùy chọn, đổi Camera 1–4 và thử lại.
- Có chữ mà không có tiếng: kiểm âm lượng Windows và biểu tượng loa ở Lời người bệnh.
- Micro nhận tiếng xung quanh: đặt gần bác sĩ, giảm tiếng nền; chọn **Kiểm tra trước khi gửi** trong Tùy chọn.
- Thiếu hoặc lặp từ khi ký: kiểm đúng danh sách từ, đủ tay/mặt trong hình và ký chậm hơn.

Hướng dẫn PDF có ảnh nằm trong thư mục `02_Huong_dan` của bộ bàn giao. Phạm vi hiện tại là nhận từng từ; chưa phải dịch câu ký tự nhiên.
