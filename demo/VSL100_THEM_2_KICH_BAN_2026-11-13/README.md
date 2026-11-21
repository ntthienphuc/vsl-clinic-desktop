# Hai kịch bản mới — dùng 62 từ trong bộ VSL100

Soạn ngày **13/11/2026**, dành cho VSL Clinic 0.6.3 có bản vá top 1. Đây là hai tình huống diễn giao tiếp giả định, không phải quy trình chẩn đoán hoặc điều trị.

| Kịch bản đầy đủ | Lượt người bệnh | Lần xuất hiện ký hiệu | Nhãn VSL100 khác nhau | Thời lượng dự kiến |
|---|---:|---:|---:|---|
| [1. Khó ngủ, mệt sau làm việc và trao đổi nhu cầu](01_Kho_ngu_met_va_hoi_benh.md) | 16 | 61 | 41 | 6–8 phút |
| [2. Đau tay, điều dưỡng và hỗ trợ sinh hoạt](02_Dieu_duong_ho_tro_sinh_hoat.md) | 18 | 71 | 45 | 7–9 phút |
| **Cả hai** | **34** | **132** | **62/100 nhãn, đã loại trùng** | Tùy tốc độ ký/đọc |

Kịch bản 1 khai thác công việc, giấc ngủ, thời điểm, đồ uống, triệu chứng, người nhà và nhu cầu nghỉ. Kịch bản 2 khai thác đau tay, người hỗ trợ, đồng ý/từ chối, dừng/tiếp tục, vệ sinh, đồ uống và chuyển sang trao đổi bằng chữ.

## Cách diễn

1. Mở **VSL Clinic** trên Desktop. Chọn **Ký hiệu + khẩu hình · 100 từ**; giữ mặt, miệng và hai tay rõ trong camera.
2. Bác sĩ dùng câu ở từng hàng. **Ký hiệu** nghĩa là câu đó có nguyên văn trong kho avatar: có thể chọn/gõ câu hoặc nói. **Chữ** nghĩa là chọn **Chỉ gửi chữ** rồi gửi nguyên văn. Có **17 câu ở mỗi loại** trong cả hai kịch bản; không khẳng định ASR sẽ nhận đúng mọi lần nói.
3. Người bệnh ký hết chuỗi trong một lượt theo dấu **→**. Không đọc/ký thêm câu giải thích ở cột cuối. Các mục như **Đau mắt**, **Không cần**, **Nhà vệ sinh**, **Thức dậy** là một nhãn nguyên vẹn.
4. Kết thúc rõ động tác mỗi từ, ngắt một nhịp tự nhiên rồi ký từ kế tiếp; **không chờ app hiện chữ/đọc xong và không bấm xác nhận giữa các từ**. Nghỉ dài hơn ở cuối lượt để bác sĩ đáp. App hiện vẫn nhận từng từ có ranh giới, không hứa hiểu mọi câu ký liền không ngắt.
5. Ở bản vá hiện tại, chat nhận top 1 từng từ; **Lời người bệnh** hiện top 1 xanh kèm top 2–3 và tự đọc top 1, không beep. Màu xanh là lựa chọn xếp hạng đầu, không phải bằng chứng từ đã đúng.
6. Chỉ diễn lời trao đổi; không thực hiện tiêm/băng bó/đo giả hoặc tự kết luận được về nhà. Sau lượt cuối, bấm **Kết thúc**.

Không thêm các nhãn như **Tôi, Không, Bao nhiêu, Bên trái, Bên phải** vào phần người bệnh: chúng không có trong đúng danh sách VSL100 này. **Không cần** không được dùng thay cho mọi câu phủ định. W038 phải ghi đúng **Lạnh (nhiệt độ)**.

## Tài liệu đi kèm

- [Kịch bản 1](01_Kho_ngu_met_va_hoi_benh.md) và [kịch bản 2](02_Dieu_duong_ho_tro_sinh_hoat.md): đầy đủ lời bác sĩ, chuỗi người bệnh, ý nghĩa và bảng W-ID.
- [THU_TU_KY.csv](THU_TU_KY.csv): bảng thứ tự 34 lượt, chuỗi nhãn và mã W-ID; mở được bằng Excel.
- [scenarios.json](scenarios.json): nội dung có cấu trúc, dùng lại khi cần tạo bài diễn/video.
- [CATALOG_RECEIPT.json](CATALOG_RECEIPT.json): số lượng, hash bộ nhãn và phạm vi đối chiếu.

Đã đối chiếu **toàn bộ 132 lần xuất hiện** với 100 nhãn trong `assets/multimodal100/label_mapping.json` và 17 lượt câu bác sĩ với đúng câu trong `assets/phrases.json`. Đây là đối chiếu nội dung tài liệu, **không chạy app, ASR, video, model hoặc benchmark**. Chưa đánh giá ký câu tự nhiên/người dùng mới. Các file này là tài liệu diễn độc lập, chưa thay nội dung nút **Bài tập thử** bên trong app.
