# Tài liệu VSL Clinic

[← Trang giới thiệu](../README.md)

Ứng dụng desktop trên một máy Windows, với hai cửa sổ dành cho bác sĩ và người bệnh. Bắt đầu ở nhóm tài liệu phù hợp bên dưới.

## Chạy và trình diễn

| Tài liệu | Nội dung |
| --- | --- |
| [Cài từ Git](GIT_SETUP.md) | Clone repo, khôi phục 107 đầu vào cục bộ, setup và kiểm tra checksum. |
| [Hướng dẫn sử dụng](USAGE.md) | Hai chế độ, camera/video, nhịp nghỉ và xử lý câu chưa hỗ trợ. |
| [Hai kịch bản demo](../demo/HAI_KICH_BAN_2026-10-31/README.md) | 10 lượt hỏi đáp, video tập theo từ và clip thử phần mềm. |
| [Bàn giao 0.3.4](DEMO_0.3.4.md) | Thay đổi gần nhất, phạm vi từ vựng, điều kiện kiểm thử và giới hạn. |
| [Kịch bản ban đầu](../demo/KICH_BAN_DEMO.md) | Bộ 8 lượt và tài liệu tập bổ sung. |

## Hiểu cơ chế

| Tài liệu | Nội dung |
| --- | --- |
| [Semantic routing và bank](SEMANTIC_AND_BANK_PLAN.md) | Alias có kiểm soát, coverage, QIPEDC và phân biệt bank avatar với 400 lớp nhận dạng. |
| [Giọng nói và ngôn ngữ](VOICE_LANGUAGE.md) | ASR cục bộ, n-best và diễn đạt có ràng buộc. |
| [Chất lượng chuyển động](MOTION_QUALITY.md) | Đồng bộ, retarget, giới hạn khớp và audit rig. |
| [Thiết kế ban đầu](DESIGN.md) | Lý do chọn kiến trúc và quá trình xây dựng; các số inventory ban đầu có thể khác 0.3.4. |

## Kiểm chứng và nguồn

| Tài liệu | Nội dung |
| --- | --- |
| [Kiểm tra checkout độc lập · 01/11/2026](evidence/standalone-source-check-2026-11-01.json) | 303 test Python, 6 test JavaScript, build và khôi phục dữ liệu. |
| [Thử lại hai kịch bản · 31/10/2026](evidence/idle-retest-summary-2026-10-31.json) | Hai vòng chạy video trên cùng EXE/cấu hình, sau khi giảm tải máy. |
| [Toàn bộ evidence](evidence) | JSON kiểm thử và provenance theo từng thời điểm; mỗi báo cáo có phạm vi riêng. |
| [Nguồn tài nguyên và giấy phép](../THIRD_PARTY_NOTICES.md) | Avatar, model, thư viện và giới hạn phân phối dữ liệu. |
| [Manifest đầu vào cục bộ](../local-assets-manifest.json) | Đường dẫn, dung lượng và SHA-256; không chứa các file model/video. |
| [Nguồn ảnh giới thiệu](media/README.md) | Screenshot thật của bản 0.3.4 và banner của repo. |

Các ghi chú [sửa giọng nói 0.3.1](SPEECH_FIX_0.3.1.md) và [bàn giao trước đây](DEMO_HANDOFF.md) được giữ làm lịch sử kỹ thuật. Khi chuẩn bị demo hiện tại, ưu tiên hướng dẫn 0.3.4.
