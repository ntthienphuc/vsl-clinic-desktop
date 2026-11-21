# 0.6.1 — giọng avatar độc lập với lịch vẽ

0.6.0 đã đạt EXE CPU/GPU và byte parity sau cài, nhưng hai lượt kiểm EXE đã cài
bắt được một lần giọng lệch quá 200 ms và một lần thiếu nhịp “Đo”. Các lỗi nằm
trong `Organization/MultimodalIntegration_2026-11-09/packaged-ui-12-natural060-installed1`
và `installed2`. Không nghiệm thu hoặc xóa rollback dựa trên các lượt này.

Lượt chẩn đoán tách khỏi đổi chế độ chạy đủ các câu tự nhiên: file giọng tải
trong 1,3–51,7 ms, độ lệch onset tối đa 33,9 ms, không có lỗi audio. Kết quả
này không xác định dứt khoát nguyên nhân từng lần lỗi trước. Code inspection
cho thấy giọng chỉ được kích hoạt trong requestAnimationFrame: nếu compositor
không trả frame trong cả khoảng cue ngắn thì từ đó có thể bị bỏ.

0.6.1 chuyển phục vụ giọng sang timer 20 ms nhẹ, độc lập với vẽ WebGL. Giọng,
motion, khẩu hình và chữ vẫn dùng cùng playback timeline. Timer không tính
hình học, không chạy model. Pause/mute/disconnect/context loss và unmount
đều chặn hoặc hủy giọng; không tạo thêm một người phát âm thanh.

`tools/check_voice_clock.mjs` cố ý giữ callback rAF qua toàn bộ một cue,
trong khi JavaScript timer/audio engine vẫn chạy, và kiểm đủ ba sự kiện phát
audio thật, đúng entry và lệch dưới 180 ms. Đây là fault injection compositor,
không phải mô phỏng toàn bộ OS/JavaScript thread bị khóa. Các kiểm câu tự nhiên
vẫn giữ ngưỡng 200 ms; không nới gate để bỏ qua lỗi. Harness lưu cả scenario
đang lỗi và toàn bộ sự kiện giọng để tránh mất bằng chứng.

Đối chứng trên EXE 0.6.0 đã cài tái hiện đúng lỗi: chỉ 2/3 từ được phát khi giữ
rAF qua cue thứ hai (`natural060-voice-clock-control`). Đây là bằng chứng trực
tiếp về điểm yếu phụ thuộc lịch vẽ, không chứng minh mọi lỗi trước đó cùng một
nguyên nhân.

Source 0.6.1 chạy cùng fault injection đã phát đủ 3/3 từ và thoát sạch
(`source-ui-final-natural061-voice-clock-source1`); so sánh nằm tại
`Organization/NaturalClinic_2026-11-10/VOICE_CLOCK_PAIRED.json`. Regression:
494 Python và 26 JavaScript đạt. Đây chưa thay thế gate EXE/bộ cài cuối.

## Chuẩn bị và đọc trọn clip

Build 0.6.1 đầu tiên còn lỗi chuẩn bị giọng tại mốc 5 giây; bản đó được giữ ở
`Archive/Rejected/0.6.1-first-clock`. Một probe media cũng ghi nhận hai sự kiện
`playing` của cùng từ sau 200 ms: thao tác seek tự động do chênh clock đã nhảy
audio.currentTime từ 0,008 tới 0,207 giây dù file nạp đủ trong khoảng 58 ms.
Đây là lý do loại việc seek liên tục khi một từ đang đọc.

Nguồn đã sửa chỉ seek lúc bắt đầu/tiếp tục có chủ ý. Clip được đọc hết trước
cue kế tiếp, không bị cắt bởi thời lượng WAV danh nghĩa khi thiết bị audio có
độ trễ khởi động. Sự kiện `playing` đầu tiên theo identity cue được tách khỏi
`resumed` của media engine; mọi sự kiện đều giữ để kiểm, không coi resumed là
thêm một từ. Lặp từ ở cue khác vẫn phải đọc lại.

Tải chậm sau 5 giây vẫn là trạng thái chuẩn bị và có thông báo, không tự bắt
đầu một chuỗi không có tiếng. Lỗi media thật hoặc giới hạn 15 giây mới dùng
fallback có thông báo. `check_voice_loading.mjs` hoãn gán nguồn audio 6,2 giây,
kiểm ở 5,2 giây vẫn loading, rồi kiểm các nhịp phát thật sau khi nạp xong.
Hai unit test mới kiểm không nhảy giữa từ và đọc hết/lặp đúng; kiểm EXE và
bộ cài đầy đủ vẫn cần gate cuối.

Đối chứng 0.6.0 với media chậm 6,2 giây đã tái hiện việc bắt đầu chuỗi ở mốc
5,2 giây khi chưa có giọng (`natural060-voice-load-control`). Sau chỉnh sửa,
28 kiểm JavaScript đã đạt; gate source/EXE thực tế phải được ghi riêng.

Source CPU thuần đã đạt cả hai phép giữ rAF và hoãn tải giọng, phát đủ các cue
và thoát sạch (`source-ui-final-natural061-clock-load-source2`);
`VOICE_LOADING_PAIRED.json` ghi kết quả đối chứng và hash báo cáo.

Build này kế thừa tính năng, model, preprocessing, INT8, LLM và giới hạn tương
thích trong [ghi chú 0.6.0](NATURAL_DIALOGUE_0.6.0.md). Bằng chứng cài và chấp nhận
cuối nằm ngoài payload tại `Organization/NaturalClinic_2026-11-10/ACCEPTANCE.json`.
Giữ tag `baseline/clinic-0.6.0-before-independent-voice`, evidence và bộ cài
0.6.0 trước sửa; baseline 0.4.1 và rollback 0.5.5 vẫn giữ.

## Âm báo và từ người bệnh phát liên tục

Lượt `natural061-installed1` đã cài qua các kiểm giọng bác sĩ nhưng bị loại vì
một từ vàng vượt giới hạn 700 ms từ beep đến giọng. Lượt đó không lưu sự kiện
giọng cuối ngay khi assert lỗi; harness nay giữ cả dữ liệu đó. Không suy ra
thời gian chính xác hoặc duy nhất một nguyên nhân từ báo cáo thiếu sự kiện.

Đường cũ tạo player của từ sau callback kết thúc beep. Đối chứng
`natural061-warning-start-control` hoãn khởi động mỗi clip giọng 900 ms đã
tái hiện khoảng ngắt này bằng media thật. Heartbeat vẫn chạy; đây là phép
kiểm điểm yếu khởi động nối tiếp, không phải chứng minh nguyên nhân duy nhất
của lần lỗi cài đặt ban đầu.

`build_patient_warning_bank.py` ghép beep nhỏ 120 ms với nguyên PCM của từng
giọng thành một WAV. Toàn bộ 419 WAV gốc được giữ nguyên hash; các clip ghép
thêm khoảng 20,3 MB. Từ vàng dùng một media stream nên không còn lần mở file
hay thiết bị âm thanh thứ hai giữa beep và từ. Observer 20 ms chỉ cập nhật
trạng thái theo vị trí media, không khởi động phần đọc từ. End, mute và sửa
từ dừng toàn bộ clip; sự kiện cũ vẫn bị chặn theo generation/identity.

30 kiểm JavaScript đạt, bao gồm PCM gốc được giữ byte-for-byte, sửa từ ngay
trong beep, tránh đọc lặp khi media phát lại event và việc quan sát bị trễ.
Source CPU chạy cùng lỗi khởi động 900 ms đã đạt với một native media start
(`source-ui-final-natural061-continuous-warning-source1`). Ngưỡng 700 ms
không đổi. Gate EXE/bộ cài mới vẫn phải chạy; không dùng lượt đã cài lỗi làm
bằng chứng chấp nhận. Tag `baseline/clinic-0.6.1-before-continuous-warning`
giữ source trước sửa và `WARNING_CONTINUITY_PAIRED.json` lưu đối chứng.
