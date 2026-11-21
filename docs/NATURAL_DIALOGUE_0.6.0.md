# VSL Clinic 0.6.0 — câu tự nhiên và bộ cài tự chọn CPU/GPU

Trạng thái build: ứng viên ngày 10/11/2026. Bằng chứng chấp nhận cuối nằm ở
`Organization/NaturalClinic_2026-11-10/ACCEPTANCE.json` ngoài source/package.
Tài liệu đóng trong bộ cài không tự khẳng định rằng chính bộ cài đã được kiểm xong.
Mốc quay lui là 0.5.5 INT8 CPU; baseline gốc 0.4.1 và dữ liệu nghiên cứu được giữ.

## Lời bác sĩ

“Bạn cần nghỉ ngơi không?” được ghép thành **Cần → Nghỉ ngơi**, giữ ý hỏi,
hiện nguyên câu và đọc từng từ ở nhịp avatar thực hiện. Bộ ghép câu có chủ thể,
trạng thái/hành động, ý cần/muốn/nên, câu hỏi, thời điểm được hỗ trợ và cách nói
lịch sự. Các ý độc lập nối bằng “rồi”, “và”, dấu phẩy hoặc dấu câu được phát
theo thứ tự. Không tự bỏ liều lượng, phủ định, vị trí hoặc phần chưa hiểu.

Các kịch bản thực thi trong app:

- Mời chị ngồi nghỉ. Bạn có cần uống nước không?
- Bác sĩ khám bệnh rồi y tá đo nhiệt độ nhé.
- Bạn có buồn nôn không? Bạn đau bụng bên trái không?
- Bạn đau tay bên phải không? Mời chị nằm trên giường. Bạn hãy ngồi đợi.

Câu nghe rõ, đủ ý và đủ ký hiệu tự gửi ngay trong chế độ tự động mặc định, không cần chọn
lại cách nói. Ví dụ “Bạn có cần được nghỉ ngơi không?” giữ nguyên câu gốc,
phát **Cần → Nghỉ ngơi** với ý hỏi; “Chị có cần được nằm nghỉ không ạ?” phát
**Cần → Nằm → Nghỉ ngơi**. Bản gõ chỉ cần nút Gửi, không chọn gợi ý trung gian.
“Được” chỉ được xử lý trong khung cần/muốn với hoạt động do chính chủ thể thực
hiện; “được khám bệnh” không bị đổi thành “khám bệnh” làm sai người thực hiện.
Câu nghe chưa rõ, thiếu ý hoặc không đủ ký hiệu vẫn ở phần chưa gửi.

Câu thông thường không chờ model ngôn ngữ. Với câu chưa ghép được, Qwen3 0.6B
Q8_0 cục bộ tự tìm cách nói trong thư viện hỗ trợ và hiện gợi ý ngay bên câu gốc.
Bác sĩ chỉ cần xem lại khi chưa xác định đủ ý. Các gợi ý còn chưa chứng minh
giữ đúng nghĩa không tự gửi; không tạo motion hay nhãn mới.
Kiểm nghĩa hai chiều loại gợi ý tự thêm/bớt bên trái/phải, thuốc, liều, thời điểm
và ý phủ định. Một probe thật từng gợi thêm “bên phải”; lỗi được giữ trong evidence
và đã thêm chặn hai chiều. Đây chưa phải bộ dịch VSL tự do.

## Năm ký hiệu bổ sung

Thêm **Buồn nôn, Bên trái, Bên phải, Nằm, Đợi**, nâng thư viện avatar 67 → 72 từ
và giọng avatar 132 → 137 clip. Clip QIPEDC, SHA-256 và khoảng trích nằm trong
`research/qipedc-sources.json`, `assets/qipedc-provenance.json` và manifest motion.
Các motion/voice cũ được đối chiếu hash với 0.5.5. Clip Đợi dùng biến thể miền Nam.
Chuyển động được trích và kiểm hình học trên avatar; chưa có đánh giá hiểu đúng
của người sử dụng VSL hoặc xác nhận tương đương mọi vùng miền.

## Máy chạy và bộ cài

Một Setup offline cho Windows 10 phiên bản 2004 trở lên hoặc Windows 11 x64, CPU AVX2. Khuyến nghị RAM 16 GB.
Có sẵn Python, Electron, engine, model tay/môi, ASR, LLM và giọng; không cần cài
Python hoặc CUDA Toolkit. Driver NVIDIA là thành phần của máy, không bị bộ cài đổi. Một bộ cài chứa cả runtime CUDA và CPU thuần để fallback không phụ thuộc driver; vì vậy dung lượng lớn hơn bản 0.5.5 chỉ CPU.

App dò CUDA trong process ngắn riêng, rồi khởi động model thực tế. Nếu chạy được, nhận dạng
dùng GPU NVIDIA với FP32; khi không có CUDA hoặc gặp lỗi CUDA được nhận diện,
dùng transformer môi INT8. Máy không có CUDA hoạt động được chọn runtime CPU thuần ngay từ đầu. Lỗi CUDA có thể bắt được trong Python (ví dụ hết VRAM) thử lại đoạn đang xử lý bằng INT8 trong worker hiện tại; trường hợp này Torch CUDA đã được nạp. Lỗi native driver lúc khởi động được thử lại một lần bằng runtime CPU thuần; lỗi native giữa phiên báo ký lại, lần Bắt đầu kế tiếp dùng CPU để tránh tự phát lại từ đã đọc. Giữ nguyên checkpoint tay/fusion, nhãn và
preprocessing; quantization 144 Linear dùng artifact đã đối chiếu ở 0.5.5.
GPU AMD/Intel chưa có backend nhận dạng riêng. Chưa hỗ trợ ARM/Raspberry Pi/Jetson.

Giới hạn cài đặt được kiểm trước. Không cho cài đè source/bản portable lưu trữ.
Setup cài theo người dùng, tạo shortcut Desktop và mục gỡ cài đặt, giữ profile
riêng. Kiểm PATH không chứa Python/FFmpeg và cache model rỗng là kiểm phụ thuộc
trên máy này, không chứng minh đã chạy trên mọi máy hoặc một Windows sạch.

Mốc Windows 10 build 19041 khớp API kiểm AVX2 của Setup theo
[tài liệu Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-isprocessorfeaturepresent).
Setup kiểm cả mốc hệ điều hành để không báo nhầm CPU thiếu AVX2 trên Windows quá cũ.

## Luồng và phạm vi kiểm

Hai chế độ người bệnh vẫn là **Ký hiệu + khẩu hình · 100 từ** (mặc định) và
**Chỉ ký hiệu · 400 từ**; bộ từ/giọng/video chuyển đồng bộ. Từ xanh đọc ngay;
từ vàng beep nhẹ rồi đọc và hiện ba gợi ý cho bác sĩ, theo lựa chọn của chủ app.
Preview có queue riêng; nhận dạng giữ lấy mẫu 25 fps, buffer hữu hạn và chuyển
vàng nếu mất nhịp. Âm thanh theo từng ký hiệu, nhép miệng, tạm dừng, nhường lượt,
chặn echo microphone, kết thúc phiên và loại kết quả muộn được kiểm trong app.

Dữ liệu kiểm là 12 clip VSL100 có môi đã khóa từ trước, không phải mẫu độc lập
để tuyên bố accuracy trên toàn bộ 100 từ. Im lặng/nhiễu kiểm bằng âm thanh tổng
hợp; chưa có kiểm webcam, tiếng ồn phòng khám, khẩu trang hay người ký trực tiếp.
Mọi số đo và lần thử thất bại phải giữ trong evidence; chỉ thay Desktop và dọn
bản cũ sau khi kiểm EXE, bộ cài, byte parity và luồng đã cài đạt.

Hai lần giả lập ẩn CUDA trong runtime CUDA cũ đã làm DLL NVIDIA `nvdxgdmal64.dll_unloaded` lỗi native (Windows Event 1000). Giữ log cả hai lần; nhánh CPU hiện dùng runtime thuần thay vì chỉ đổi device trong Torch CUDA.
