# Kiểm tra chuyển động avatar

## Ngoại hình 0.3.4 — 31/10/2026

Giữ nguyên rig nam và các motion. Runtime thay vật liệu toon bằng vật liệu nhận ánh sáng mềm; giảm vùng mắt đồng thời biến đổi cả morph delta để blink/câu hỏi vẫn khớp. Tóc card anime được ẩn, thay bằng một bề mặt tóc ngắn liền. Thêm kính mảnh, phục hồi cà vạt tối, kéo dài phần áo có skin và thêm cúc/bảng tên. Không thay chiều dài cánh tay, xương/ngón tay, model nhận dạng hay dữ liệu tham chiếu.

Mất WebGL trong lúc phát sẽ hiện thông báo và gửi tạm dừng đến phiên chung; khôi phục hình ảnh không tự nhảy qua phần còn lại. Telemetry cục bộ có số frame, fps trung bình, CPU submit và khoảng cách frame để kiểm tra trên Electron thật. Audit IK vẫn kiểm tra rig/khớp; nó không thay thế việc xem mesh, tiếp xúc tay–mặt hoặc đánh giá hiểu ký hiệu bởi người dùng VSL.

Ngoại hình mới vẫn là nhân vật 3D cách điệu. Không mô tả là người thật hay dùng các ảnh của bản cũ làm bằng chứng cho bản này.

## Nền chuyển động từ bản 0.3.0

- **Avatar nam:** `ClinicMale.vrm`, Sakurada Fumiriya (CC0 theo trang riêng của pixiv). Thân/tay áo giữ mesh và skin nguyên bản, đổi màu áo trắng và thêm ống nghe/thẻ tên nhỏ. Các mảnh áo cứng ghép bên ngoài của bản cũ được bỏ khỏi đường render hiện tại. Tên morph legacy được chuyển sang metadata mà GLTFLoader hiểu; provenance giữ cả hash gốc và runtime.
- **Độ nét:** khử răng cưa, pixel ratio 1,5–2 với ngân sách 2,4 triệu pixel; viền được giảm. Camera tự căn đầu–hông và bề ngang ký hiệu; rAF theo màn hình tới 60 fps. Giới hạn pixel giúp dành CPU/GPU cho nhận dạng.
- **Nội suy:** cubic Hermite đơn điệu, đi qua pose đã đo và không vượt tọa độ hai frame lân cận. Hướng xương tay được vận chuyển từ frame trước, tránh điểm kỳ dị khi shortest-arc từ T pose gặp hướng đối diện. Lần audit đầu phát hiện 38 bước xoay >90° ở nhiều case (có lặp trong câu); sửa frame xương rồi chạy lại **124 case, 0 lỗi**, giữ nguyên gate.
- **Bank:** 65 từ (56 local + 9 QIPEDC), 58 mẫu và một chuỗi nhiều mệnh đề. Local có 546 candidate recording, chọn 278 reference, 4–5 signer khai báo cho mỗi từ. Các motion cũ được giữ nguyên byte để các profile nối câu đã duyệt vẫn khớp hash.

Audit `evidence/motion-audit.json` hiện dùng rig nam, 30 Hz, 124 case; có hash avatar và code. Sai số IK tối đa trong lần kiểm tra < 1e-12 m. Đây là tính nhất quán số học của khung xương, không phải sai số ký hiệu/tiếp xúc da trong đời thật. Test riêng kiểm tra arm qua hướng đối diện T pose và nội suy không overshoot. Các ảnh `motion-review-v0.2.1-*.png` bên dưới là bằng chứng của rig cũ, không đại diện ngoại hình nam mới.

## Bổ sung ở bản 0.2.1

Bank ở bản đó có 29 từ (20 consensus local + 9 clip QIPEDC đơn), 36 mẫu câu và timeline nhiều mệnh đề. Audit lúc đó gồm 66 trường hợp: mọi từ, mọi mẫu và một chuỗi ba câu. Window Bệnh nhân W00248 giới hạn 1.500–4.200 ms sau khi xem source: loại lượt lặp góc nghiêng, giữ nguyên video gốc.

Đã tìm thấy ngón cái Cơm đổi góc 93,14° trong một frame ở khoảng 800 ms: depth nhiễu kéo anchor gốc ngón cái ra sau cổ tay, khiến phép chiếu cone lật đột ngột. Profile v2 giới hạn anchor về phía ngón trỏ của lòng bàn tay trong cone 45° và lọc anchor trước khi áp CMC. Giữ gate 90°, chạy lại 66 trường hợp không còn lỗi này; không nới ngưỡng để che spike.

Avatar được thêm áo blouse, ống nghe và thẻ tên bằng hình học gắn theo rig. Tư thế nghỉ đưa cổ tay ra ngoài vạt áo; envelope phía trước thân được tăng theo chiều sâu áo trước bước lọc/IK. Bản cuối đã chạy lại toàn bộ 66 trường hợp cùng áo và profile v2, không có lỗi hình học bắt buộc. Envelope chỉ bảo vệ mục tiêu cổ tay: không được suy ra rằng toàn bộ cẳng tay/ngón tay đều có collision mesh chính xác.

Bốn mẫu câu hỏi có/không dùng morph chân mày có sẵn, cộng hướng đầu nhẹ, với trọng số vào/ra theo đồng hồ phát. Pause giữ nguyên pha hỏi, stop trả về trung tính. Không dùng biểu cảm ngạc nhiên có miệng mở để thay câu hỏi. Các tín hiệu này cần người ký Đồng Nai thẩm định. Chi tiết câu và nguồn QIPEDC: [VOICE_LANGUAGE.md](VOICE_LANGUAGE.md).

## Quy tắc đang dùng

Profile `clinic-articulation-v2` trong `src/avatar/kinematics.ts` là bộ guardrail kỹ thuật của demo. Các con số không được trình bày như giới hạn sinh lý đã kiểm định.

1. Bank dùng shared DTW để căn pha, medoid làm mốc và trọng số chất lượng cho các reference. Mỗi signer đóng góp tối đa một recording vào consensus để tránh một người lấn át trung bình.
2. Hướng lòng bàn tay được trung bình trên SO(3). Hướng các đốt ngón được tổng hợp trong hệ tọa độ của lòng bàn tay; vị trí thiếu vẫn có mask/imputation và provenance. Chiều dài đốt dùng median cố định.
3. Cánh tay dùng IK hai đoạn với chiều dài xương VRM thật. Lọc vị trí cổ tay trước khi giải, tránh việc lọc từng xương làm bàn tay trượt khỏi mục tiêu. Bend plane giữ liên tục khi khuỷu gần duỗi.
4. MCP của bốn ngón có gập và xòe; PIP/DIP gập trong một mặt phẳng. Bộ fit có ràng buộc xét cả ba hướng đốt cùng nhau, sau đó lọc các góc. Ngón cái giữ đối ngón 3D và cone riêng.
5. Mỗi đốt dùng một frame đầy đủ, bao gồm trục bản lề. Chỉ khớp một vector hướng bằng shortest-arc quaternion đã gây xoắn đột ngột khi ngón gập sâu; lỗi này được tìm thấy bằng đo quaternion trên hierarchy VRM thật và đã sửa.
6. Góc khuỷu 3–155°, MCP gập −20–100°/xòe ±30°, PIP −8–115°, DIP −10–85°; cổ tay có envelope gập và lệch bên. Motion follower hạn chế tốc độ góc và quá trình tăng tốc. Chiếu lại vào giới hạn cứng hoặc phanh có thể vượt acceleration cap tạm thời; không có cam kết jerk/acceleration tuyệt đối của mọi xương.
7. Tay gần mặt được hiệu chỉnh theo mốc mũi/mắt và tỷ lệ avatar. Hai tay gần nhau nhận cùng phần dịch. Tay buông được hiệu chỉnh theo tỷ lệ chiều dài tay nguồn để tránh khuỷu co ở hông. Torso envelope chỉ xử lý mục tiêu cổ tay, không phải va chạm mesh toàn thân.

## Bằng chứng đã lưu

- `evidence/motion-audit.json`: báo cáo hiện tại 124 trường hợp, hierarchy và normalized humanoid từ VRM nam thật, 30 Hz, gồm intro/outro, các từ nối và nhiều câu. Có SHA256 avatar, motion và ba module điều khiển.
- Audit đo finite transforms, góc ngón/khuỷu, IK reach error, correction, vận tốc/gia tốc cổ tay và vận tốc góc xương thực tế. Bước xoay >90°/frame làm thất bại; sau sửa không còn trường hợp vượt gate. Discontinuity ghi cả tên xương, thời điểm và góc khi có lỗi.
- `evidence/motion-review-v0.2.1-1.png` đến `motion-review-v0.2.1-6.png`: 87 cặp avatar/video ở 25%, 50%, 75%, có áo bác sĩ và đúng source window QIPEDC. Đây là cùng pha chuẩn hóa, không phải mọi frame được căn DTW hoàn toàn tương ứng. Bốn ảnh bản 0.2 cũ vẫn được giữ.
- Trang `tools/review_motion.html` qua Vite HTTP: chuyển từ, chạy/dừng, tua và xuất sáu bảng. rAF của UI patient quan sát khoảng 28,6 fps, frame và nhãn đổi từ Y tá sang Đo trong cùng lượt; pause giữ pha. Route lưu ảnh chỉ có ở Vite dev, không đưa vào portable.

## Giới hạn cần giữ rõ

**Chuyển động đã có ràng buộc hình học; chưa được xác nhận là phiên dịch VSL tự nhiên, đúng nghĩa.**

- Phần local hiện có 278 reference được chọn thuộc 5 mã signer, chưa đủ để khẳng định “chuyển động trung bình chuẩn”; chín nguồn QIPEDC được theo dõi riêng. Pose 3D đơn camera có nhiễu depth; các góc ngón cần correction lớn ở một số từ. Audit giữ các cờ này để review, không xóa chúng bằng cách nới ngưỡng. Các từ mới chưa có đánh giá hiểu ký hiệu với người điếc.
- Sau hiệu chỉnh, dáng tay nghỉ và vùng tay–mặt đã cải thiện. Một số tiếp xúc vẫn chỉ gần đúng: Ngủ ở vùng mắt/má, Ốm/Giúp đỡ ở tay đỡ cẳng tay, Cần/Xin lỗi/Dừng lại ở tiếp xúc hai tay. Chưa có solver tiếp xúc ngón–da hoặc chứng nhận không xuyên mesh. Không được dùng kết quả audit số để khẳng định những tiếp xúc này đã chính xác.
- Nguồn QIPEDC một video không có trung bình nhiều signer. Tỷ lệ điểm nội suy/neutral có thể lớn, đặc biệt tay không hoạt động; correction lớn ở Bụng/Bệnh nhân được giữ trong audit. Tiếp xúc Sốt còn lệch vùng trán xuống mắt/mũi ở một số pha; Nhiệt độ và Ngủ cần duyệt vị trí tay–mặt. Tư thế cúi người của Ngồi chưa tái tạo đầy đủ. Không coi mọi chuyển động là đã đúng chỉ vì không gãy khớp.
- Ngón cái có cone 3D, chưa phải mô hình giải phẫu đầy đủ. Có chân mày/hướng đầu cho câu hỏi nhưng chưa đầy đủ khẩu hình/ngữ pháp phi thủ công. Câu ngoài catalogue/ngữ pháp khai báo bị chặn ở chế độ ký hiệu; có thể gửi chữ nguyên văn.
- Cần người sử dụng VSL kiểm tra blind nhận diện từng từ, vị trí tiếp xúc, hướng lòng bàn tay, handshape và nhịp trước khi dùng như kênh giao tiếp chính. UI luôn giữ nguyên chữ để đối chiếu.

## Chạy lại

```powershell
npm test
node tools/audit_motion.mjs
$env:CLINIC_ENGINE_ORIGIN = 'http://127.0.0.1:<port backend đang chạy>'
npm run dev -- --port 8770
```

Mở `http://127.0.0.1:8770/tools/review_motion.html`. Các bản H.264 review trong `research/review` chỉ phục vụ so sánh trên trình duyệt; video gốc không bị thay đổi. Audit hiện nằm trong `tools/build.ps1` để các sửa đổi tiếp theo phải qua cùng kiểm tra.
