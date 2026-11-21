# VSL Clinic 0.6.3 — bản vá hiển thị top 1 ngày 13/11/2026

Chủ ứng dụng yêu cầu bỏ beep, trạng thái chưa chắc/màu vàng/dấu hỏi và bước xác nhận; hiện và đọc top 1 tự động theo từng từ. Bản vá này chỉ đổi frontend và đường chọn clip giọng đọc.

- Chat giữ đúng từ top 1 của mỗi kết quả, theo thứ tự nhận; không thêm dấu hỏi hay nhãn yêu cầu đối chiếu.
- Lời người bệnh hiện mỗi từ top 1 màu xanh, top 2 và top 3 đi kèm bên dưới nếu model trả về đủ ứng viên. Màu xanh biểu thị vị trí đầu bảng xếp hạng, không gán trạng thái được con người xác nhận.
- Mỗi từ được đọc ngay bằng clip gốc, không dùng clip ghép beep. Giữ hàng đợi tuần tự, chống đọc trùng, ngắt khi kết thúc phiên và tạm micro khi phát giọng.
- Bỏ hộp kiểm tra/xác nhận từ, chú giải vàng/xanh và thông báo chưa chắc trong giao diện nhận lời người bệnh. Dữ liệu chất lượng nội bộ vẫn giữ để truy vết; không sửa điểm model hay giả ghi confirmed.
- Giữ nguyên model, backend, xử lý môi, hai chế độ nhận và nút VI / EN.

## Cài bản vá

Đây là bản vá trực tiếp của frontend trên bản đã cài 0.6.3, không phát hành lại bộ cài đầy đủ. Build bằng TypeScript/Vite rồi thay thư mục `resources/frontend` trong bản đã cài. Bản gốc và bản build mới được lưu tại `Organization/PatientTop1_2026-11-13`; file `LOCAL_PATCH.json` trong thư mục app xác định các file thay thế và hash source.

`App/0.6.3` và `Installer/VSL-Clinic-Setup-0.6.3.exe` vẫn là bản phát hành song ngữ gốc để quay lại. Chạy lại Setup gốc sẽ đưa giao diện về trước bản vá. Biên nhận BUILD_RECEIPT gốc chỉ mô tả baseline; đọc thêm LOCAL_PATCH để biết frontend hiện đang dùng. Không tuyên bố parity đầy đủ của Setup gốc với bản đã vá.

Lúc cài nhanh, theo yêu cầu không chạy unit/UI/realtime test và chưa commit/sync Git. Ở lượt tiếp theo ngày 13/11/2026, chủ ứng dụng yêu cầu lưu Git: source bản vá và hai kịch bản VSL100 mới được ghi vào Git cục bộ. Không push. Các kết quả runtime trước đây không được dùng làm kết quả kiểm bản vá này.

Shortcut Desktop được đọc lại và cả 7 file frontend đã cài được đối chiếu hash với `LOCAL_PATCH.json`: khớp bản vá `patient-top1-20261113`. Đây là xác minh file của bản cài, không phải chạy lại app hoặc nhận dạng. Các kịch bản mới nằm ở [hai kịch bản VSL100](../demo/VSL100_THEM_2_KICH_BAN_2026-11-13/README.md).
