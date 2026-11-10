# Multimodal VSL100 — Clinic 0.5.1

Trạng thái: bản local 0.5.1 đã qua kiểm source/EXE, lifecycle hơn 5 phút, CPU,
đủ assets/runtime/voice và đối chiếu hash package. Phạm vi nghiệm thu là fixture
theo yêu cầu người dùng. Kiểm kê được lưu trong `release-051/PORTABLE.json`;
source/package parity cuối ở `BUILD_RECEIPT.json` trong thư mục portable.
Mô hình chính đã chuyển sang **SL-GCN + AV-HuBERT / cross-attention**,
checkpoint VSL100 R3 fold01/seed17. [Lý do chọn và đối chiếu fusion](FUSION_SELECTION_0.5.1.md).
Baseline0.4.1 và package0.5.0 vẫn được giữ nguyên.

## Luồng sử dụng

Mở app, chọn camera hoặc video VSL100, bấm **Bắt đầu cuộc trao đổi**.
App tự nạp model trong worker riêng. Tay và hình ảnh môi được lấy từ cùng
khung hình/đoạn; microphone không phải đầu vào của nhánh môi.
Từng từ đủ chắc hiện chữ và được đọc ngay, rồi mới gom lượt sau khoảng nghỉ.
Từ chưa chắc chờ đối chiếu, không tự đọc thành lời khẳng định.
Không cần người dùng mở server hoặc chọn giữa nhiều đáp án model.

Bác sĩ vẫn có thể nói/gõ để avatar ký, phát giọng nam và nhép miệng.
Từ người bệnh được commit sẽ nhường lượt avatar; **Tiếp tục** phát phần còn lại.
**Kết thúc** dừng hình/giọng và xóa phiên, chặn kết quả cũ đến muộn.

## Contract

`vsl100-r3-slgcn-avhubert-xattn-f01-s17-clinic-v1`.
100 nhãn W001…W100 có thứ tự và voice mapping riêng; không trộn index với400 cũ.
Hai encoder frozen và head học thật; thiếu một nhánh báo chưa nhận được.
Xử lý trong RAM, một nguồn capture, hàng đợi/buffer hữu hạn.
Không lưu hình người bệnh hay nội dung trao đổi ra đĩa trong luồng thường.

Ngữ cảnh R3 giữ tối đa500ms trước active core và400ms sau core, chỉ lấy ảnh đã
quan sát đến thời điểm chốt từ. Thời điểm endpoint và ngưỡng0,8/0,25 không đổi.
Điều chỉnh này giữ phần môi/tay mở đầu mà crop250ms trước đó có thể cắt mất.
Không cần chờ hết câu hoặc đợi frame tương lai.

## Bằng chứng

- Bảng nghiên cứu VSL100 sẵn có:97,39% macro-F1 trung bình cho cấu hình đã chọn,
  6 fold ×3 seed. Đây không phải accuracy webcam/Clinic.
- Kiểm3 clip VSL100 từ pixel nguồn đến100 xác suất: cùng top1, sai số tuyệt đối
  lớn nhất2,39e-7 so output nghiên cứu gốc. Cả hai modality ảnh hưởng logits.
- Lượt source đầu trước sửa context:6/12 tự đọc đúng,6 review,11/12 top1;
  test lặp Sốt cần review nên chưa pass. Giữ nguyên receipt thất bại.
- Source sau sửa context:10/12 từ tự đọc đúng,2 review,11/12 top1;10 kiểm tra
  luồng pass, thoát0. Hai từ Sốt trong fixture lặp được đọc tự động trước khi gom lượt.
- EXE lượt đầu:9/12 tự đọc đúng,3 review,11/12 top1. Assertion yêu cầu mọi từ
  trong fixture lặp phải đủ chắc không đạt; chưa chạy đến ASR/End cuối suite.
- EXE lượt kiểm đầy đủ:8/12 tự đọc đúng,4 review,11/12 top1,0 clip bị bỏ;
  đủ10 kiểm tra luồng pass, thoát0. Trong4 review có1 frame-gap quá300ms,
  1 chưa có endpoint tự nhiên ởEOF và2 điểm/margin chưa đủ.
  Fixture lặp MP4V có2 từ Sốt cần QA xác nhận; sau xác nhận, mỗi từ cóID riêng,
  được đọc1 lần trước khi gom lượt, không bị dedup theo text.
  Không cộng hai lượt12 clip thành24 mẫu độc lập.
- Kiểm bổ sung trên EXE với hai lần clip Sốt giữ nguyên encoding nguồn:
  cả 356 frame giải mã khớp pixel nguồn; hai từ được tự động hiện/đọc mỗi từ
  đúng một lần trước khi đóng lượt, không cần QA xác nhận. Đây là kiểm lặp từ,
  không phải hai mẫu accuracy độc lập. Receipt:
  `packaged-ui-r3-051-original-repeat/REPORT.json` và
  `fusion_explore/REPEAT_ORIGINAL_PIXELS.json`.
- End-to-end EXE:frame ký cuối→chữ802,67/895,19ms p50/p95(n=12);
  →audio playing818,55/938,92ms(n=8 automatic);inference334,65/431,08ms.
  Sampling15,84–19,09fps. Đây là timestamp phần mềm trên mẫu nhỏ,
  không phải độ trễ photon/âm thanh hay accuracy ngoài phòng.
- Regression:396 testPython của project và23 testJavaScript pass.
  `pytest.ini` giới hạn discovery ở `tests`; lần đầu thu nhầm testTensorFlow/Torch
  của pose-format vendor bị collection error và được giữ log riêng.
- Worker đóng gói chạy video ghép312s và tiếp tục nhận từ sau300s;
  8 kết quả cóID riêng,top1 đều khớp các đoạn đã ghép,4 automatic/4 review.
  RSS quan sát1.196–1.704GB,buffer tối đa221 frame,queue có giới hạn.
  Đổi nguồn,kill/restart worker vàEnd đều pass,không có từ cũ sau hủy.
  Thời gian kiểm315,07s do lấy mẫu trạng thái mỗi5s.
  Khoảng nghỉ lặp một frame tĩnh không sinh từ; không thay cho testđộng tác tự nhiên.
- CPU: runtime đóng gói với `CUDA_VISIBLE_DEVICES=-1` nhận đúng Sốt và tự commit.
  Một lần inference là 1.105 ms; từ frame ký cuối đến kết quả worker là 1.588 ms.
  Load khoảng 12,46 s và warmup 3,29 s. Chỉ một clip, không chứng minh CPU giữ
  được tốc độ trong phiên dài; chậm hơn GPU trong kiểm này.
- Bốn fixture tổng hợp từ VSL100: thiếu mặt không phát từ; che phần thân/tay
  chuyển review; ảnh nghỉ có rung không phát từ. **Che môi vẫn tự commit Sốt**
  với score 0,843 (đúng nhãn nguồn). Face detector chưa kiểm được môi có thật
  sự khả dụng; không coi kết quả này là đã giải quyết khẩu trang. Không yêu cầu
  người bệnh bỏ khẩu trang hay phát âm. Khi không nhận được có thể ký lại/nhập chữ.
- Đối chiếu bảo toàn cuối: 190 tệp/snapshot khớp hash đã ghi trước đó, gồm
  source Android, R3 và baseline. Receipt `release-051/PRESERVATION.json`.
- Ba video ngoài từ điển 100 (Buổi chiều, Chú ý, Đọc) từ bộ legacy sẵn có:
  3 review, 0 tự commit, 0 clip bị bỏ. Đây là kiểm âm tính bổ sung riêng;
  dữ liệu đo nhận đúng/latency chính vẫn là VSL100 có hình môi. Ba ca này
  không chứng minh nhận biết mọi từ ngoài từ điển.

Các kiểm đều dùng fixture theo yêu cầu người dùng. Chưa kiểm camera/người ký
trực tiếp, khẩu trang thật hay acoustic echo ngoài phòng. Điểm softmax không
phải bộ phát hiện từ ngoài từ điển hoặc động tác ngoài ký hiệu.

## Bản portable

Đích build: `E:\Project\VSL Clinic\App\0.5.1\win-unpacked\VSL Clinic.exe`.
Lối mở riêng: `E:\Project\VSL Clinic\Open Clinic 0.5.1.lnk`.
`Open Clinic.lnk` gốc vẫn mở baseline 0.4.1; profile mới dùng `UserData_0.5.1`.
Giữ cả thư mục portable cùng model/runtime/voice. Bản nghiên cứu cục bộ;
AV-HuBERT có license giới hạn non-commercial research, kèm package và
`THIRD_PARTY_NOTICES.md`. Không có push/publish/deploy.

## Thử nhanh từ đầu tới cuối

1. Mở `VSL Clinic.exe` trong thư mục 0.5.1; giữ cả thư mục portable đi cùng.
2. Ở màn hình bác sĩ, chọn video mẫu **Sốt**, bấm **Bắt đầu cuộc trao đổi**.
   Đợi lần nạp model đầu; app tự quản lý worker. Có thể dùng video VSL100 khác
   qua chọn tệp. Hình môi là đầu vào camera, không phụ thuộc microphone.
3. Quan sát từ hiện và được đọc ngay khi đã nhận chắc. Nếu đang review,
   bác sĩ đối chiếu/chỉnh lại trước khi đọc. Không cần xác nhận mọi từ rõ.
4. Gõ **Bụng** hoặc câu được hỗ trợ ở phía bác sĩ để xem avatar, giọng nam,
   khẩu hình; kiểm tạm dừng và tiếp tục như luồng cũ.
5. Bấm **Kết thúc**: cả hai cửa sổ xóa phiên và dừng phát; có thể bắt đầu phiên mới.

Tổng hợp máy đọc được: `docs/evidence/multimodal-051-SUMMARY_051.json`.
Raw evidence đầy đủ ở
`E:\Project\VSL Clinic\Organization\MultimodalIntegration_2026-11-09`.
Giữ các lượt thất bại và phiên bản cũ để đối chiếu; không chọn lại checkpoint
hoặc hạ ngưỡng dựa trên các ca này.
