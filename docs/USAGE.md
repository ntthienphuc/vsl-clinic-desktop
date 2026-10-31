# Sử dụng hai màn hình

[← Trang giới thiệu](../README.md) · [Mục lục tài liệu](README.md) · [Hai kịch bản demo](../demo/HAI_KICH_BAN_2026-10-31/README.md)

## Chuẩn bị

Mở `VSL Clinic.exe` từ cả thư mục portable, hoặc chạy `npm start` sau khi hoàn tất [setup từ Git](GIT_SETUP.md). Chỉ mở một phiên Clinic. Menu **Bố trí màn hình** hỗ trợ tự sắp xếp, đổi bên và toàn màn hình; một màn hình thì hai cửa sổ chia đôi.

Với webcam, cần thấy rõ mặt, vai, khuỷu và hai bàn tay. Chưa có webcam có thể dùng **Camera / video → Mở video trên máy** sau khi khôi phục bộ demo. Video ghép để thử phần mềm có nhịp nghỉ; không phải câu ký tự nhiên.

## Bác sĩ bắt đầu cuộc trao đổi

1. Chọn nguồn camera/video.
2. Chọn **Tự động** hoặc **Xác nhận trước khi gửi**.
3. Bấm **Bắt đầu cuộc trao đổi**. Nguồn hình ảnh bắt đầu theo dõi và micro mở nếu có thiết bị/quyền sử dụng. Không có micro vẫn nhập chữ được.
4. Nói từng ý ngắn hoặc chọn câu trong **Chọn câu / từ**. Trong chế độ tự động, một nhịp nghỉ sẽ chốt lời nói; chỉ câu nhận rõ và đủ ký hiệu mới tự gửi.
5. Chờ avatar hoàn tất rồi để người bệnh trả lời.

| Chế độ | Khi nào gửi? |
| --- | --- |
| **Tự động** | Câu nhận rõ, đã qua kiểm tra nghĩa và đủ ký hiệu được gửi sau nhịp nghỉ. |
| **Xác nhận trước khi gửi** | Bác sĩ kiểm tra/sửa và bấm gửi từng câu. |

Nếu nghe chưa rõ, câu dài bị cắt hoặc thiếu ký hiệu, bản nháp được giữ để kiểm tra. **Nói lại** bằng một ý ngắn được hỗ trợ, chọn mẫu có sẵn, hoặc chủ động gửi nguyên văn bằng chữ. App không tự bỏ phần nghĩa chưa hỗ trợ để phát phần còn lại.

Ví dụ khi nhập chữ: **“Y tá ơi, đo nhiệt độ nha”** có alias đã duyệt và phát **Y tá → Nhiệt độ → Đo**. Khi demo giọng nói nên dùng **“Bác sĩ đo nhiệt độ.”** theo kịch bản; mẫu y tá từng bị ASR nghe sai trong thử âm thanh và đã bị chặn. Thêm phủ định hoặc liều lượng không được xem là thêm từ đệm.

## Người bệnh trả lời

Người bệnh xem lời bác sĩ và avatar; camera theo dõi trong phiên, không cần bấm để bắt đầu từng từ.

- Mỗi từ nhận xong được gửi ngay sang khung **Người bệnh đang nói** phía bác sĩ.
- Giữ hoặc hạ tay khoảng **0,7–1 giây giữa các từ** để model từ rời xác định ranh giới.
- Nghỉ khoảng **1,5 giây sau từ cuối** để gom thành lượt trong lịch sử. Nếu từ kế tiếp đang xử lý, app chờ kết quả trước khi chốt.
- Các nút **Tôi đã hiểu / Xin giải thích lại** là phản hồi tùy chọn.

Ví dụ **Đau → Mệt** xuất hiện dần ở bác sĩ, rồi được gom thành **Đau và mệt.** sau nhịp nghỉ. Từ gốc vẫn được giữ để đối chiếu. App không tự thêm vị trí đau hoặc triệu chứng từ câu hỏi của bác sĩ.

Ký liền nhiều từ không có ranh giới có thể bị gộp thành một động tác. Ghép các từ vào lịch sử không biến model 400 từ rời thành bộ dịch câu ký hiệu liên tục.

## Kiểm tra, phát lại và kết thúc

Avatar hỗ trợ tạm dừng, phát lại và thay đổi tốc độ; chữ và chuyển động dùng chung timeline. Khi mất WebGL, phần phát sẽ tạm dừng và chờ khôi phục.

Nếu nhận sai hoặc báo thiếu nhịp quan sát, dùng **Đối chiếu từ vừa nhận** để sửa/xác nhận, giảm công việc xử lý nặng trên máy và thử lại. Video mẫu cũng có thể nhận sai khi máy thiếu tài nguyên.

**Kết thúc** dừng camera, micro và avatar, giữ nội dung trong phiên. **Cuộc trao đổi mới** xóa nội dung RAM và vô hiệu hóa kết quả cũ. Đóng cả hai cửa sổ để thoát app và engine.

## Trước buổi demo

Tập một vòng với đúng người diễn, webcam và micro. Hai kịch bản đã được thử bằng video có sẵn; chưa bảo đảm giọng/người ký mới sẽ luôn được nhận đúng. [Điều kiện thử, kết quả và phạm vi →](DEMO_0.3.4.md)
