# Hướng dẫn dùng VSL Clinic 0.5.2

[Tài liệu dự án](README.md) · [Kết quả kiểm tra và giới hạn](CLINIC_0.5.2.md)

Chạy **VSL-Clinic-Setup-0.5.2.exe**, chọn nơi cài rồi bấm **Cài đặt**. Bộ cài đã chứa model, giọng đọc và các thành phần cần thiết; không cần tự tải hoặc mở server. Sau khi cài, bấm **VSL Clinic** trên Desktop. Ứng dụng tự mở hai cửa sổ: **Bác sĩ** và **Người bệnh**.

Máy phát triển vẫn giữ `Open Clinic 0.5.2.lnk` để mở bản portable và `Open Clinic.lnk` để đối chiếu baseline 0.4.1. Khi chuyển sang máy khác, chỉ cần mang theo file Setup. Có thể gỡ ứng dụng qua **Cài đặt Windows → Ứng dụng → VSL Clinic**; hồ sơ ứng dụng được giữ riêng trong `%LOCALAPPDATA%\VSL Clinic\UserData`.

## Bác sĩ bắt đầu

1. Mở **Camera và tùy chọn** để chọn camera. Có thể bấm **Mở thử camera** để kiểm tra khung hình. Khi tập thử, chọn **Video mẫu** hoặc **Mở video trên máy**.
2. Trong cùng hộp này, chọn **Gửi lời nói của bác sĩ → Kiểm tra trước khi gửi** hoặc **Tự gửi sau khi nói**.
3. Đóng hộp tùy chọn, bấm **Bắt đầu cuộc trao đổi**. Camera và micro mở cho cuộc trao đổi. Gõ chữ và chọn câu vẫn dùng được khi tắt micro.
4. Nói từng câu ngắn rồi nghỉ một nhịp. Câu chưa rõ hoặc chưa đủ ký hiệu sẽ nằm ở **câu chưa gửi · Kiểm tra** để sửa, nói lại hoặc gửi nguyên văn bằng chữ.
5. Hoặc bấm **Câu khám bệnh**, chọn một câu như **Bác sĩ khám bệnh.** hay **Y tá đo nhiệt độ.** Câu được điền vào ô nhập; kiểm tra rồi bấm **Gửi người bệnh**. Có 24 câu thuộc bốn nhóm, tìm được bằng chữ không dấu.

**Thêm câu / từ** mở đầy đủ câu, từ ký hiệu có sẵn và bài tập thử. **Chỉ gửi chữ** giữ nguyên nội dung khi chưa có cách thể hiện đầy đủ bằng ký hiệu. Những ý như phủ định, liều lượng hoặc vị trí đau không được tự bỏ để cho câu qua.

Micro tự tạm nghỉ khi ứng dụng đọc lời bác sĩ/người bệnh, sau đó nghe tiếp. Có thể **Tắt micro** bất cứ lúc nào; việc chọn câu và gõ chữ vẫn hoạt động. Chế độ tự gửi không phân biệt được bác sĩ với người đứng cạnh đang nói: ở nơi nhiều người trò chuyện, dùng **Kiểm tra trước khi gửi**.

## Người bệnh trả lời

Người bệnh xem lời bác sĩ bằng chữ và ký hiệu, rồi trả lời trước camera. Không cần bấm Bắt đầu cho từng từ.

| Cách nhận | Cách dùng |
| --- | --- |
| **Ký hiệu + khẩu hình** — mặc định khi mở ứng dụng | Bộ 100 từ. Giữ mặt và hai tay rõ trong hình; không cần nói thành tiếng. |
| **Chỉ ký hiệu** | Bộ 400 từ cũ. Giữ vai và hai tay rõ trong hình; không cần hình miệng. |

Hai lựa chọn nằm ngay dưới **Hình ảnh của bạn**. **Xem 100 từ / Xem 400 từ** mở đúng bộ từ đang chọn; không cần nhớ mã từ. Bác sĩ cũng có thể đổi trong **Camera và tùy chọn**. Khi đổi, danh sách từ và video mẫu tự cập nhật. Hạ tay trước khi đổi vì động tác đang dở sẽ được bỏ; các từ đã nhận vẫn còn trong nội dung trao đổi. Video tải lên sẽ chạy lại từ đầu.

Ký từng từ, hạ tay một nhịp khoảng 0,7–1 giây giữa các từ. Từ nhận đủ rõ hiện ở **Lời người bệnh** và được đọc ngay; từ chưa rõ chờ bác sĩ kiểm tra. Nghỉ khoảng 1,5 giây sau từ cuối để gom lượt vào lịch sử, không đọc lại cả lượt đã gom. Đây là nhận từng từ trong bộ, chưa phải dịch mọi câu ký hiệu tự do.

**Tôi đã hiểu** và **Xin giải thích lại** là hai nút phản hồi nhanh khi đã có lời bác sĩ. Với khẩu trang hoặc khi miệng không rõ, có thể chọn **Chỉ ký hiệu** và đối chiếu nội dung. Hai bộ từ không hoàn toàn giống nhau; chức năng tra từ giúp biết từ cần dùng có trong bộ hay không.

## Kiểm tra và kết thúc

Nếu từ vừa nhận chưa đúng, bác sĩ mở **Đối chiếu từ vừa nhận**, sửa rồi **Xác nhận**. Kết quả chưa rõ không được tự đọc. Nếu hình ảnh thiếu nhịp, chờ máy ổn định và ký lại. Điểm nhận dạng cao vẫn có thể sai.

Các nút **Tạm dừng**, **Tiếp tục**, **Phát lại** và tốc độ nằm dưới phần ký hiệu. Khi người bệnh trả lời đủ rõ trong chế độ tự gửi, ký hiệu đang phát nhường lượt; bấm **Tiếp tục** để xem phần còn lại. Nút loa bật/tắt giọng đọc. **Bố trí màn hình** ở góc trên hỗ trợ mở lại cửa sổ người bệnh, đổi vị trí và toàn màn hình.

Ưu tiên hai màn hình, mỗi vai một màn hình. Nếu dùng một màn hình chia đôi, cửa sổ bác sĩ nhỏ có thể phải cuộn; bấm **Bố trí màn hình** để dùng toàn màn hình khi cần đọc hoặc nhập nội dung.

**Kết thúc** dừng camera, micro, ký hiệu và giọng đọc; xóa nội dung, bản nháp và hình ảnh trên cả hai màn hình. Chế độ nhận và nguồn hình đang chọn được giữ cho cuộc trao đổi tiếp theo. Mở ứng dụng mới lại mặc định **Ký hiệu + khẩu hình**.

Nếu cần xem lại, tích **Lưu tạm** trước khi Kết thúc rồi bấm **Xem lại bản tạm**. Bản này chỉ nằm trong bộ nhớ, không tự phát lại; mất khi đóng ứng dụng hoặc bị thay/xóa khi kết thúc cuộc trao đổi tiếp theo. **Camera và tùy chọn → Xóa nội dung và bắt đầu lại** có bước xác nhận trước khi dọn phiên hiện tại.

Đây là bản thử nghiệm đã kiểm bằng video và âm thanh ghi sẵn; chưa kiểm người dùng, camera và micro trong phòng khám thật ở lượt này. Phạm vi kiểm chứng, số đo và giới hạn giấy phép được ghi trong [trạng thái 0.5.2](CLINIC_0.5.2.md).
