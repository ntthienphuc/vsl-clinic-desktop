# Sửa luồng giọng nói Tự động — 0.3.1

## Hành vi sử dụng

1. Chọn **Tự động**, **Bắt đầu cuộc trao đổi**; micro mở một lần và tiếp tục nghe.
2. Nói một ý ngắn rồi nghỉ khoảng nửa giây. Câu nghe rõ và có đủ kế hoạch ký hiệu tự gửi tới người bệnh, avatar phát theo timeline.
3. Nếu chưa có từ hoặc mẫu câu: hiện cảnh báo **Câu này chưa gửi** và nút **Nói lại**. Bấm nút để bỏ đúng bản nháp đã chọn, tiếp tục nghe và diễn đạt lại. Có thể sửa chữ hoặc chủ động **Gửi chữ**. Không tự chọn một nghĩa gần giống.
4. “Bạn cảm thấy thế nào?” chưa có ký hiệu “thế nào” trong bank hiện tại: phải cảnh báo. “Bạn có đau không?” và “Uống nước.” đã hỗ trợ và tự gửi. Câu hỏi mở không bị thay thành câu hỏi đau.
5. Manual giữ bản nháp cho đến khi bác sĩ bấm gửi. Dừng/đổi chế độ/phiên vô hiệu các kết quả cũ.

## Nguyên nhân và sửa đổi

Bản 0.3.0 dùng WebRTC VAD: trong phép tái hiện với nhiễu có biến thiên biên độ, nó đánh dấu nhiễu là lời nói. Tín hiệu liên tục chạm trần 12 giây rồi tự mở đoạn mới, đưa nhiều đoạn nhiễu vào PhoWhisper. Model thực sự sinh chữ từ các đoạn đó. Đây là tái hiện bằng tín hiệu tổng hợp, không phải bản ghi micro lần báo lỗi của người dùng.

- Thay bằng Silero v6 ONNX đã có trong faster-whisper 1.2.1: 32 ms/frame, onset 0,60, offset 0,35, pre-roll 320 ms, endpoint 576 ms. Mỗi micro có trạng thái recurrent riêng. Chạy CPU một luồng, offline.
- Sau đoạn chạm trần 12 giây, đợi nhịp nghỉ thật trước đoạn tiếp. Câu quá dài chờ xem lại và nhắc chia ý.
- Tắt AGC của trình duyệt; vẫn khử tiếng vọng/lọc nhiễu. PCM giữ 16 kHz, worklet gửi 100 ms/gói, không phát ngược micro ra loa.
- Không dùng `hallucination_silence_threshold` như một bảo đảm: trong phiên bản thư viện cài trên máy, tùy chọn này chỉ chạy ở nhánh word timestamps mà cấu hình cũ không bật.
- Không tạo bản nháp từ kết quả rỗng. Thêm kiểm tra lặp bất thường qua compression ratio. Transcript không hợp lệ/quá dài không làm chết phiên micro.
- Mỗi đoạn có ID duy nhất; cùng một câu được nói thật hai lần vẫn nhận hai lần. Không dùng danh sách cấm câu hoặc dedupe theo chữ để che lỗi VAD.
- Bản nháp hiển thị từng câu với bộ chọn khi có nhiều câu; không xếp chín thẻ cảnh báo chiếm màn hình. Câu tự gửi có trạng thái **Đã gửi người bệnh**.

Nguồn kỹ thuật: [Silero VAD](https://github.com/snakers4/silero-vad), [faster-whisper VAD](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/vad.py). Giấy phép/hash mô hình nằm trong `licenses/inventory.json`.

## Bằng chứng tái hiện

`tools/probe_speech_gate.py` dùng cùng seed/tín hiệu và WAV công khai trước/sau sửa:

| Âm thanh đầu vào | 0.3.0 | 0.3.1 |
|---|---:|---:|
| 40 s nhiễu có biên độ biến thiên | 4 đoạn, ASR sinh câu không có trong âm thanh | 0 đoạn |
| Một câu + 40 s nhiễu đó | 4 đoạn; câu đầu bị giữ đến trần 12 s | 1 đoạn, endpoint 576 ms |
| Một câu + 40 s im lặng/hum | 1 đoạn | 1 đoạn |
| Cùng một câu nói hai lần, có nghỉ | 2 đoạn | 2 đoạn |

`evidence/speech-gate-before-v0.3.1.json` và `speech-gate-after-v0.3.1.json` giữ chi tiết. Bộ lọc mới xử lý 40 s âm thanh trong khoảng 0,15–0,18 s ở phép replay offline; đây không phải thời gian đáp ứng micro. `synthetic-asr-v0.3.1.json`: bốn câu TTS tiếng Việt qua VAD/PhoWhisper thật; hai câu được hỗ trợ, hai câu thiếu từ bị planner từ chối. TTS không phải đánh giá người thật.

## Giới hạn

Bộ 65 ký hiệu/58 mẫu câu chưa dịch mọi câu tiếng Việt. Không có nhận dạng danh tính người nói: TV hoặc người khác nói gần micro vẫn có thể được nhận là lời nói. Thử nhiễu tổng hợp và WAV/TTS không thay cho kiểm tra micro trong phòng thực, giọng người dùng hoặc WER. Các mức tin cậy là heuristic. Phần nhận 400 từ của bệnh nhân và bank/avatar không được huấn luyện lại trong bản sửa này.

## Bản đóng gói

Đường dẫn mục tiêu: `release/desktop-v0.3.1/win-unpacked/VSL Clinic.exe`. Giữ cả folder. Bản 0.3.0 giữ nguyên.

### Xác nhận trên gói frozen 0.3.1

- `npm run package` hoàn tất sau khi dựng lại thư mục portable; Vite/TypeScript đều đạt. Engine trong `resources/engine` có cùng SHA-256 với engine build.
- Mở đúng `VSL Clinic.exe` bằng Electron (hai cửa sổ và một `ClinicEngine.exe` con), log ghi `ready ... model=400 words`. Runtime bootstrap/diagnostics xác nhận model SL-GCN 400 lớp, avatar nam, hai client bác sĩ/người bệnh, và không còn `speech_drafts` chờ sau khi phát xong.
- Bài kiểm tra UI trên frontend do gói frozen phục vụ: nhập `Bạn cảm thấy thế nào?` hiện cảnh báo `Có từ hoặc nội dung chưa hỗ trợ avatar` và liệt kê `Bạn, thế, nào`; câu không bị đổi sang nghĩa gần nhất. Đổi sang `Uống nước.` hiện kế hoạch `Nước → Uống`, người bệnh nhận tin nhắn, avatar phát đủ timeline 4,335 ms và trạng thái `completed`.
- Bằng chứng chuyển động avatar: `evidence/browser-avatar-v0.3.1.json` ghi 37 mẫu khung với số frame tăng, cổ tay thay đổi, sai số bám tay lớn nhất 4,65e-16. Ảnh giao diện cuối nằm ở `evidence/ui-final-unsupported-v0.3.1.png` và `evidence/ui-final-patient-v0.3.1.png`.
- Bằng chứng runtime gói: `evidence/packaged-runtime-v0.3.1.json`; biên bản đóng gói: `evidence/release-receipt.json`; log package: `evidence/package-v0.3.1-final.log`.

Kiểm tra trên fixture âm thanh TTS/nhiễu và nhập UI không thay thế được thử micro người thật trong phòng. Khi chạy thử thật, nói một ý ngắn rồi nghỉ; nếu câu không có đủ bank, giao diện phải giữ cảnh báo và yêu cầu nói lại/cho phép gửi chữ.
