# VSL Clinic 0.7.5 · 20/11/2026

Ba câu gửi nhanh nằm ngay phía trên ô soạn. Nút Câu mẫu mở thư viện theo tình huống. Tab Từ điển ký hiệu dành riêng cho tra từ và xem động tác.

Bản đánh giá nội bộ dùng SL-GCN và nhánh hình ảnh Auto-AVSR với cross-attention. Mô hình mặc định nhận 100 từ qua tay và khẩu hình. Bác sĩ có thể chọn Chỉ ký hiệu (400 từ) trong Tùy chọn. Avatar có 200 mục. CPU lượng tử hóa động 48 lớp truyền thẳng của Conformer; GPU dùng FP32.

Bấm Bắt đầu ở màn hình bác sĩ. Chọn câu mẫu để gửi ngay, hoặc nói hay nhập câu. Khi camera lỗi, có thể tiếp tục trao đổi bằng chữ và câu mẫu. Người bệnh xem avatar và ký trước camera. Bấm Kết thúc trước khi tiếp người tiếp theo.

Trọng số môi được tách từ bản VLR có SHA-256 b38177ae98f1f3cbea1a4c183c2bca804cf0a576e99abd23aab85ae56f413280. Apache-2.0 áp dụng cho mã Auto-AVSR. Quyền phân phối trọng số và phạm vi sử dụng tại BV175 cần được xác nhận riêng. Tài liệu nhà phát triển: https://github.com/mpc001/auto_avsr#license . Các mục bên dưới lưu thông tin các phiên bản trước.

# VSL Clinic 0.7.4 · 20/11/2026

Ứng viên đánh giá cục bộ. Giữ 100 nhãn tay + khẩu hình, 400 nhãn chỉ ký hiệu và 200 chuyển động avatar. Bổ sung câu gọi người thân và mời viết. Khi Windows không mở được dịch vụ, hộp thoại có nút **Xem tệp chẩn đoán**. Gửi `clinic-startup.json` cho kỹ thuật viên để đối chiếu máy, phiên bản, đường dẫn và lỗi hệ thống.

Kết thúc phiên trong lúc mở camera hủy lần bắt đầu đang chờ. Bản sao video nhập vào được giải phóng khi dừng hoặc kết thúc phiên. Bộ cài yêu cầu thư mục trống hoặc bản Clinic đã cài. Kết quả kiểm và phạm vi sử dụng ghi ở `../Organization/Readiness074_2026-11-20`.

AV-HuBERT có giới hạn nghiên cứu phi thương mại và hạn chế cụ thể ở mục 2(a), gồm sử dụng trong sản xuất/vận hành và mục đích quân sự. Trước khi dùng tại BV175, cần làm rõ quyền sử dụng theo mục đích, đơn vị và bối cảnh dự kiến hoặc thay thành phần rồi đánh giá lại. Chưa nghiệm thu lâm sàng.

# Cập nhật 0.7.3 — 16/11/2026

Cập nhật bộ cài R2: không có trang chấp thuận giấy phép hoặc trang thông tin trước cài. Word `Giay_phep_VSL_Clinic.docx` cung cấp riêng và đi kèm thư mục `Tai_lieu` sau cài; giấy phép thành phần gốc tiếp tục được giữ. Hướng dẫn bản 03 dùng câu ngắn, thao tác trực tiếp. Runtime/model/giao diện ứng dụng không đổi trong lượt này; trạng thái build và kiểm thực tế ghi tại `../Organization/GuideSimpleSetup_2026-11-16`.

Kết quả người bệnh phía bác sĩ: top 1 xanh, top 2 và 3 vàng, cùng cỡ chữ 23 px và cùng độ đậm để đối chiếu ngữ cảnh. Nội dung được đọc vẫn là top 1. Hồ sơ đề xuất v4 định hướng thí điểm, phát triển phiên bản nâng cao và triển khai thực tế; có danh mục 200 từ avatar.

Trạng thái các lượt kiểm phát hành được ghi tại Organization/Revision073_2026-11-16. Phần dưới là hồ sơ phiên bản trước để đối chiếu.

# VSL Clinic 0.7.2 — 15/11/2026

Phạm vi đã chốt là **200 từ avatar**. Bản này sửa khuỷu tay xoắn sau nhiều động tác, làm liền tay áo, bổ sung kho từ xem trước, câu mẫu gửi ngay và hai luồng trao đổi song song. Source ứng viên đã qua kiểm dưới đây. **Trạng thái EXE/cài đặt/shortcut được chốt riêng tại `../Organization/AvatarReview_2026-11-15/ACCEPTANCE.json`; chỉ coi đã nghiệm thu khi biên nhận có `passed: true`.** Biên nhận build không thay cho kiểm bản cài.

## Hành vi hiện tại

- Người bệnh chỉ xem, không phải bấm nút. Chế độ nhận dạng nằm trong cài đặt bác sĩ; mặc định Ký hiệu + khẩu hình (100), Chỉ ký hiệu dùng 400. Kho avatar 200 là bộ riêng.
- Từ người bệnh đứng đầu hiện/đọc ngay; không beep, không chờ xác nhận. Bác sĩ thấy thêm top 2–3. Xanh biểu thị hạng đầu, không phải độ chắc đã hiệu chuẩn.
- Người bệnh ký trong lúc avatar đang chạy không gây tạm dừng hoặc hiện yêu cầu Tiếp tục. Micro bác sĩ tiếp tục nghe khi app đọc; câu bác sĩ mới được gửi sẽ ngắt avatar/giọng câu cũ và phát ngay. Câu cũ được ghi là đã ngắt; kết quả ASR còn chờ kiểm tra chưa gây ngắt. Tạm dừng thủ công và Kết thúc vẫn có hiệu lực.
- Một lần bấm câu mẫu gửi ngay, chống bấm đúp đồng thời, giữ bản nháp khác. 57 câu / 6 nhóm / 8 câu thường dùng; kho 200 từ có tìm không dấu, xem trước và thêm vào câu.
- VI/EN đổi giao diện; lời trao đổi, ký hiệu và giọng vẫn tiếng Việt. Bộ cài offline có lựa chọn GPU NVIDIA/CPU, chọn sẵn GPU khi phát hiện NVIDIA; CPU không cài runtime GPU.

## Avatar và lưu trữ

Solver giữ tham chiếu ổn định cho cánh tay và truyền góc xoay sang cẳng tay, tránh xoắn tích lũy làm thắt khuỷu tay. Tay áo dùng bề mặt liên tục, không thêm mô phỏng vải mỗi frame. Chỉnh độ rộng/sâu vạt áo để quần không xuyên ra hai bên. Các điểm chạm Bụng, Đọc, Sữa, Sốt, Bác sĩ và Mẹ có quy tắc theo thời gian nguồn. Hiệu chỉnh hình ngón tay khóa bằng hash nguồn, không ghi đè motion gốc.

96 từ bổ sung dùng VSL400 cục bộ, ba người ký/từ; không có tải video QIPEDC mới. Đã rà 12 ảnh theo thời gian của đúng video đại diện cho từng từ mới. 75/96 video đại diện khác video đầu tiên trong danh sách, nên ảnh đối chiếu cũ được giữ làm lịch sử, không dùng để xác nhận biến thể hiện tại.

Runtime 200 chuyển động: **6.613.972 byte**, từ **72.164.680 byte** JSON, sai số tọa độ tối đa **0,000063336** đơn vị vai. Có 265 mục giọng; đủ giọng cho 200 nhãn avatar, 169 mục cũ giữ nguyên hash. Đây là giảm phần chuyển động, không phải số đo giảm tổng Setup. Model nhận dạng/INT8/GPU giữ nguyên, không training.

## Kiểm chứng

Evidence: `../Organization/AvatarReview_2026-11-15/`.

- Python: **800 passed** (`release-python-final.log`); JavaScript: **35 passed** (`release-js.log`); TypeScript/Vite đạt (`doctor-interrupt-build.log`).
- Actual Electron: 200 từ × 4 ảnh = **800 ảnh**, đủ 200 lượt; kiểm lại riêng 16 từ sau hiệu chỉnh ngón tay. Lượt này dùng ảnh theo thời gian, không phải xem liên tục mọi frame hay chứng nhận nghĩa ký hiệu.
- Numerical actual-VRM: **266** trường hợp (200 từ + 66 câu), không lỗi số học; rig chạy nối tiếp 200 từ rồi về nghỉ có độ lệch góc tối đa **0°** tại cùng pha thở (`release-motion-audit.json`).
- Fixture hội thoại song song: video VSL100 có môi W068 ra/đọc Sốt khi avatar vẫn chạy; PCM tiếng Việt giả lập qua đường microphone/ASR tạo câu bác sĩ tiếp theo; micro mở một lần, không dừng khi hai luồng chồng nhau; Kết thúc xóa cả hai (`duplex-source/duplex-probe.json`).
- UI thật ở 375/570/754/768/1440 px; tìm kiếm, VI/EN, focus/Escape, kho xem trước, chế độ bác sĩ và màn hình người bệnh thụ động (`duplex-ui/`, `duplex-dictionary/`).
- Kiểm EXE, CPU/GPU, toàn bộ runtime/model/voice, source/package/installed parity, shortcut và dọn bản cũ: xem `ACCEPTANCE.json` nêu trên; không suy ra từ kiểm source.

## Giới hạn

Chưa kiểm người ký trực tiếp, loa/micro với vọng âm vật lý, tiếng ồn bệnh viện hoặc Windows sạch khác. Hình ngón tay/contact và mức hiểu được vẫn cần người thông thạo VSL đánh giá; một số chi tiết nguồn bị che khuất. Không tuyên bố 200 từ đều chính xác về ngôn ngữ. AV-HuBERT vẫn giữ điều kiện nghiên cứu/phi thương mại. Windows x64 AVX2 là nền tảng hiện hành; Raspberry Pi/Jetson chưa kiểm.

Giữ bản cài rollback 0.7.0 và lịch sử Git. Chỉ dọn các gói/cache sinh tự động đã xác định sau khi bản mới qua kiểm; không xóa nguồn nghiên cứu. Không push/publish/deploy.
