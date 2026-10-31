# VSL Clinic — quyết định kiến trúc, cập nhật 22/10/2026

## Cập nhật 0.2.1

Phạm vi hiện tại là 400 từ nhận dạng, 29 động tác avatar (20 consensus local + 9 nguồn QIPEDC đơn), 36 mẫu câu có kiểm soát và timeline nối nhiều mệnh đề. Từ bổ sung QIPEDC có `model_id: null`, không thay đổi classifier. Phiên chung quản lý hàng đợi, pause/resume, hủy và câu thực sự đang được trình bày; n-best chỉ tham khảo ngữ cảnh đã phát gần đây. Chi tiết ở [VOICE_LANGUAGE.md](VOICE_LANGUAGE.md).

Hai UI ưu tiên viewport 16:9: người bệnh xem avatar, chữ, phản hồi và preview; bác sĩ có composer, kết quả và lịch sử. Danh mục câu/từ, nguồn camera/video và chẩn đoán kỹ thuật nằm trong hộp mở theo nhu cầu. Chỉ các vùng nội dung dài cuộn riêng. Bộ `demo/benh_nhan` có tám lượt và 13 video đánh số, toàn bộ nằm trong bộ 400. Bằng chứng hiện tại và giới hạn sử dụng ở [DEMO_HANDOFF.md](DEMO_HANDOFF.md); mốc 0.2 dưới đây ghi lịch sử mở rộng.

## Cập nhật 0.2 — 22/10/2026

Mốc 0.2 bổ sung nhập giọng nói tiếng Việt offline bằng PhoWhisper-base INT8, tám mẫu câu ban đầu, tín hiệu hỏi trên mặt/đầu, gợi ý từ có xác nhận và ứng viên n-best liên quan câu hỏi gần nhất. Mô hình sign 400 lớp và dữ liệu gốc được giữ nguyên. Bộ câu đã mở rộng ở 0.2.1; không dùng LLM tự sinh nội dung trong runtime.

## Phạm vi đã thống nhất

Một ứng dụng Windows chạy trên một máy tính, mở đồng thời cửa sổ **Bác sĩ** và **Bệnh nhân**. Khi có hai màn hình, mỗi cửa sổ được đặt lên một màn hình; một màn hình vẫn dùng được với hai cửa sổ. Không cần Android, LAN, tài khoản hoặc dịch vụ đám mây để trò chuyện.

- Bệnh nhân → bác sĩ: camera PC → landmark → phân đoạn → SL-GCN ONNX 400 gloss → chữ và trạng thái nhận dạng.
- Bác sĩ → bệnh nhân: tiếng nói/nhập chữ → bác sĩ xem lại → planner câu có kiểm soát → timeline gloss → reference motion → avatar VRM có cánh tay, cổ tay và đầy đủ ngón tay.
- Demo avatar gồm 20 từ có trong bộ 400 và 9 từ QIPEDC bổ sung, ưu tiên bệnh viện và giao tiếp cơ bản.
- Hiện chưa có webcam: kiểm chứng bằng video có sẵn, phát theo đồng hồ thật qua cùng hàng đợi/nhận dạng. Kiểm thử webcam thật là giới hạn cần ghi rõ.
- Đây là nhận dạng từ riêng lẻ và phát chuỗi gloss. Chưa có bằng chứng dịch ngữ pháp câu VSL hoặc đủ tin cậy cho quyết định lâm sàng. UI giữ nguyên văn bản bác sĩ, cho phép đối chiếu/xác nhận và không tự suy diễn từ chưa hỗ trợ.

## Nguồn đã khảo sát

1. Translator local `vsl_server/app.py`, `data/utils.py`, `pipelines/slgcn_onnx_inference.py`: phân đoạn theo khuỷu tay/vùng ký hiệu, debounce, timestamp đơn điệu, buffer hữu hạn, inference 27 điểm `[N,3,150,27,1]`; kênh thứ ba là confidence, không phải chiều sâu. Model SL-GCN SHA256 `582f3d8712f73f78c5fe7b7521609ea54a9257e5a3a877aa8c9346b8e28ebb21`.
2. Signova local `E:/Project/Signova/signova_practice_i_final`: bank gồm nhiều exemplar, shoulder normalization, median/tolerance; trajectory hiện là 2D. Không dùng trực tiếp các file 2D này như dữ liệu xương 3D.
3. `E:/Project/pose-reference-toolkit`: chọn exemplar hoàn chỉnh, một đường DTW chung cho các joint, mask tracking và lineage. Giữ nguyên repo tham khảo. Thuật toán mới ghi rõ các phần học lại và các thay đổi phục vụ tổng hợp chuyển động.
4. [MediaPipe Pose](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker) và [Hands](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker): pose world và hand world dùng tâm gốc khác nhau. Phải ghép tay tại wrist, thống nhất hệ tọa độ và scale trước retargeting.
5. [three-vrm humanoid API](https://pixiv.github.io/three-vrm/docs/classes/three-vrm.VRMHumanoid.html): normalized bone transforms cho rig người và ngón tay. [Electron screen](https://www.electronjs.org/docs/latest/api/screen/) hỗ trợ liệt kê và đặt cửa sổ lên từng màn hình.
6. [Spoken-to-signed pipeline](https://github.com/sign-language-processing/spoken-to-signed-translation): tham khảo cấu trúc text → gloss → pose và báo coverage. Dự án này không cung cấp model dịch câu VSL cho ứng dụng của chúng ta.
7. [Semantics2Hands](https://arxiv.org/abs/2308.05920): hình học bàn tay ảnh hưởng ý nghĩa khi chuyển motion giữa avatar. [Kinematic retargeting](https://arxiv.org/abs/2103.08882) nhấn mạnh ràng buộc hình học/quan hệ giữa hai tay. Không nhận các kết quả của hai bài là kết quả ứng dụng này.

## Phương án được chọn

### Desktop và realtime

Electron + React/TypeScript cho hai UI, Three.js/VRM cho avatar. Python/FastAPI chỉ bind loopback, được tiến trình desktop sở hữu và đóng cùng app. Một process nhận dạng chung, trạng thái phiên trong RAM, không cần Redis hoặc một server chạy riêng do người dùng quản lý.

Camera/video được đọc theo đồng hồ thật. Preview và detector tách luồng; hàng đợi detector giữ tối đa một frame đang chờ, thay frame cũ bằng frame mới và đếm số frame bỏ. Inference segment chạy ở worker riêng; không làm dừng capture hoặc UI. Giới hạn hàng đợi segment và thông báo quá tải. Reset/stop dùng generation để kết quả cũ không sang phiên mới. WebSocket phát trạng thái và kết quả tới hai cửa sổ; một snapshot đồng bộ khi reconnect.

Giữ model, thứ tự joint và preprocessing SL-GCN đã kiểm tra. Capture PC dùng MediaPipe Tasks Pose Lite + Hands, hai worker song song trên ảnh tối đa 640 px; profile `clinic-pc-tasks-lite-parallel-v2`. Mỗi video decoder dùng một thread, ORT dùng hai thread CPU không spin-wait. Đây là cấu hình được chọn sau đo thành phần và chạy hai UI đồng thời; không khẳng định tương đương detector Android. Timestamp từ video/camera đơn điệu; mirror chỉ dùng ở preview. Holistic là thử nghiệm ban đầu đã được thay thế.

### Reference bank và avatar

Tạo bank mới từ các video local được người dùng chỉ định. Lưu mã gloss/model_id, video_id, signer_id khai báo trong metadata, SHA256, extractor/profile, FPS/timestamps, mask, chất lượng và các ID được dùng. Có 5 mã signer trong metadata cho mỗi từ demo; đây không phải xác minh độc lập danh tính người ký.

Trích pose world 33 điểm cùng hand world 21 điểm mỗi bên. Tách khỏi tensor recognition 2D/confidence. Normalize theo vai, gắn tay tại cổ tay, giữ hướng lòng bàn tay. Căn thời gian bằng DTW có band, cùng một đường cho toàn bộ cơ thể và hai tay. Chọn medoid, căn các lần thực hiện về medoid, tạo consensus có trọng số và giữ exemplar/độ phân tán để so sánh. Không lấy trung bình tọa độ ở các thời điểm chưa căn pha. Không coi điểm tracking bị mất là quan sát thật.

Bank v2 lấy consensus hướng lòng bàn tay trên SO(3), rồi tổng hợp hướng từng đốt trong hệ tọa độ lòng bàn tay trước khi ghép lại. Cách này tránh trộn góc cổ tay với độ gập ngón khi lấy trung bình hướng trong không gian toàn cục. Mỗi đốt được dựng lại với chiều dài median cố định. Có 99 reference thuộc 5 mã signer; một video mỗi từ đã được tách khỏi bank trước chọn mẫu, nhưng không phải đánh giá độc lập signer hay dữ liệu huấn luyện.

Chín từ bổ sung dùng một video QIPEDC mỗi từ, giữ checksum, URL, source window và lượng điểm nội suy. Không gọi các motion này là consensus nhiều người. Bệnh nhân W00248 dùng phần chính diện 1.500–4.200 ms sau kiểm tra video; raw source giữ nguyên và không nằm trong gói portable.

Retarget sang VRM giữ chiều dài xương, lọc mục tiêu cổ tay rồi giải IK hai đoạn chính xác. Bend plane của khuỷu được duy trì khi tay gần duỗi. Các động tác gần mặt dịch theo mốc mũi/mắt của avatar; hai tay gần nhau nhận cùng phần hiệu chỉnh để giảm phá vỡ quan hệ. Tư thế tay buông dùng tỷ lệ chiều dài tay nguồn, tránh co tay ở hông do tỷ lệ vai khác nhau.

Ngón tay được giải trong mặt phẳng gập: MCP có độ xòe và gập, PIP/DIP có trục bản lề; ba góc được fit cùng nhau trong miền giới hạn rồi lọc theo thời gian. Ngón cái giữ đối ngón 3D với giới hạn cone riêng. Mỗi đốt được điều khiển bằng frame đầy đủ gồm hướng và trục bản lề, tránh lỗi xoắn khi chỉ dùng shortest-arc quaternion từ một vector. Có giới hạn khuỷu/cổ tay, phát hiện bàn tay suy biến và các chỉ số correction. Đây là guardrail kỹ thuật, không phải giới hạn sinh lý đã kiểm định.

Animation dùng `requestAnimationFrame`, render mục tiêu 30 FPS, đồng hồ motion và blend ngắn giữa gloss. Có phát lại, tạm dừng, tốc độ và xem gần bàn tay. Audit đọc hierarchy VRM thật, kiểm tra góc, finite transforms, IK và thay đổi quaternion theo frame; các bước xoay lớn hơn 90° trong 1/30 giây làm audit thất bại. Kiểm tra số không chứng nhận va chạm mesh, nét mặt hay độ hiểu đúng VSL. Bảng hình đối chiếu và các hạn chế nằm trong `docs/evidence` và `docs/MOTION_QUALITY.md`.

Avatar mẫu pixiv `VRM1_Constraint_Twist_Sample` có đầy đủ các xương cần dùng. Metadata nhúng cho phép chỉnh sửa và phân phối theo [VRM Public License 1.0](https://vrm.dev/en/licenses/1.0/). Giữ attribution/metadata và hash trong notices. Đây là model đồ họa mẫu, không phải người phiên dịch đã được kiểm định.

### Text và giao tiếp bệnh viện

20 gloss local: Bác sĩ, Y tá, Bệnh viện, Khám bệnh, Đau, Mệt, Khỏe, Ốm, Ăn, Uống, Nước, Nghỉ ngơi, Ngủ, Cần, Giúp đỡ, Dừng lại, Cảm ơn, Xin lỗi, Đúng, Đồng ý. Chín mục chỉ cho avatar: Bụng, Tay, Sốt, Ngồi, Đo, Nhiệt độ, Cơm, Thở, Bệnh nhân.

Chuẩn hóa Unicode tiếng Việt, giữ dấu và so cụm dài nhất; sau đó mỗi mệnh đề phải khớp mẫu hoặc ngữ pháp đã khai báo. Biết từng từ chưa đủ để chấp nhận câu tùy ý. Phải phủ được toàn bộ nội dung trước khi phát avatar; không tự bỏ phủ định, số lượng hoặc từ ngoài bank. Nội dung chưa đủ coverage vẫn có thể gửi nguyên văn dưới dạng chữ, với lựa chọn rõ trên UI. Không tự thay thế từ ngoài từ vựng bằng từ gần giống. Các kết quả nhận dạng là ứng viên có thể sửa/xác nhận; lịch sử không tự trở thành hồ sơ y tế.

## Kiểm chứng bắt buộc

- Kiểm tra hash/model 400 labels, finite logits và parity preprocessing với nguồn kế thừa.
- Realtime paced video qua capture → detector → segment → inference → WebSocket → UI; đo FPS, queue/drop, inference và độ trễ end-of-gesture → hiển thị.
- Hai UI nhận cùng revision, kết nối lại nhận snapshot; stop/reset không hiển thị kết quả cũ.
- Text → avatar: coverage đầy đủ, từ chưa hỗ trợ, gửi liên tiếp, pause/replay/speed, độ trễ bắt đầu.
- Bank 29 từ: lineage, số nguồn, shared DTW cho consensus local, source window QIPEDC, dữ liệu hữu hạn, mask và xương không đổi chiều dài; kiểm tra các pose khác thời điểm, ngón tay và toàn bộ timeline câu.
- Mở app thật, quan sát hai UI và avatar nhiều thời điểm, không lỗi console; thử kích thước cửa sổ khác nhau.
- Đóng/mở lại app, xác minh tiến trình backend do app sở hữu được giải phóng. Chạy bản đóng gói ngoài source khi hoàn tất.

Chỉ báo cáo các phép đo và kiểm tra đã thực hiện. Video replay không xác nhận độ chính xác hội thoại trực tiếp; webcam thật và người dùng VSL cần đánh giá tiếp sau demo.
