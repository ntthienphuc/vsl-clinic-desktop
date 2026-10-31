# Giọng nói và câu có kiểm soát — 0.3.1

## Luồng trên máy

Micro → PCM 16 kHz ở RAM → VAD → PhoWhisper-base INT8 → planner → timeline avatar và chữ đầy đủ. **Tự động:** câu nghe rõ, có kế hoạch ký hiệu đầy đủ sẽ tự gửi sau nhịp ngừng. **Xác nhận trước khi gửi:** mọi transcript chờ bác sĩ đọc/sửa và gửi. Cả hai chế độ giữ câu thiếu ký hiệu, nghe không rõ hoặc bị cắt vì dài để xem lại. Không ghi âm hoặc hội thoại ra đĩa.

PhoWhisper-base có 74M tham số; bản CTranslate2 INT8 khoảng 80 MB, chạy CPU hai luồng/một worker. Chọn cấu hình này để chia tài nguyên với MediaPipe, ONNX và hai UI trên i7-10750H/16 GB/GTX 1650 Ti 4 GB. Runtime không tải model hoặc gọi cloud. Nguồn: [VinAI PhoWhisper](https://github.com/VinAIResearch/PhoWhisper), [model](https://huggingface.co/vinai/PhoWhisper-base), [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

Audio gửi từng 100 ms; Silero v6 ONNX nhận dạng hoạt động lời nói ở frame 32 ms, pre-roll 320 ms, ngắt sau 576 ms không còn lời nói, tối đa 12 giây/ý. Trạng thái h/c và context riêng cho từng micro, weights dùng chung. Ngưỡng bắt đầu 0,60/kết thúc 0,35; 3/5 frame để mở đoạn, tối thiểu 192 ms lời nói. Nếu chạm trần 12 giây, đoạn đó chờ kiểm tra và phải có nhịp nghỉ trước khi nhận lượt mới. Không cắt tín hiệu kéo dài thành vô hạn bản nháp. Tắt AGC của trình duyệt, giữ khử tiếng vọng/lọc nhiễu. Nguồn mô hình: [Silero VAD](https://github.com/snakers4/silero-vad); ONNX đi kèm faster-whisper 1.2.1 đã được đóng gói, không tải mạng.

Hàng đợi hai ý; quá tải dừng và báo để xem lại chữ. Live micro chạy suốt phiên, bỏ giới hạn 85 giây của đường dictation cũ. Một kết quả có ID duy nhất để tránh gửi lặp; nói thật cùng một câu hai lần vẫn tạo hai lượt. Dừng/reset/đổi chế độ tăng epoch, vô hiệu kết quả đến trễ và giải phóng track. Có tối đa 20 bản nháp chưa gửi trước khi ngừng nhận thêm; UI xem từng câu, không âm thầm xóa bản nháp. Câu thiếu từ hoặc mẫu câu có cảnh báo **Nói lại**; nút đó bỏ đúng bản nháp đã chọn và tiếp tục nghe. Gửi chữ phải được bác sĩ chọn. Câu “Bạn cảm thấy thế nào?” hiện chưa có mẫu/ký hiệu “thế nào”, nên chỉ cảnh báo, không tự phát một câu khác.

`hallucination_silence_threshold` cũ được bỏ vì nó không có tác dụng khi không bật word timestamps. Bộ lọc thần kinh ngăn nhiễu đi vào ASR; kết quả rỗng không tạo bản nháp. ASR có compression ratio > 2,4 hoặc log probability thấp vẫn chờ xem lại. Không tuyên bố lọc được lời nói từ TV/người khác: đó vẫn là lời nói; chưa có nhận dạng danh tính người nói.

**Bắt đầu cuộc trao đổi** ở bác sĩ kích hoạt cả theo dõi camera và nghe micro. Bệnh nhân không cần bấm bắt đầu theo từng từ. Không có thiết bị/quyền micro thì lỗi được hiển thị và vẫn nhập chữ được.

## Từ và lượt của bệnh nhân

`backend/live_segmenter.py` kiểm tra chuyển động tay/khuỷu theo khoảng vai; tư thế giơ tay tĩnh không tự sinh lại từ. Giữ tay ổn định khoảng 700 ms hoặc hạ tay kết thúc đoạn từ; đoạn đủ dài được gửi model ngay. Mất tracking lâu loại đoạn chưa hoàn chỉnh.

Kết quả mỗi đoạn được broadcast ngay và thêm vào `patient_turn.words`, giữ n-best cùng metric của từng từ. `backend/patient_turns.py` chỉ gom lịch sử sau 1.500 ms không có hoạt động/kết quả mới; chưa chốt khi đang signing hoặc còn inference/queue. Khung bác sĩ cập nhật và cuộn tới từng từ mới. Lượt dài chia sau 128 từ, không bỏ từ. Dừng/đổi nguồn/feedback đóng lượt hiện tại.

Gợi ý diễn đạt dùng một số quy tắc hẹp: Cần → Giúp đỡ thành “Cần giúp đỡ.”; Đau → Mệt thành “Đau và mệt.”. Từ gốc luôn được giữ. Không suy ra “đau bụng” chỉ vì bác sĩ vừa hỏi bụng; chuỗi phủ định, lặp hoặc không chắc giữ nguyên. Chưa có LLM viết lại nội dung.

## Catalogue và ngữ pháp

65 từ avatar: 56 từ local có ID model, 9 từ QIPEDC có `model_id: null`. Recognizer bệnh nhân vẫn giữ đúng 400 lớp. Catalogue có 40 mẫu tường minh và 18 tổ hợp chủ thể/vị ngữ có kiểm soát, tổng 58 mẫu. Tối đa 6 mệnh đề/24 ký hiệu trong một lượt. Có thêm câu hỏi lạnh/nóng/yếu, muốn ngủ/uống nước/nghỉ, gọi y tá/bác sĩ, rửa tay và nhu cầu giúp đỡ. Biết thêm từ không có nghĩa mọi câu ghép đều được chấp nhận.

| Câu nhập | Thứ tự ký hiệu |
|---|---|
| Bạn có đau bụng không? | Bụng → Đau, kèm tín hiệu hỏi |
| Bạn có mệt không? | Mệt, kèm tín hiệu hỏi |
| Y tá đo nhiệt độ. | Y tá → Nhiệt độ → Đo |
| Uống nước. | Nước → Uống |
| Bệnh nhân ăn cơm. | Bệnh nhân → Cơm → Ăn |
| Ngồi nghỉ ngơi. Uống nước. | Ngồi → Nghỉ ngơi; Nước → Uống |

`assets/phrases.json` và `backend/text_to_sign.py` là nguồn quy tắc. Khớp Unicode NFC và casefold, giữ dấu; ưu tiên cụm dài. Chỉ chấp nhận toàn mẫu, ngữ pháp khai báo hoặc một nhãn đơn. Không tự chấp nhận chuỗi bất kỳ chỉ vì từng từ đều có trong bank. Phủ định, con số, toán tử hoặc phần ngoài phạm vi phải giữ nguyên bằng **Chỉ gửi chữ**, không phát một phần câu.

Tài liệu QIPEDC có các ví dụ đưa đối tượng trước hành động, cấu trúc chủ thể–đối tượng–hành động và các dấu hiệu hỏi/phi thủ công. Đây là cơ sở thiết kế mẫu, không phải quy tắc đảo mọi câu sang một thứ tự duy nhất. Nguồn: [tài liệu người lớn điếc, trang in 23–25](https://qipedc.moet.gov.vn/congvan/T%C3%A0i%20li%E1%BB%87u%20t%E1%BA%ADp%20hu%E1%BA%A5n-Ng%C6%B0%E1%BB%9Di%20l%E1%BB%9Bn%20%C4%91i%E1%BA%BFc.pdf).

Các mẫu câu vẫn cần người sử dụng VSL thẩm định. Chân mày/hướng đầu hiện tại chưa thay thế đầy đủ ngữ pháp nét mặt/khẩu hình. Không gắn nhãn chuẩn Đồng Nai; người dùng đã chọn không phân biệt vùng cho nguồn demo.

## Phát câu liên tục

`backend/playback.py` tạo một timeline có phiên bản, độ dài từng motion, khoảng nối và ranh giới mệnh đề. Frontend dùng cùng timeline để lấy pose, đổi nhãn từ và biểu cảm hỏi. Có intro/outro 350 ms, cầu nối mặc định 280 ms và ngắt mệnh đề 160 ms. Ba cặp nối có profile riêng trong `assets/sentence_motion.json`, chỉ áp dụng khi SHA-256 khớp; không cắt tay nghỉ hàng loạt ở clip chưa duyệt.

Patient tải đủ motion trước khi báo ready. Server giữ đồng hồ phát, hàng đợi, ID và iteration. Pause/resume/speed giữ pha; replay tạo iteration mới; stop hủy cả nội dung chờ. Caption chỉ đổi khi nội dung được trình bày. Ready/complete cũ không tác động vào lượt mới; thông báo complete quá sớm bị từ chối. Mất UI patient thì tạm dừng.

## N-best và LLM

- Giữ nguyên top-1/n-best, không thêm nhãn ngoài 400. Gợi ý ngữ cảnh chỉ lấy ứng viên có điểm ≥ `max(0,10; 0,5 × top-1)`; ngưỡng là heuristic, chưa hiệu chỉnh xác suất.
- Ngữ cảnh phải đến từ câu đã được trình bày và mệnh đề hiện tại/gần nhất trong 60 giây. Câu tương lai còn ở hàng đợi hoặc mệnh đề chưa phát không được gây thiên lệch nhận dạng.
- Gợi ý từ đồng nghĩa được khai báo, chỉ dùng sau khi bác sĩ bấm chọn; không bỏ dấu hoặc lấy từ gần nhất theo khoảng cách chuỗi.
- Chưa đưa LLM sinh nội dung vào runtime: chưa có tập đánh giá nghĩa/độ trễ cho miền này. Nếu mở rộng, chỉ cho LLM đề xuất ID trong allowlist, giữ câu gốc và yêu cầu bác sĩ duyệt. LLM không tạo ra ký hiệu ngoài bộ nhận dạng.

## QIPEDC và provenance

Đã nhập đúng 9 clip: Bụng, Tay, Sốt, Ngồi, Đo, Nhiệt độ, Cơm, Thở, Bệnh nhân. Mỗi từ dùng **một video**, không gọi là chuyển động trung bình nhiều người. Original nằm trong `assets/reference-source/qipedc`, không sửa và không đưa vào portable. `research/qipedc-sources.json` lưu URL/hash/window; `assets/qipedc-provenance.json` được phân phối kèm chuyển động dẫn xuất.

Phân biệt nguồn: `research/qipedc-dictionary-index.json` là catalogue 4.362 entry/3.315 nhãn thô của export QIPEDC chính thức (3.314 nhóm sau NFC/casefold để tìm kiếm); `research/allcam1-bank/` là candidate bank trích từ All_cam1 (4.152 clip/402 nhãn) cho recognizer. Hai namespace không dùng chung ID. Một nhãn giống nhau chỉ là ứng viên crosswalk, cần kiểm tra sense, chuyển động và signer trước khi nhập.

Window mặc định lấy first/last observed hand ±400 ms. Bệnh nhân W00248 được xem trực quan và lấy riêng 1.500–4.200 ms chính diện; phần quay ngang rồi lặp lại bị loại khỏi motion. Video nguồn vẫn nguyên vẹn. Hai tay mất tracking có confidence/imputation tách biệt, không được ghi thành dữ liệu quan sát thật. Không đổi nhãn QIPEDC sang class model.

## Bằng chứng 0.3.0

- `evidence/runtime-v0.3-duplex.json`: 6 video theo clock thật cùng avatar; 6/6 top-1 khớp mẫu, capture errors 0; kết thúc đoạn từ → server median 579 ms, p95 722 ms; server → WebSocket median 2 ms. Doctor paint thiếu ở một số mẫu vì tab nền nên không suy ra toàn bộ độ trễ UI từ báo cáo này.
- `evidence/live-turn-v0.3.json`: hai video mẫu Đau/Mệt được nối với 800 ms nghỉ; cả hai từ đến khi lượt còn streaming, rồi gom đúng một lượt. `live-turn-v0.3-no-pause.json` giữ trường hợp không nghỉ bị gộp đoạn; đây là giới hạn của model từ rời.
- `evidence/speech-v0.3.json`: ba WAV theo clock thật; giải mã median 1.152 ms; endpoint 540 ms + queue + decode median 1.692 ms, p95 1.875 ms. Đây là đường ASR thật; không phải micro thật hay WER. Auto/Manual và gửi trước khi đóng socket được kiểm tra bằng fixture VAD/ASR trong `tests/test_speech.py`, không gọi fixture là nhận giọng người thật.
- `evidence/motion-audit.json`: 124 trường hợp trên rig nam thật (65 từ, 58 mẫu, một chuỗi); không lỗi vượt gate kỹ thuật. Không chứng minh người điếc hiểu đúng câu.
- Các gate backend/động học và gói cuối được ghi trong `DEMO_HANDOFF.md` và log build. Bằng chứng 0.2.1 cũ vẫn giữ để đối chiếu, không dùng thay kiểm tra 0.3.0.

Bộ [kịch bản và video bệnh nhân](../demo/KICH_BAN_DEMO.md) chỉ dùng 8 nhãn đã đối chiếu trong 400. Chưa kiểm thử hội thoại tự nhiên, người ký mới hoặc môi trường bệnh viện ồn.
