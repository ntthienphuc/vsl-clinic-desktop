# VSL Clinic — desktop demo 0.3.4

Ứng dụng chạy cục bộ trên một máy Windows, hai cửa sổ đồng thời cho bác sĩ và bệnh nhân.

Repo độc lập: [ntthienphuc/vsl-clinic-desktop](https://github.com/ntthienphuc/vsl-clinic-desktop). Mã Clinic nằm ngay thư mục gốc; repo không kèm ứng dụng Android/Flutter hay lịch sử Git của dự án Translator. Stack: Electron, React/TypeScript, Three.js/VRM và Python/FastAPI.

**Clone từ Git:** mã nguồn và bank chuyển động có trong repo; model/video cục bộ cần khôi phục theo [GIT_SETUP.md](docs/GIT_SETUP.md) trước khi chạy. EXE và dữ liệu gốc được giữ riêng trên máy.

- **Bệnh nhân → bác sĩ:** camera/video → phát hiện chuyển động → SL-GCN **400 từ riêng lẻ** → mỗi từ hiện ngay → ngừng một nhịp dài thì gom thành một lượt hội thoại.
- **Bác sĩ → bệnh nhân:** nói tiếng Việt hoặc gõ → semantic bank có kiểm soát → **65 ký hiệu, 58 mẫu câu** → avatar nam mặc áo trắng, có cánh tay, cổ tay và 30 xương ngón tay.
- Hai chế độ **Tự động** và **Xác nhận trước khi gửi**. Engine, nhận giọng nói và model ký hiệu đều chạy trên máy; không cần Android, Wi-Fi hoặc cloud.

## Mở bản chạy

Mở **`release/desktop-v0.3.4/win-unpacked/VSL Clinic.exe`** từ thư mục dự án, hoặc dùng shortcut **VSL Clinic 0.3.4** trên Desktop. Giữ cả thư mục `win-unpacked`; không chỉ chép EXE. Đóng phiên Clinic cũ trước khi mở phiên mới. Bản Windows này chưa có chứng thư ký mã; các bản cũ được giữ riêng.

**Bản chuẩn bị demo 31/10/2026:** avatar nam áo blouse dài hơn, tóc ngắn, kính mảnh, vật liệu ánh sáng mềm và mắt bớt cách điệu. Giữ bộ xương và bank chuyển động. Có **2 kịch bản / 10 lượt** trong **Chọn câu / từ → 2 kịch bản demo**, cùng [bộ video bệnh nhân](demo/HAI_KICH_BAN_2026-10-31/README.md). Sửa lỗi bộ dò đồng nghĩa chặn nhầm đoạn gồm nhiều câu đã có đủ mẫu; mất WebGL sẽ tạm dừng ký hiệu để tránh bỏ qua nội dung. Xem [bàn giao 0.3.4](docs/DEMO_0.3.4.md).

**Kiểm thử lại sau khi dừng hai tác vụ xử lý Lip:** cùng EXE/cấu hình đã đạt **20/20 lượt, 28/28 từ đúng thứ tự** qua hai vòng kịch bản bằng video; keypoint 24,3–30 fps, avatar hoàn tất đủ chuỗi. Các lần chạy trước ở 8–16 fps có nhận sai; guard dưới 12 fps hoặc khoảng trống hơn 250 ms không bảo đảm mọi kết quả trên ngưỡng đều đúng. Avatar dùng tối đa 30 fps khi phát, 12 fps khi chờ. Khi demo nên chỉ mở một phiên Clinic, tránh xử lý nặng đồng thời và thử thêm với đúng người diễn, webcam, micro. Xem bằng chứng và giới hạn trong [bàn giao 0.3.4](docs/DEMO_0.3.4.md).

Gói chứa engine, model ký hiệu, PhoWhisper INT8, avatar, font và video; không cần cài Python/Node để chạy. Menu **Bố trí màn hình** có sắp lại, đổi bên và toàn màn hình. Một màn hình thì hai cửa sổ chia đôi; hai màn hình thì mỗi vai trò một màn hình.

## Bắt đầu trao đổi

**Sửa giọng nói 0.3.3:** giữ bộ phát hiện lời nói bằng Silero ONNX cục bộ, chốt sau 576 ms không còn lời nói; không dùng âm lượng tiếng nền để khởi tạo câu. Câu dài chạm 12 giây chờ xem lại và cần ngắt nhịp trước lượt tiếp theo. Câu thiếu ký hiệu/mẫu câu hiện cảnh báo **Nói lại**, giữ nguyên chữ và không tự gửi. Lời nói lịch sự như “Y tá ơi, đo nhiệt độ nha” được bỏ từ đệm có kiểm soát để phát **Y tá → Nhiệt độ → Đo**; câu dài có alias được nhận diện sẽ hiện candidate đầy đủ và chỉ cảnh báo phần từ chưa phân loại. Phủ định, số lượng, thời gian và liên từ chưa được tự suy đoán. Ví dụ “Bạn cảm thấy thế nào?” chưa có ký hiệu “thế nào”; nói lại bằng mẫu “Bạn có đau không?” hoặc chủ động gửi chữ. Tất cả bản nháp vẫn giữ trong phiên, giao diện xem từng câu để tránh một danh sách cảnh báo dài. Xem [bản sửa và bằng chứng](docs/SPEECH_FIX_0.3.1.md).

1. Bác sĩ chọn **Camera / video**. Khi chưa có webcam, chọn **Video mẫu** và một nhãn. Với webcam, chọn camera phù hợp, thấy rõ mặt, vai, khuỷu và hai bàn tay.
2. Chọn **Tự động** hoặc **Xác nhận trước khi gửi**, rồi bấm **Bắt đầu cuộc trao đổi** một lần. Nguồn hình ảnh bắt đầu theo dõi; micro bác sĩ được mở nếu có thiết bị/quyền sử dụng. Không có micro vẫn nhập chữ được.
3. Bệnh nhân chỉ cần làm ký hiệu. Mỗi từ nhận xong xuất hiện trong khung **Người bệnh đang nói** ở bác sĩ, kể cả khi lượt dài còn tiếp tục. Danh sách tự cuộn tới từ mới.
4. Giữ hoặc hạ tay khoảng **0,7–1 giây giữa các từ** để model từ rời xác định ranh giới. Nghỉ khoảng **1,5 giây** sau hoạt động/kết quả cuối thì app gom lượt vào lịch sử. Nếu đang xử lý từ kế tiếp, app chờ xử lý xong trước khi chốt lượt.
5. Bác sĩ nói từng ý ngắn. **Tự động:** nhịp ngừng kết thúc một ý, câu được nhận rõ và có đủ ký hiệu sẽ tự gửi. **Xác nhận trước khi gửi:** mọi câu nói chờ bác sĩ đọc/sửa và bấm gửi. Câu thiếu ký hiệu, nghe chưa rõ hoặc bị cắt vì dài luôn được giữ để xem lại.
6. **Kết thúc** dừng camera, micro và phát ký hiệu; nội dung vẫn còn trong phiên. **Cuộc trao đổi mới** xóa nội dung RAM và vô hiệu kết quả cũ. Đóng cả hai cửa sổ để thoát app/engine.

Người bệnh có preview và avatar; hai nút phản hồi **Tôi đã hiểu / Xin giải thích lại** là tùy chọn. Các thiết lập camera nằm bên bác sĩ. Bố cục 16:9 dùng vùng cuộn riêng cho lịch sử và nội dung dài, có bố cục linh hoạt khi cửa sổ hẹp hoặc phóng chữ.

### Semantic routing và bank nghiên cứu 0.3.3

Các câu nói tự nhiên có từ đệm hoặc biến thể đã duyệt được đưa về canonical phrase trước khi phát. App vẫn giữ câu gốc, liệt kê từ đệm đã bỏ và chặn phủ định/số lượng/thời gian chưa có mẫu. `Tôi ăn cơm` hiện yêu cầu bác sĩ duyệt vì trật tự VSL và việc lược đại từ chưa được signer xác nhận. Chi tiết nằm ở [SEMANTIC_AND_BANK_PLAN.md](docs/SEMANTIC_AND_BANK_PLAN.md).

`tools/build_qipedc_bank.py` lập inventory corpus local và tạo NPZ keypoint nén theo batch khi được chỉ định; nó không tự đưa record chưa review vào runtime. Inventory QIPEDC chính thức và crosswalk nhãn được giữ riêng, không gộp ID với bộ 400 lớp nhận dạng.

## Từ hiện ngay, câu gom sau

Ví dụ: **Đau** hiện ngay → thêm **Mệt** thành **Đau · Mệt** → hết lượt thì hiện **Đau và mệt.** trong lịch sử. Phần diễn đạt là gợi ý có quy tắc, giữ từ gốc để đối chiếu. App không tự thêm vị trí đau hoặc triệu chứng theo câu hỏi bác sĩ. Các từ không chắc, phủ định hoặc chuỗi chưa có quy tắc giữ nguyên từng nhãn.

Hai ngưỡng độc lập: phân đoạn **từ** để gọi model và gửi ngay; nhịp ngừng **lượt** chỉ dùng để nhóm lịch sử. Không đợi hết câu mới gửi. Một lượt rất dài được chia sau 128 từ nhưng giữ đầy đủ các từ và thứ tự.

Model hiện vẫn nhận 400 từ riêng lẻ. Ký nối liền không có ranh giới có thể bị gộp thành một động tác; ghép từ thành lịch sử không biến model này thành bộ dịch câu ký hiệu liên tục.

## Bộ từ, câu và avatar

- **56 từ local** thuộc đúng bộ 400, thêm nhóm cảm giác, nhu cầu, vệ sinh, giao tiếp và thời gian. **9 từ QIPEDC** chỉ dùng cho avatar: Bụng, Tay, Sốt, Ngồi, Đo, Nhiệt độ, Cơm, Thở, Bệnh nhân; `model_id: null`.
- Bank local chọn **278 recording** từ **546 ứng viên**, 4–5 signer khai báo cho mỗi từ. Mỗi video demo được tách khỏi bank của từ đó; không phải tập đánh giá tách signer hoặc tách dữ liệu huấn luyện.
- **58 mẫu câu** gồm 40 mẫu khai báo và 18 tổ hợp chủ thể/vị ngữ. Tối đa 6 mệnh đề/24 ký hiệu một lượt. Ví dụ **Y tá đo nhiệt độ.** → Y tá → Nhiệt độ → Đo; **Ngồi nghỉ ngơi. Uống nước.** phát liên tiếp hai mệnh đề.
- Planner chỉ nhận đầy đủ mẫu/cấu trúc đã khai báo hoặc nhãn đơn. **Không đau**, **Uống 2 viên** chưa được hỗ trợ trọn vẹn; dùng **Chỉ gửi chữ** để giữ nguyên nội dung. Không bỏ phủ định/con số rồi phát phần còn lại.
- Avatar nam dùng thân và tay áo có skin liền với bộ xương; nội suy liên tục giữa frame, IK hai đoạn, giới hạn khớp, hướng lòng bàn tay và frame xương được vận chuyển liên tục để tránh xoắn đột ngột. Pause/resume/replay/tốc độ giữ chung timeline với chữ. Xem [chất lượng chuyển động](docs/MOTION_QUALITY.md).

N-best gốc giữ nguyên. Gợi ý ngữ cảnh chỉ dùng ứng viên sẵn có đủ điểm và câu bác sĩ thực sự đã trình bày gần đây. Runtime chưa có LLM sinh câu; phần diễn đạt dùng quy tắc hẹp để giữ nghĩa và giảm tải máy. Chi tiết: [VOICE_LANGUAGE.md](docs/VOICE_LANGUAGE.md).

## Demo và bằng chứng

[Kịch bản 8 lượt](demo/KICH_BAN_DEMO.md) và [thư mục tập bệnh nhân](demo/benh_nhan) gồm 13 video đánh số, giữ nguyên hash nguồn; tất cả nhãn nằm trong 400 lớp. Ví dụ `03_Met_Can_Nghi_ngoi`: `1.mp4` = Mệt, `2.mp4` = Cần, `3.mp4` = Nghỉ ngơi. Portable chứa cả thư mục `demo`.

Máy kiểm tra: i7-10750H, RAM 16 GB, GTX 1650 Ti 4 GB; model ONNX và ASR dùng CPU hai luồng. Avatar theo rAF tối đa 60 fps với giới hạn pixel GPU. Các mốc dưới đây là đo phần mềm trên máy này:

| Phép thử 0.3.0 | Kết quả |
|---|---|
| 6 video chạy theo clock thật, avatar đồng thời | 6/6 top-1 khớp mẫu, 0 lỗi capture |
| Hết ký hiệu theo segmenter → server có từ | Trung vị 579 ms, p95 722 ms |
| Server gửi → WebSocket nhận | Trung vị 2 ms, p95 3 ms |
| Gửi → frame avatar đầu | Trung vị 41 ms, p95 46 ms |
| 3 WAV tiếng Việt qua ASR | 3/3 có transcript; endpoint 540 ms + queue + decode trung vị 1.692 ms |
| Chuỗi Đau → Mệt, thêm khoảng nghỉ 800 ms | Cả hai từ gửi khi lượt còn mở, sau đó gom đúng một lượt |

Đây là thử tích hợp trên video/âm thanh có sẵn, không phải độ chính xác bộ 400, WER hay độ trễ hội thoại người thật. Bài thử nối hai clip không có nhịp nghỉ bị gộp từ và được giữ làm trường hợp giới hạn. Bằng chứng trong `docs/evidence/runtime-v0.3-duplex.json`, `speech-v0.3.json`, `live-turn-v0.3.json`, `live-turn-v0.3-no-pause.json`. Xem [bàn giao bản đóng gói](docs/DEMO_HANDOFF.md).

## Phát triển và tái tạo

Python 3.11, Node.js 22 trở lên:

```powershell
./tools/setup.ps1
npm start
```

Đóng bản app đang sử dụng thư mục đầu ra trước khi build:

```powershell
.venv/Scripts/python.exe tools/build_demo_kit.py
./tools/build.ps1
```

Build chạy pytest, test động học, audit rig thật, thu giấy phép, PyInstaller, Electron và đối chiếu SHA-256 payload. `BUILD_RECEIPT.json` lưu hash nguồn/đầu ra. `tools/probe_live_turn.py` kiểm tra luồng từ/lượt; `tools/realtime_probe.py` đo capture/hiển thị; `tools/probe_speech.py` gửi PCM theo thời gian thật. Portable dùng token ngẫu nhiên, engine chỉ nghe `127.0.0.1`.

`backend/`: engine; `desktop/`: Electron; `src/`: hai UI/avatar; `assets/`: runtime; `demo/`: kịch bản/video học; `research/`: nguồn/cache; `docs/evidence/`: bằng chứng; `release/`: bản chạy. Log engine: `%APPDATA%/VSL Clinic/clinic-engine.log`. Audio và hội thoại chỉ giữ RAM; video người dùng mở được lưu tạm trong phiên capture.

## Phạm vi

Chưa kiểm chứng webcam/micro hội thoại thật, hai monitor vật lý, máy Windows sạch khác hoặc người điếc hiểu avatar khi ẩn chữ. Kỹ thuật khớp đạt không chứng nhận nghĩa/độ tự nhiên VSL; vị trí chạm mặt/tay và nét mặt vẫn cần duyệt. Nguồn demo không phân biệt vùng theo lựa chọn của người dùng, không gắn nhãn chuẩn Đồng Nai. Xem [nguồn tài nguyên](THIRD_PARTY_NOTICES.md). Đồng bộ Git chỉ bao gồm phần Clinic; các thay đổi Android/server khác được giữ nguyên trong thư mục làm việc cũ.
