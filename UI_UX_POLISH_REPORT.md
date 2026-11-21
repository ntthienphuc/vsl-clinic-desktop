# VSL Clinic 0.7.2 — avatar, kho từ và hội thoại song song

15/11/2026. Trạng thái hiện hành và giới hạn: [PROJECT_STATE](PROJECT_STATE.md). Biên nhận cài đặt cuối: `../Organization/AvatarReview_2026-11-15/ACCEPTANCE.json`; cần `passed: true` để xác nhận bản cài đã nghiệm thu.

- Sửa khuỷu tay bị xoắn sau lịch sử chuyển động, tay áo liền và vạt áo không xuyên quần. Điều chỉnh khuôn mặt, tóc, áo blouse/cà vạt xanh và thẻ bác sĩ theo ảnh tham khảo.
- Kho 200 từ có tìm không dấu, xem trước 3D, tạm dừng xem trước và thêm vào câu. Motion nén khoảng 6,31 MiB; tải theo nhu cầu và giữ bộ đệm hữu hạn.
- Câu mẫu gửi ngay bằng một lần bấm; bỏ cơ chế tự nhường lượt. Người bệnh ký/được đọc từ và bác sĩ nói đồng thời; câu bác sĩ mới thay ngay câu đang phát; vẫn dừng hết bằng Kết thúc.
- Kiểm source: 793 Python, 35 JavaScript, build; 266 motion cases và 200 lượt capture thật. 96 video đại diện mới được rà theo 12 mốc/từ, nguồn/hashes giữ nguyên. Bản sửa 16 hình tay được chụp lại riêng.

Phần dưới là lịch sử vòng thiết kế 0.7.1. Các kết quả ở đó thuộc checkpoint tương ứng, không thay cho biên nhận 0.7.2.

# VSL Clinic 0.7.1 — thiết kế lại không gian trao đổi

15/11/2026. Baseline 0.7.0/e790e23, tag `baseline/clinic-0.7.0-before-minimal-redesign`. Một vòng thay đổi có chủ đích theo phản hồi chủ app.

## Thay đổi đã áp dụng

- Bác sĩ: thay bố cục nhiều card/hai cột bằng một mặt hội thoại. Lời người bệnh, lịch sử, trạng thái giọng và soạn lời cùng một trục đọc. Bắt đầu/kết thúc ở góc phải; tùy chọn camera có nhãn rõ.
- Soạn lời: nút gửi gọn, thư viện ở ngay thanh nhập, hai chế độ ký hiệu/chữ có trạng thái chọn; vẫn hỗ trợ gõ, nói, Ctrl+Enter, sửa câu chưa gửi và kiểm ý chưa đủ ký hiệu.
- Người bệnh: avatar và nguyên câu bác sĩ chung một mặt; camera là vùng phụ. Bỏ dòng sẵn sàng trùng lặp và vòng trang trí quanh avatar. Không có nút bấm.
- Thị giác: Segoe UI cục bộ, xanh trầm, nền trung tính, đường phân cách nhẹ, kích thước chữ và bán kính thống nhất. Màu kết quả top 1 xanh, top 2–3 đi kèm.
- Câu mẫu: dạng danh sách nhẹ thay cho nhiều ô viền; giữ 8 câu hay dùng, 6 nhóm, tìm không dấu, tab từ và tập trao đổi.
- Code: thay 940 dòng bố cục tích lũy bằng module `src/workspace/{shell,doctor,patient,dialogs}.css`, tách `speech-panel.css`; giữ cấu trúc component và các hợp đồng nghiệp vụ.
- VI/EN: bổ sung các chuỗi mới vào từ điển hiện hành. Nội dung ký hiệu và giọng giữ tiếng Việt.

## Kiểm thực tế

TypeScript/Vite build, 32 kiểm JavaScript và 599 kiểm Python đạt. UI Electron thực tế được kiểm trước và sau ở 375, 570, 754, 768 và 1440px: không tràn ngang; màn hình desktop vừa khung, màn hình hẹp cuộn được. Tìm kiếm, trạng thái rỗng, Escape/trả focus, ngôn ngữ chung, giảm chuyển động, tùy chọn bác sĩ và màn hình bệnh nhân thụ động đã kiểm.

Ảnh hiện hành: [bác sĩ](docs/media/product071-doctor.png), [câu mẫu](docs/media/product071-library.png), [người bệnh](docs/media/product071-patient.png). Bằng chứng ứng viên EXE nằm tại `../Organization/UIRefresh_2026-11-15/`; checkpoint này chưa có biên nhận ACCEPTANCE cài đặt. Báo cáo build không thay cho kiểm cài.

Model, từ điển nhận dạng và runtime CPU/GPU kế thừa bản 0.7.0. Bộ cài offline giữ lựa chọn CPU/GPU. Không suy ra accuracy mới hoặc hiệu năng trên mọi máy từ kiểm UI.

Giới hạn: chưa có user study với bác sĩ/người ký, kiểm người dùng screen reader, tiếng ồn bệnh viện hoặc máy Windows sạch khác. Motion cần người thông thạo VSL đánh giá. AV-HuBERT giữ điều kiện nghiên cứu phi thương mại.

## Tối ưu theo yêu cầu bổ sung

- Lịch sử giữ cùng tham chiếu khi snapshot chỉ thay đổi camera. Component lịch sử được memo hóa; vẫn cập nhật ngay khi nội dung, từ sửa, trạng thái hoặc top ứng viên thay đổi. Tự đăng ký đổi ngôn ngữ nên memo không giữ nhãn VI cũ khi chuyển EN.
- Bộ đệm chỉ giữ lịch sử mới nhất. Xóa map đánh dấu/thời gian kết quả khi đổi phiên, tránh giữ tích lũy sau nhiều phiên.
- Bỏ timer kiểm giọng avatar 25 lần/giây ở cửa sổ người bệnh vì cửa sổ đó không dùng timer này. Nhịp giọng/nhép miệng và rAF 3D giữ đường thời gian hiện hành.
- Không thêm thư viện runtime. Model và voice không được nhân bản cho thiết kế mới. Đã kiểm correction/top ứng viên/reset cùng tối ưu bộ đệm; bằng chứng đo UI thực tế nằm ngoài gói trong thư mục nghiệm thu.

Đo giới hạn trên EXE ứng viên: 100 tin nhắn, 40 lần cập nhật ô nhập. Thời gian chờ hai animation frame trung vị 13,9ms, P95 14ms trên màn hình của máy này; không phải đo độ trễ bàn phím/hiển thị vật lý và không chứng minh tăng tốc so với baseline. Cửa sổ người bệnh có 66 DOM node lúc kiểm; avatar chờ khoảng 12fps theo giới hạn tiết kiệm hiện hành. Kiểm sau cài được lưu riêng.
