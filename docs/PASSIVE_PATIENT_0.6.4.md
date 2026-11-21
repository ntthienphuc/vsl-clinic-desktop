# 0.6.4 — màn hình bệnh nhân chỉ hiển thị, câu tự nhiên và bản cài nhẹ hơn

Ngày 13/11/2026. Bằng chứng chi tiết tại `Organization/Clinic064_2026-11-13`; trạng thái cài đặt và dọn ổ đĩa nằm trong receipt cuối ở đó.

## Giao diện và luồng trao đổi

- Người bệnh chỉ xem avatar, lời bác sĩ, hình camera và từ vừa ký. Đã bỏ nút hiểu/giải thích lại, điều khiển phát, nút loa, phóng to, đổi ngôn ngữ, menu màn hình, link logo và lựa chọn bộ từ khỏi màn hình này. Trạng thái lỗi cũng không yêu cầu người bệnh bấm nút.
- Bác sĩ quản lý **Ký hiệu + khẩu hình / Chỉ ký hiệu** trong **Camera và tùy chọn**. Bộ từ, video và giọng tự chuyển theo chế độ; mặc định vẫn là multimodal. Bỏ thông tin số lớp khỏi hai nút chọn chính.
- **VI / EN** chỉ ở phía bác sĩ và đổi giao diện hai màn hình cùng lúc. Nội dung ký hiệu và giọng vẫn tiếng Việt.
- Giữ thay đổi top-1 đã yêu cầu: hiện và đọc từng từ ngay, không beep/chữ vàng/dấu hỏi/xác nhận. Panel Lời người bệnh hiển thị top 1 xanh cùng top 2–3 khi có. Xanh là thứ hạng, không phải độ chắc chắn đã được hiệu chuẩn.
- Bác sĩ có điều khiển phát và bật/tắt giọng avatar. Kết thúc/reset vẫn dừng chữ, giọng, camera và bỏ kết quả muộn.

## Bác sĩ nói và kho ký hiệu

Trường hợp **“Đồng ý nằm nghỉ ngơi”** đi qua ba ký hiệu và ba nhịp giọng **Đồng ý → Nằm → Nghỉ ngơi**. Có dấu phẩy hoặc dùng “Bạn có đồng ý nằm nghỉ không?” cũng được hỗ trợ. Sửa ASR `năm nghỉ` chỉ áp dụng cho toàn câu hướng dẫn nghỉ có bằng chứng âm thanh tốt; không thay hàng loạt từ “năm”, không bỏ số lượng, thời gian, phủ định hoặc câu chưa nghe rõ. Raw transcript được giữ trong metadata.

Thêm tám video tham chiếu từ [từ điển QIPEDC](https://qipedc.moet.gov.vn/dictionary): **Đau mắt, Đau tai, Nhà vệ sinh, Ăn uống, Băng bó, Cấp cứu, Khẩu trang, Tiêm**. Từ 72 lên **80 chuyển động**, từ 137 lên **145 mục giọng**, từ 32 lên **44 câu chọn nhanh**. Một số mẫu mới:

- Bạn có đau mắt không? / Chị có bị nhức tai không ạ?
- Bạn cần đi vệ sinh không? / Anh muốn được ăn uống không?
- Bác sĩ băng bó. / Y tá tiêm. / Gọi cấp cứu.
- Bạn hãy viết nhé. / Bạn muốn nói chuyện không? / Bạn hãy tiếp tục thở nhé.

Mỗi từ mới có clip gốc, SHA-256, khung thời gian trích xuất và giọng đi kèm. “Ăn uống” chỉ trích lần ký chính diện, bỏ lần lặp nghiêng người. Đây là chuyển động trích xuất từ một tham chiếu; chưa được người dùng VSL xác nhận độ tự nhiên/ngữ nghĩa vùng. Không gán ID QIPEDC vào bộ phân loại người bệnh.

## Tối ưu đã áp dụng

1. Loại **Torch C++ headers và file `.lib`** khỏi runtime phát hành, ghi lại phần loại trong `RUNTIME_MANIFEST.json`. Giữ DLL, Python, CUDA, model và bản CPU riêng; source runtime không đổi.
2. `app.asar` chỉ mang code desktop và metadata; bỏ bản sao dependency JavaScript và frontend đã có ở `resources/frontend`.
3. Tải mã giao diện riêng theo vai. Bác sĩ không cần tải Three.js/VRM.
4. Chuyển động avatar tải theo câu, cache tối đa 24; chỉ báo ready khi chuyển động và giọng cần thiết đã tải. Giữ mẫu chuyển động nguyên vẹn, không giảm độ chính xác tensor hoặc đổi model.

Số đo candidate (cùng máy, lúc mới mở; không phải benchmark độc lập):

| Hạng mục | Bản 0.6.3 top-1 | Bản 0.6.4 |
| --- | ---: | ---: |
| Tổng file portable, byte logic | 10,754,179,827 | 9,098,657,240 |
| `app.asar` | 58,115,812 byte | 16,661 byte |
| JS heap cửa sổ bệnh nhân sau GC | 34,198,084 byte | 7,876,528 byte |
| Chuyển động tải lúc mở | 72 | 0 |
| JS tải ở phía bác sĩ | 1,437,629 byte | 557,307 byte |
| Điều khiển HTML phía bệnh nhân | 10 | 0 |

JS heap không phải tổng RAM của Electron, model hoặc Windows. Kích thước portable có thể tăng rất nhỏ khi thêm receipt/tài liệu. Baseline probe đã lấy được các số trên, nhưng lệnh đóng chờ trả lời sau khi app thoát gây timeout ở harness; engine log xác nhận exit 0. Bản harness sau sửa gửi yêu cầu đóng không chờ vào cửa sổ đã bị hủy. Không gọi attempt đầu là một lượt acceptance đạt.

## Bằng chứng và giới hạn

- 156 kiểm tra Python: câu tự nhiên, phạm vi sửa ASR, bảo toàn số/phủ định, tự gửi một lần, mỗi ký hiệu có giọng, playback/reset/version và runtime filter.
- 9 kiểm tra JavaScript: tải motion theo nhu cầu, cache/eviction, voice clock và tiến độ.
- Motion audit trên rig thật không có khớp quay quá 90° trong một frame; vẫn lưu các cảnh báo hiệu chỉnh ngón và tiếp xúc đầu/tay để đánh giá VSL sau.
- Candidate EXE: bốn chuỗi hội thoại gồm 17 ký hiệu, 17 lần phát tiếng, có chuyển động miệng; sai lệch thời điểm bắt đầu giọng so với cue lớn nhất khoảng 20 ms trong lượt đo này. Kiểm thêm pause/resume/reset, đổi chế độ, giao diện tiếng Anh và số điều khiển người bệnh bằng 0.
- CPU INT8 và NVIDIA CUDA của **bộ runtime đã tinh gọn** đều chạy ba fixture VSL100 có pixel miệng. Toàn bộ logits trùng lịch sử cùng thiết bị/precision trên đúng ba fixture (`max_abs_delta = 0`). Đây là kiểm tra bảo toàn đóng gói, không phải đo accuracy mới hoặc lời hứa realtime trên mọi máy.
- Ba câu giọng tổng hợp qua ASR live của EXE đều được nhận và tự gửi đúng chuỗi ký hiệu: “Đồng ý nằm nghỉ ngơi”, “Bạn có đau mắt không?”, “Bạn cần đi vệ sinh không?”. Mỗi câu có 4 giây im lặng ở đuôi, chỉ một transcript; lượt đầu harness tranh micro lúc khởi động bị từ chối, lượt retry chờ mic cũ nhả thành công. Không gộp thành kiểm micro người thật. Model nhận bệnh nhân, threshold, sampling và trọng số không đổi.

## Dọn dẹp và khôi phục

Theo yêu cầu chủ app ngày 13/11, chỉ xóa các release/bộ cài/cache đã được thay thế sau khi bản mới vượt kiểm cài đặt. Giữ source, Git, evidence, dữ liệu nghiên cứu và một rollback 0.6.3 cùng patch top-1. Danh sách chính xác, dung lượng logic và thay đổi dung lượng trống thực nằm trong `cleanup.json`. Không cộng hardlink như các bản sao độc lập.

Tag Git trước sửa: `baseline/clinic-0.6.3-top1-before-passive-ui`. Không training, benchmark lớn, push, publish hoặc deploy trong đợt này.
