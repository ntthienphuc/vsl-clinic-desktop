# Bộ cài offline VSL Clinic 0.5.2

Mở `Installer/VSL-Clinic-Setup-0.5.2.exe` tại thư mục dự án, cài xong dùng **VSL Clinic** trên Desktop. Bộ cài dành cho Windows x64, mặc định ở `%LOCALAPPDATA%\Programs\VSL Clinic`; profile riêng ở `%LOCALAPPDATA%\VSL Clinic\UserData`. Người dùng không cần Python, Node, server hoặc tải model khi dùng. Chọn gỡ cài đặt **VSL Clinic 0.5.2** trong Windows nếu cần. Giữ model và runtime cùng ứng dụng.

Bản phân phối có SL-GCN + AV-HuBERT và head cross-attention R3, bộ 400 lớp cũ, PhoWhisper, Silero, runtime gợi ý câu, 67 ký hiệu phía bác sĩ, 419 clip giọng người bệnh và 132 clip giọng bác sĩ. Năm checkpoint SPOTER/VLR lịch sử không được engine R3 sử dụng được loại khỏi bản phân phối để bộ cài vừa trong một EXE; các file gốc vẫn giữ ở source/nghiên cứu. Manifest đóng gói và kiểm hash đều dùng đúng danh sách đang hoạt động.

## Kiểm chứng và giới hạn

Lượt cài đầu kiểm trùng toàn bộ 24.108 file nhưng thử EXE thật không đạt tiêu chí tự đọc: 1/12 tự động, 11 chờ đối chiếu. Báo cáo lỗi được giữ ở `Organization/MultimodalIntegration_2026-11-09/packaged-ui-12-installed-final-052`. Không dùng việc cài thành công để thay thế kiểm luồng thực tế.

Đo hẹp hai clip cho thấy lần gọi bộ dò đầu mất 235–265 ms, gây rơi phần đầu video đang chạy. Bản sửa chuẩn bị hai graph bằng ảnh trống trước khi mở nguồn; ảnh trống không vào bộ đệm/tách từ/model. Đối chiếu 16 khung hình có pose sai số 0, điểm mặt và ảnh xám giống tuyệt đối. Không đổi trọng số, ngưỡng, cách tách từ hoặc công thức preprocessing.

Lượt source Electron sau sửa kiểm lại cùng 12 clip VSL100 nguyên hình môi: 8 tự đọc đúng, 4 chờ đối chiếu, 0 tự đọc sai, 11/12 top-1 khớp. Hai từ Sốt liên tiếp tự đọc một lần mỗi từ trước hết lượt. Đủ 20 kiểm chức năng, gồm đổi 100/400, câu nhanh, avatar/giọng/miệng, nhường lượt, im/nhiễu tổng hợp, ASR gửi một lần, Kết thúc và thoát sạch 1,699 giây. Lấy mẫu 13,85–20,38 fps; từ khung hình hoạt động cuối đến chữ p50/p95 829/935 ms, đến giọng tự động 869/945 ms. Đây là timestamp phần mềm và tập cố định rất nhỏ. [Tóm tắt source](evidence/clinic-052-warmup-source-summary.json); [đối chiếu bộ dò](evidence/clinic-052-warmup-parity.json).

Mỗi bộ cài cuối phải có kiểm cài lại, hash đầy đủ và thử chính EXE đã cài. Kết quả sau đóng gói được lưu bên ngoài payload để không thay đổi bộ cài đã kiểm:

- `Organization/Installer_0.5.2/installer-build.json`: kích thước, SHA-256 setup, compiler và receipt payload.
- `Organization/Installer_0.5.2/installed-parity.json`: đối chiếu từng file đã cài, cả model/runtime/giọng.
- `Organization/Installer_0.5.2/installed-runtime-summary.json`: kết quả fixture của EXE đã cài.
- `Organization/Installer_0.5.2/desktop-shortcut.json`: đúng một shortcut Desktop, đúng EXE/profile.
- `Organization/CleanupInstaller_2026-11-10/installation-gate.json`: điều kiện tổng hợp trước xóa chín thư mục cũ đã duyệt.
- `Organization/CleanupInstaller_2026-11-10/cleanup-completed.json`: số file xóa và dung lượng trống đo thực tế; baseline 0.4.1/nghiên cứu được kiểm riêng.

Các đường dẫn `Organization/` tính từ root dự án, không phải thư mục cài app. Hướng dẫn trạng thái cuối nằm tại `E:\Project\VSL Clinic\README.md`. Receipt nguồn/gói nằm trong `BUILD_RECEIPT.json`. Không coi lượt source là kiểm EXE đã cài. Không thử người ký/webcam thật, khẩu trang hoặc tạp âm phòng khám theo phạm vi fixture người dùng chọn. Giấy phép AV-HuBERT giới hạn demo nghiên cứu phi thương mại; chưa phải xác nhận dùng lâm sàng.
