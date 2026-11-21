# VSL Clinic 0.6.3 — giao diện Tiếng Việt / English

Ngày 13/11/2026. Bản này nối tiếp 0.6.2, thêm lựa chọn ngôn ngữ giao diện theo yêu cầu chủ ứng dụng.

## Cách sử dụng

Bấm **VI / EN** ở góc trên của màn hình bác sĩ hoặc người bệnh. Ngôn ngữ giao diện đổi đồng thời trên hai cửa sổ và được nhớ khi mở lại ứng dụng. Mặc định là tiếng Việt. Nút dùng được trong phiên, không bắt đầu lại phiên hay đổi chế độ nhận dạng.

English áp dụng cho nút, hướng dẫn, trạng thái, hộp thoại, nhóm câu/từ và nhãn hỗ trợ tiếp cận. **Nội dung bác sĩ/người bệnh, mẫu câu, từ ký hiệu, nhận giọng và giọng đọc vẫn là tiếng Việt.** Đây là giao diện tiếng Anh cho VSL, không phải dịch sang ASL hay nhận giọng tiếng Anh. Các ô nhập/tìm kiếm tiếng Anh nhắc rõ nhập tiếng Việt.

## Thiết kế

- `src/i18n.ts`: trạng thái ngôn ngữ chung, hàm dịch giao diện và cập nhật React. Chỉ dịch tại chỗ hiển thị; không sửa payload gửi backend hoặc dữ liệu hội thoại.
- `src/i18n/en.ts`, `enStatus.ts`: bản dịch cục bộ; không gọi API dịch hoặc tải dịch vụ.
- `desktop/interface-language.cjs`: lưu lựa chọn vào `interface-language.json` trong thư mục hồ sơ Electron, độc lập cổng localhost ngẫu nhiên mỗi lần mở app. Ghi file tạm rồi thay thế; chỉ chấp nhận `vi` và `en`.
- IPC qua preload truyền lựa chọn tới các cửa sổ. Đổi giao diện không remount luồng camera/avatar/micro. Giao diện browser phát triển dùng localStorage cùng origin.
- Các tên từ và câu gốc được giữ nguyên khi đổi giao diện; bộ lọc nhóm vẫn dùng khóa tiếng Việt ổn định.

## Trạng thái bàn giao

Chủ ứng dụng yêu cầu **sửa giao diện, cài ngay và không kiểm thử thêm**. Vì vậy 0.6.3 chỉ thực hiện build/đóng gói, ghi nhận nguồn và cài đặt; không chạy lại unit test, mô phỏng VSL100, kiểm UI hay đánh giá tốc độ. Các thao tác ghi nhận file và bộ cài không phải bằng chứng hành vi runtime.

Bằng chứng build/cài đặt cuối nằm ngoài source tại `Organization/BilingualUI_2026-11-13/DELIVERY.json`. Tài liệu này đi kèm payload nên không tự khẳng định việc cài đặt đã xong. Kết quả realtime 0.6.2 vẫn ở `Organization/RealtimeComfort_2026-11-13/ACCEPTANCE.json` và `KET_QUA_KIEM_THU.md`; không chuyển các kết quả đó thành kết quả test của 0.6.3.

Baseline Git `baseline/clinic-0.6.2-before-english-ui` và portable `App/0.6.2` được giữ để quay lại. Các mốc 0.6.1, 0.5.5 và 0.4.1 vẫn giữ. Sau khi cài xong, Setup cũ chuyển vào `Archive/Rollback/0.6.2`, thư mục Installer chỉ giữ Setup 0.6.3. Không push/publish/deploy.

Lỗi nhận giọng “Y tá giúp đỡ” và biến động khung hình dưới tải đã ghi ở 0.6.2 còn mở; bản đổi giao diện này không tuyên bố khắc phục các lỗi đó.
