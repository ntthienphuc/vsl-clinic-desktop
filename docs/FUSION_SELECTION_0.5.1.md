# Lựa chọn fusion cho Clinic 0.5.1

Ngày 09/11/2026. Người dùng yêu cầu chọn phương pháp multimodal tốt nhất sẵn có
và giữ luồng từng từ mượt như sign-only, dùng dữ liệu VSL100 có hình ảnh môi.

## Quyết định

Chọn **SL-GCN + AV-HuBERT, cross-attention và learned gating** từ VSL100 R3.
Đây là cấu hình có macro-F1 trung bình cao nhất trong bảng so sánh VSL100 hiện có.
Giữ checkpoint fold01/seed17 như quy ước triển khai trước; không tìm seed/fold
tốt nhất trên clip Clinic, không training và không đổi ngưỡng để tăng số ca pass.
Contract mới: `vsl100-r3-slgcn-avhubert-xattn-f01-s17-clinic-v1`.

## Bằng chứng chọn model

Nguồn: `VSL100_R3_20261106/analysis/primary_report_20261106T204235Z/primary_all_models.csv`
và `reports/PRIMARY_RESULTS_20261107.md`. Kết quả trên 5.400 video VSL100,
6 fold × 3 seed; đây là kết quả nghiên cứu đã có, không phải accuracy đo trong Clinic.

| Cặp encoder / fusion | Macro-F1 trung bình (%) |
| --- | ---: |
| **SL-GCN + AV-HuBERT / cross-attention** | **97,39** |
| SL-GCN + VLR / cross-attention | 97,26 |
| SL-GCN + VLR / interaction concat | 97,15 |
| SL-GCN + AV-HuBERT / gated | 97,13 |
| SPOTER + AV-HuBERT / cross-attention | 97,06 |
| SPOTER + VLR / gated | 96,87 |
| SPOTER + VLR / cross-attention (Clinic 0.5.0) | 96,81 |

Cả ba learned fusion family đều được đối chiếu. Chênh lệch nhỏ trong cùng cặp
encoder không chứng minh một phương pháp luôn thắng trên mọi người ký.
Không so số Core60 với VSL100 và không dùng accuracy của sign-only400 làm
cùng một bài toán 100 lớp. Bảng đủ 20 cấu hình cùng hash nguồn nằm tại
`Organization/MultimodalIntegration_2026-11-09/fusion_explore/EXISTING_METHOD_RANKING.json`.

Khảo sát bên ngoài cũng cho thấy fusion tay/môi có nhiều thiết kế:
[SignMouth](https://arxiv.org/abs/2509.10266) kết hợp tín hiệu tay/môi và
contrastive learning cho PHOENIX14T/How2Sign;
[SignBind-LLM](https://cogvis-cvssp.github.io/papers/signbind/) dùng expert streams
và cross-attention để xử lý lệch nhịp tay/môi. Đây là các bài toán dịch ký hiệu
khác ngôn ngữ/dataset, không có bằng chứng chuyển trực tiếp thành checkpoint
VSL100 tốt hơn. Vì vậy bảng VSL100 ghép cặp và trọng số sẵn có là căn cứ chọn
cho app này. Không tuyên bố một SOTA toàn cầu.

## Kiểm nhỏ trên máy hiện tại

Ba clip đã chốt: Huy_T01_C1_W068 (Sốt), Học_T01_C1_W066 (Mệt),
Huy_T01_C1_W093 (Cần). Mỗi clip dùng cặp keypoint75×4 và mouth96×96 được
trích từ cùng video VSL100; hash nguồn/pixel/feature được đối chiếu.
GPU GTX 1650 Ti, Torch2.6.0+cu124, FP32, TF32 tắt.

- AV-HuBERT strict-load đủ536 keys; sai số feature tối đa1,17e-6 so cache gốc.
- SL-GCN strict-load đủ342 keys; sai số feature CUDA tối đa3,82e-6.
- Chạy cả hai encoder và fusion từ assets Clinic cho ra100 xác suất khớp
  `test_predictions.json`/`validation_predictions.json` của nghiên cứu;
  sai số tuyệt đối lớn nhất2,39e-7, cùng top1 cho cả3 clip.
- Thay riêng sign feature hoặc mouth feature bằng clip khác đều làm logits đổi;
  thiếu một nhánh trả unavailable. Đường chạy chính thực sự dùng cả tay và môi.
- Thử encoder độc lập sau lượt đầu: SL-GCN CUDA21,8–24,9ms;
  AV-HuBERT46,2–131,2ms, gồm một lượt đầu còn khởi động GPU.
  Các lượt AV-HuBERT sau đó chủ yếu46–78ms.
  Đây chưa phải độ trễ hiển thị/giọng của app.
- Chạy tích hợp3 clip: encoder wall340/95/80ms; peak CUDA allocated1394,72MiB.
  Lượt đầu có chi phí khởi động; không gọi các số này là p95 ổn định.

Raw receipts: `fusion_explore/{avhubert_cuda,slgcn_cuda,slgcn_cpu,current_cuda,clinic-r3-parity}/REPORT.json`.
Full UI/EXE và lifecycle phải được ghi riêng trong trạng thái phát hành0.5.1.

## Contract và đóng gói

Giữ preprocessing camera1080/25fps/crop96→88 và ranh giới từng từ.
SL-GCN dùng đúng pose-format0.15.0,27 joints,bone stream,repeat pad150;
chỉ uniform toàn đoạn khi dài hơn150. AV-HuBERT encode toàn chuỗi môi trước
uniform tối đa96 feature tokens. Feature dimensions256/1024, layer norm theo
đúng chiều, class order W001…W100 giữ nguyên. Hai encoder chạy tuần tự trênGPU
để giảm tranh chấpCPU với MediaPipe; chế độCPU dùng cùng toán học khi không cóCUDA.

Lượt12 clip đầu trong UI được lưu nguyên ở `source-ui-final-r3-source`:
6 automatic đúng,6 review,11/12 top1; ca lặp Sốt cần review nên probe dừng.
Chẩn đoán trên cùng pixel/chính checkpoint cho thấy cắt active-core với250ms
context làm điểm Sốt giảm0,948→0,609; giữ500ms lead-in và ảnh đã thấy đến
decision cho0,926. Đây là kiểm lỗi tích hợp sau quan sát fixture,
không phải validation độc lập hay điểm accuracy mới.
Clinic vì vậy dùng `clinic-r3-elbow140-context500-400-v1`:500ms trước core,
tối đa400ms sau core nhưng chỉ đến decision hiện tại.
Không đổi ngưỡng confidence/margin0,8/0,25, không đổi thời điểm endpoint,
không xem frame tương lai và không chờ hết câu.
Đoạn đầu có thể chứa cử động môi trước khi khuỷu tay vượt ngưỡng.
Kiểm natural replay sau thay đổi được báo riêng.

Fairseq trainer/registry không được nhập. Adapter chỉ thực thi các định nghĩa
inference nguyên bản đã hash, giữ strict state loading. Sai số feature và
xác suất đã được đối chiếu với output nghiên cứu trước khi đổi đường chạy chính.
Tất cả phụ thuộc được đặt trong Clinic; app không cần thư mục nghiên cứu khi chạy.

AV-HuBERT is licensed under the AV-HuBERT license, Copyright (c) Meta
Platforms, Inc. All Rights Reserved. Bản license gốc kèm package; đây là bản
demo nghiên cứu cục bộ phi thương mại. License upstream giới hạn mục đích sử dụng,
bao gồm commercial/production; bản tích hợp này không cấp quyền triển khai sản xuất.
[License gốc](https://github.com/facebookresearch/av_hubert/blob/main/LICENSE).
