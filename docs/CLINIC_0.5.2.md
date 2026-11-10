# VSL Clinic 0.5.2 — hai chế độ người bệnh và câu khám nhanh

Ngày 10/11/2026. Phạm vi: demo nghiên cứu cục bộ, fixture ghi sẵn theo yêu cầu người dùng. Giữ baseline 0.4.1, source nghiên cứu và bằng chứng. Chủ dự án đã duyệt dọn chín thư mục phát hành cũ, gồm 0.5.0/0.5.1, sau khi kiểm bộ cài mới và app đã cài. Hồ sơ dọn và Git nằm tại `Organization/CleanupInstaller_2026-11-10` của dự án.

## Cách dùng

Cài bằng `Installer/VSL-Clinic-Setup-0.5.2.exe`, rồi mở **VSL Clinic** trên Desktop. Bộ cài chứa model, runtime và giọng offline, mặc định cài vào `%LOCALAPPDATA%\Programs\VSL Clinic`. Bản portable tại `App/0.5.2/win-unpacked` là đầu vào đóng gói dành cho phát triển. App tự mở hai cửa sổ và bộ nhận dạng; không cần mở server hay chọn checkpoint.

| Chọn phía người bệnh | Bộ nhận dạng và từ vựng |
| --- | --- |
| **Ký hiệu + khẩu hình** — 100 từ (mặc định khi mở app) | Tay + hình môi từ cùng video; SL-GCN + AV-HuBERT cross-attention/gating, contract `vsl100-r3-slgcn-avhubert-xattn-f01-s17-clinic-v1`. |
| **Chỉ ký hiệu** — 400 từ | Model SL-GCN ONNX cũ; contract `clinic-slgcn400-onnx-v1`. Đây là bộ 400 riêng, không phải head sign-only 100 của fusion. |

Chọn chế độ ngay dưới **Hình ảnh của bạn**. Bác sĩ cũng có cùng lựa chọn trong **Camera và tùy chọn**. **Xem 100/400 từ** mở đúng danh sách đang nhận, tìm được bằng chữ không dấu. Nhãn, ID, giọng và danh sách video mẫu đổi theo bộ; chỉ hiện video thực sự có trong gói. Hai bộ không cộng thành 500 lớp. `fusion` và `sign_only` vẫn là ID nội bộ để giữ contract, không phải nhãn giao diện.

Khi chuyển giữa phiên, app dừng nguồn hình cũ trước khi mở bộ mới, bỏ đoạn chưa xong và kết quả muộn, rồi tiếp tục nguồn hình. Camera vẫn là camera; video được tải lên được phát lại từ đầu; video mẫu chuyển sang cùng nhãn nếu có, nếu không chọn một mẫu có sẵn của bộ mới. Từ/lượt đã nhận vẫn ở lịch sử. Nên hạ tay trước khi chuyển chế độ. Kết thúc giữ lựa chọn hiện tại trong lần mở app đó; mở app mới mặc định **Ký hiệu + khẩu hình**.

Phía bác sĩ: **Câu khám bệnh** có 24 câu thuộc bốn nhóm Khám bệnh, Điều dưỡng, Hỏi tình trạng, Hướng dẫn & hỗ trợ. Có “Bác sĩ khám bệnh.” và “Y tá đo nhiệt độ.”. Chọn câu chỉ điền ô soạn; bác sĩ kiểm tra rồi bấm **Gửi người bệnh**. Các câu lấy từ ngân hàng đã có đủ nghĩa/ký hiệu/giọng. Không tạo thêm động tác hoặc lược bỏ phần chưa hỗ trợ.

Giữ cách giao tiếp từng từ: một từ đủ rõ hiện và đọc ngay, chưa rõ chờ kiểm tra; nghỉ dài mới gom lượt. Người bệnh không phải phát âm thành tiếng. **Ký hiệu + khẩu hình** vẫn cần hình miệng dùng được; nếu không có tín hiệu môi phù hợp có thể chủ động chọn **Chỉ ký hiệu**. Không có cam kết tự phát hiện mọi khẩu trang, cử chỉ ngoài ký hiệu hoặc từ ngoài bộ.

## Im lặng và tạp âm

Giữ Silero streaming VAD và ngắt câu 576 ms; thêm lượt kiểm tín hiệu tiếng nói độc lập cho từng đoạn trước khi giải mã. PhoWhisper có xác suất “không có lời nói” cao không còn được chấp nhận chỉ vì chuỗi chữ có điểm cao. Đoạn không có tiếng nói trở lại trạng thái chờ và không sinh transcript. Giới hạn câu dài và chờ khoảng nghỉ trước khi nhận lại vẫn hoạt động.

Các fixture 40 giây gồm im lặng, tiếng xì, ù điện, xung giống bàn phím và nhiễu điều biên: không sinh đoạn lời nói. Sau tiếng nói + 40 giây im/nhiễu: chỉ có một đoạn lời nói; hai lần nói thật được giữ thành hai. Đây là kiểm âm thanh tổng hợp, không phải thu âm phòng khám. VAD không định danh người nói; người đứng cạnh nói rõ vẫn có thể được nhận. Khi cần kiểm soát, dùng **Kiểm tra trước khi gửi** hoặc tắt micro; gõ/chọn câu vẫn hoạt động. Chưa đo mic thật, phản xạ âm phòng, khẩu trang và giọng yếu ngoài fixture.

## Đánh giá trải nghiệm cho pilot

Luồng chính: mở ứng dụng → chọn nguồn → bắt đầu → nói/ký. **Camera và tùy chọn** gom nguồn hình, cách gửi lời nói, chế độ nhận và đặt lại phiên. **Kết thúc** luôn nằm ngoài hộp để thao tác nhanh. Câu khám bệnh nằm ngay trên ô nhập; không tự gửi khi chọn câu. Chỉ hiện trạng thái có ích; bớt nội dung lặp và thu gọn tiến độ khi phát xong. Các nút có viền focus bàn phím; hộp đặt lại phiên dùng dialog giữ focus và hủy được. Hai nút phản hồi người bệnh chỉ bật sau khi có lời bác sĩ. UI chính không dùng Fusion, Sign only, avatar, checkpoint hoặc backend. Hướng dẫn sử dụng mới hoàn toàn bằng tiếng Việt.

Kiểm bố cục 1280×720, 1920×1080 và cửa sổ hẹp 800×900; modal cuộn bên trong. Trên một màn hình chia đôi cửa sổ nhỏ, màn hình bác sĩ phải cuộn; để thao tác khám mô phỏng nên dùng hai màn hình hoặc toàn màn hình từng vai. Kết quả chưa rõ tự mở khung đối chiếu/sửa, tăng phần hiển thị cho bước này. Đây là đánh giá kỹ thuật/UX của người phát triển, chưa phải thử tính dễ dùng với bác sĩ, điều dưỡng và người điếc.

Trước sử dụng bệnh viện thật vẫn thiếu kiểm người dùng/người ký, mic/camera thật và tập âm thanh/cử chỉ/khẩu trang thực tế. Đọc [license AV-HuBERT](../licenses/multimodal100/AV-HuBERT-LICENSE.txt): artifact này chỉ cho nghiên cứu phi thương mại, cấm mục đích production/commercial. Không coi bản demo đã đủ điều kiện triển khai khám thật.

## Evidence và bàn giao

**Bản EXE cuối:** `packaged-ui-12-minimal-reviewed-052/REPORT.json` đạt các kiểm chức năng và thoát sạch trên gói đã build. Dùng 12 clip VSL100 có hình môi (6 nhãn, 2 người ký, giữ SHA256 và fold01/seed17 đã chốt): **7 tự đọc đúng, 5 chờ đối chiếu, 0 tự đọc sai, 11/12 top-1 khớp**. Không bỏ clip nào. Một lượt sửa từ qua UI là thao tác QA cố ý, không tính thành nhận đúng tự động. Clip Đau ở bộ 400 nhận/đọc đúng. Hai từ Sốt liên tiếp trong video nguyên pixel được tự đọc một lần mỗi từ trước khi hết lượt, không cần xác nhận.

| Số đo EXE cuối | Kết quả |
| --- | --- |
| Khung hình đầu vào của 12 đoạn | 10,15–17,31 fps |
| Từ khung hình còn hoạt động cuối đến hiện chữ | p50 **857 ms**, p95 **929 ms**, n=12 |
| Đến bắt đầu giọng đọc của từ tự động | p50 **898 ms**, p95 **962 ms**, n=7 |
| Thời gian suy luận | p50 **358 ms**, p95 **416 ms**, n=12 |
| Chuyển 100→400 giữa phiên | **908 ms**, một quan sát |
| Đóng hẳn EXE | **2,45 giây**, desktop và engine trả mã 0, worker đã thoát; không cưỡng bức |

Các mốc là timestamp phần mềm trên máy này, không phải đo photon/âm thanh vật lý; p95 chỉ mô tả tập rất nhỏ. Không suy ra accuracy bệnh viện hoặc độ ổn định mọi tải. Trước khi rút gọn riêng khung sửa, lượt 12 clip đạt 6 tự động / 6 chờ đối chiếu; các lần trước còn dao động mạnh như ghi bên dưới. Tỷ lệ cần đối chiếu ở lượt cuối là **41,7%**, nên chưa chứng minh được hội thoại tự động ổn định trong phòng khám.

Kiểm âm thanh qua **WebSocket/VAD/ASR của EXE thật**: 8 giây im lặng, xì, ù và xung giống bàn phím tạo **0 transcript**; sau đó mẫu lời bác sĩ tạo đúng **1 transcript được gửi**. 24 câu nhanh, chọn-xem-gửi, từ điển, phản hồi, nội dung thuốc chưa có ký hiệu vẫn được giữ nguyên bằng chữ, pause/resume ngừng cả âm thanh và miệng, nhường lượt, bản tạm, End/reset/fence đều qua kiểm. Ô sửa và nút Xác nhận được kiểm nằm trong vùng thấy được ở 1280×720, không chỉ tồn tại trong DOM.

Kiểm bổ sung cửa sổ Windows thật bằng Computer Use: chọn **Bác sĩ khám bệnh.** chỉ điền bản nháp; hộp 24 câu dễ bấm; hai nhãn người bệnh đúng, phản hồi tắt khi chưa có lời bác sĩ; bố cục bác sĩ toàn màn hình 1536×864 nằm gọn. Cửa sổ bác sĩ chia nửa màn hình (~755×810 pixel ngoài) vẫn phải cuộn; màn hình người bệnh vừa khung. Đây là giới hạn sử dụng một màn hình; dùng toàn màn hình từng vai hoặc hai màn hình để đọc dễ hơn.

Gói đầy đủ gồm engine, runtime multimodal, model 100/400, PhoWhisper/Silero, model/runtime gợi ý, 67 ký hiệu, 419 clip đọc người bệnh, 132 clip giọng bác sĩ và các video mẫu. Receipt và portable audit đối chiếu toàn bộ đầu vào/gói; xem `Organization/ModesPilot_2026-11-10/portable-final.json` tại root dự án. Baseline 0.4.1 và 0.5.1 được audit lại, 190 đầu vào nghiên cứu/original được băm lại; 10 file core fusion khớp 0.5.1. Kế thừa riêng bằng chứng parity, CPU, thiếu modality/OOV và phiên dài từ 0.5.1; không ghi thành mới chạy trên 0.5.2.

Source tests: **404 Python + 23 JavaScript**. Source Electron: đổi hai chiều giữa đoạn ký; dictionary 100/400 và nguồn hình đồng bộ; model400 nhận/đọc Đau; 24 câu nhanh với chọn-xem-gửi; avatar/giọng/miệng; lặp Sốt từ video VSL100 nguyên pixel; ASR gửi một lần; End xóa và chặn callback. Lượt đổi Fusion→400 đầu tiên đo 1,220 ms trên máy này, không phải p95. Hai ca hồi quy bổ sung kiểm End ngay khi model đang nạp và giữ khóa camera khi thread dừng bị timeout.

Evidence chính ở `Organization/ModesPilot_2026-11-10` và `Organization/MultimodalIntegration_2026-11-09`. Lượt source với UI gọn `source-ui-final-minimal-052-r2` xử lý đủ 12 clip VSL100 cố định: 7 tự đọc đúng, 5 review, 10/12 top1 khớp; 0 từ tự đọc sai trong lượt này. Khung hình đầu vào dao động 10,36–17,31fps. Sửa câu, giọng/miệng, nhường lượt, lặp từ, silence/noise và Kết thúc đều qua; nhưng driver phải đóng cưỡng bức sau 8 giây nên lượt đó **không được tính là đạt đóng ứng dụng sạch**. Đã sửa desktop đóng renderers trước để nhả WebSocket/mic/WebGL rồi chờ engine/worker theo hạn có giới hạn. Lượt source cuối `source-ui-final-minimal-final-052` kiểm lại mode/UX/voice/noise/End và thoát: desktop0, engine0, worker hết chạy, không cưỡng bức; shutdown1.822ms. Đây là 1,822 giây, không phải p95.

Hai lượt script cũ `source-ui-final-modes-052` và `source-ui-final-minimal-052` bấm trước khi React bỏ trạng thái bận; đã sửa driver chờ nút thật sẵn sàng. Không xóa các báo cáo thất bại.

Lượt EXE `packaged-ui-12-modes-052` thất bại vì test khởi động trước khi đóng gói xong, gây khóa thư mục/renderer crash. Packager và probe đã thêm chặn chạy đồng thời. Lượt `packaged-ui-12-modes-052-r2` đi qua mode/dictionary/câu nhanh/phản hồi nhưng phát hiện Sign-only400 nhận clip Đau thành Bố với score0,9835 và tự đọc, ở14,71fps/28frame. Không giấu failure hoặc đổi ngưỡng softmax. Đã giới hạn graph2 luồng, XNNPACK1 luồng ở detector400; kiểm142frame cố định từ Đau/Mệt cho tọa độ, tensor và logits giống hoàn toàn bản trước (sai số0). Profile mới `clinic-pc-tasks-lite-parallel-bounded-v3`; chưa xem một lượt chạy lại là chứng minh hết nhận sai trên webcam.

Lượt `packaged-ui-12-modes-052-bounded` nhận/đọc đúng Đau400 và qua kiểm chuyển mode, nhưng chỉ tự đọc1/12 clip Fusion, còn11 cần review, khung hình khoảng6,2–11,5fps: không đạt tính mượt. Hai phép kiểm tách nguyên nhân sau đó dùng cùng video lặp Sốt VSL100 nguyên pixel: mở mới đạt14,95fps, sau đổi400→100 đạt18,99fps; cả hai tự đọc đúng2 từ, không phải xác nhận. Chưa có bằng chứng lỗi tất định do giữ provider400; vẫn ghi nhận dao động tải/sampling. Không đổi threshold để biến các lượt này thành pass.

Lựa chọn fusion và numerical parity kế thừa [báo cáo phương pháp 0.5.1](FUSION_SELECTION_0.5.1.md). Không thay weights/preprocessing/boundary/threshold fusion trong 0.5.2. Kết quả 97,39% macro-F1 là nghiên cứu VSL100 đã có, không phải độ chính xác trong Clinic. Không training hoặc benchmark lớn.
