# Semantic routing và reference bank — hướng nâng cấp 0.3.3

## Kết luận sau khi rà lại flow

Luồng bác sĩ hiện có hai phần khác nhau:

1. Nhận tiếng Việt và hiểu ý định câu.
2. Chọn chuỗi ký hiệu, nối chuyển động và phát avatar.

Việc thêm video vào bank chỉ giải quyết phần thứ hai. Nếu vẫn đưa từng từ tiếng Việt vào planner theo đúng thứ tự nói, câu như `Y tá ơi, kiểm tra thân nhiệt giúp em nhé` vẫn dễ bị rơi vào cảnh báo thiếu mẫu. Vì vậy bản nâng cấp dùng một lớp semantic routing ở giữa. Lớp này chỉ được đưa câu về một mẫu đã duyệt; nó không tự sinh gloss ID và không được phép bỏ phủ định, số lượng, thời gian, vị trí cơ thể hoặc mức độ.

## Kiến trúc đã chốt

```text
PhoWhisper / ô nhập
        |
        v
giữ câu gốc + tách mệnh đề
        |
        v
semantic bank (alias, từ đệm, intent, mẫu câu)
        |
        +-- auto: mọi token đã được giải thích, canonical phrase đã có trong planner
        |
        +-- review: có ý định gần đúng nhưng cần bác sĩ duyệt
        |
        +-- block: còn từ chưa biết hoặc nghĩa nguy hiểm bị bỏ sót
        v
TextPlanner hiện tại -> gloss ID allowlist -> motion bank -> avatar
```

`assets/semantic_bank.json` và `backend/semantic_router.py` là seed đầu tiên. Ví dụ:

- `Y tá ơi, kiểm tra thân nhiệt giúp em nhé` → `Y tá → Nhiệt độ → Đo`, với các từ đệm được ghi lại.
- `Bác sĩ ơi, đo nhiệt độ nha` → `Bác sĩ → Nhiệt độ → Đo`.
- `Tôi ăn cơm` → **chờ duyệt**, vì việc đổi trật tự và lược đại từ phụ thuộc ngữ cảnh VSL; app không phát tự động phần còn lại rồi giả vờ đã dịch đủ.
- `Y tá ơi, không đo nhiệt độ` → bị chặn; từ `không` không được xem là từ đệm.

Planner thông thường vẫn là cửa cuối. Một rule semantic chỉ được auto khi canonical phrase đi qua planner và tất cả motion ID tồn tại trong `assets/vocabulary.json`/`assets/motions/manifest.json`. UI giữ câu bác sĩ nói và hiện các từ đệm đã bỏ để bác sĩ đối chiếu.

## LLM nên đứng ở đâu

LLM có ích nhất ở vai trò candidate planner/reranker, không phải bộ sinh ký hiệu. Output bắt buộc có dạng tương tự:

```json
{
  "intent": "measure_temperature",
  "clauses": [
    {
      "gloss_ids": ["368", "qipedc-W01298", "qipedc-W01227"],
      "source_tokens": ["y tá", "kiểm tra thân nhiệt"],
      "omitted_fillers": ["ơi", "giúp em", "nhé"],
      "confidence": 0.98
    }
  ],
  "unsupported_tokens": [],
  "requires_review": false
}
```

Runtime phải kiểm tra JSON schema, allowlist, token coverage và các từ cấm trước khi gọi avatar. Nếu model trả một ID lạ, thiếu token có nghĩa, hoặc confidence thấp, kết quả chuyển sang review. Trên máy i7-10750H/16 GB/GTX 1650 Ti 4 GB, mô hình local lượng tử nhỏ hoặc một adapter tuỳ chọn là hướng thực tế; bản portable không nên phụ thuộc cloud để hội thoại cơ bản vẫn chạy khi mất mạng. Seed hiện tại chạy offline và là fallback bắt buộc của adapter LLM.

## Bank QIPEDC và keypoint

QIPEDC công bố từ điển khoảng 4.000 ký hiệu kèm video/diễn giải, được thu từ người điếc ở ba miền và dùng cho tra cứu, dạy học và hỗ trợ giao tiếp ([trang từ điển QIPEDC](https://qipedc.moet.gov.vn/slang2)). Đây là nguồn tốt để mở rộng coverage, nhưng một video từ điển đơn lẻ không tự tạo ra chuyển tiếp tự nhiên giữa các từ trong một câu.

Bank được chia ba tầng:

| Tầng | Nội dung | Được phát runtime? |
| --- | --- | --- |
| A | 50–100 từ/cụm y tế, nhiều signer, keypoint đủ tay và thân, đã duyệt ngôn ngữ | Có |
| B | 400–1.000 candidate keypoint, có hash/mask/chất lượng, chờ review | Không mặc định |
| C | Metadata/video QIPEDC và record chưa xử lý | Không |

`tools/build_qipedc_dictionary_index.py` tạo `research/qipedc-dictionary-index.json` từ export chính thức 4.362 entry. Index này chỉ lưu metadata, URL và hash của export; không tải/copy video, không gán `model_id` và không tự đưa từ vào runtime.

`tools/build_qipedc_bank.py` hiện chỉ xử lý kho **All_cam1** (4.152 clip, 402 nhãn) để tạo candidate keypoint. Tên tool được giữ để tương thích quy trình cũ, nhưng schema và output mới là `clinic-allcam1-keypoint-bank-v2` ở `research/allcam1-bank/`. Đây là dữ liệu phục vụ recognizer/candidate motion, không phải bản sao của từ điển QIPEDC. Khi truyền `--labels` hoặc `--limit --extract`, tool mới xử lý từng video theo batch có thể tiếp tục; raw MP4 không bị sửa.

Mỗi NPZ compact giữ:

- 75 điểm pose + hai bàn tay, thời gian và profile extractor;
- `source_sha256`, nhãn, signer và trạng thái review;
- `observed` tách khỏi `imputed`;
- patch nội suy tuyến tính chỉ cho khe ngắn nội bộ (mặc định tối đa 2 frame), không vá qua đoạn mất dài;
- `float16`/nén để giảm kích thước, trong khi video gốc vẫn được giữ nguyên.

Khi dựng motion tổng hợp, tiếp tục dùng một đường DTW chung cho các khớp, trung bình palm-local và giới hạn xương. Không trung bình từng ngón theo frame độc lập vì cách đó tạo bàn tay xoắn và chuyển động rời mảnh. Với câu dài, cần thêm phrase bank hoặc dữ liệu continuous signing; nối các video từ điển đơn lẻ chỉ là fallback kỹ thuật.

Các hướng nghiên cứu phù hợp là text → gloss → pose → video với lemmatizer/reorder có kiểm soát ([ACL 2023](https://aclanthology.org/2023.at4ssl-1.3/)), retrieval và ngôn ngữ pretrained trong production challenge ([SLRTP 2025](https://openaccess.thecvf.com/content/CVPR2025W/SLRTP/html/Walsh_SLRTP2025_Sign_Language_Production_Challenge_Methodology_Results_and_Future_Work_CVPRW_2025_paper.html)), và segmentation/alignment để tìm cụm trong kho video ([Oxford SEA](https://robots.ox.ac.uk/~vgg/research/SEA/)). Nghiên cứu pseudo-gloss với prompt LLM là nguồn ý tưởng cho candidate extraction, không phải bằng chứng rằng LLM đã dịch đúng VSL ([Google Research, NeurIPS 2025](https://research.google/pubs/bridging-sign-and-spoken-languages-pseudo-glossgeneration-for-sign-language-translation/)).

## Phản chiếu luồng bệnh nhân → bác sĩ

Luồng này không nên dùng LLM để đoán từ đang thiếu. Thiết kế giữ hai lớp:

1. **Ký hiệu nhận được:** mỗi từ top-1 xuất hiện ngay, kèm score/n-best và dấu `?` nếu không chắc.
2. **Câu diễn đạt:** sau khoảng nghỉ 1,5 giây, một bộ quy tắc/semantic assembler có thể đổi các chuỗi đã quan sát thành tiếng Việt quen thuộc, ví dụ `Cơm · Ăn` → `Ăn cơm.` hoặc `Bụng · Đau` → `Đau bụng.`.

Câu gốc `raw_text` luôn còn trong lịch sử. Khi thêm LLM sau này, model chỉ được phép sắp xếp hoặc thêm từ nối được chứng minh từ các gloss đã quan sát; nó không được thêm `nhiều`, `không`, `thuốc`, vị trí đau hay chẩn đoán. Nếu có hai cách đọc, UI hiện các lựa chọn để bác sĩ hỏi lại người bệnh.

Như vậy:

- streaming vẫn gửi từng từ ngay;
- pause chỉ đóng lượt, không làm chậm nhận từ;
- ngữ cảnh được dùng sau lượt để hỗ trợ đọc câu, không được dùng để ghi đè top-1;
- mất track hoặc n-best thấp vẫn tạo cảnh báo, không tạo câu y khoa tưởng tượng.

## Việc cần làm tiếp theo

1. Dùng inventory QIPEDC để chọn pilot 50–100 từ y tế có ít nhất ba signer.
2. Chạy extractor theo batch, review `observed_fraction`/`imputed_fraction`, loại video có tay mất nhiều hoặc cửa sổ sai.
3. Tạo phrase bank cho các câu demo thật, ưu tiên continuous/teaching clips hoặc annotation thủ công; không suy ra ngữ pháp từ video từ đơn lẻ.
4. Chốt bảng alias theo signer điếc: mỗi alias có `canonical_gloss_id`, nguồn, confidence và `review_state`; không fuzzy-merge nhãn khác nhau.
5. Đo ba cấu hình trên cùng kịch bản y tế: deterministic, retrieval-only và LLM-assisted. Báo coverage, tỷ lệ bỏ sai từ bắt buộc, thời gian từ ASR đến avatar và số lượt cần bác sĩ duyệt.

### Giới hạn hiện tại

Seed semantic mới có một số mẫu an toàn quanh nhiệt độ, nước và nghỉ; nó chưa phải bản dịch tự do 400 từ. `Tôi ăn cơm` cố ý nằm ở review để chờ người dùng/người điếc chốt cách diễn đạt. Bank lớn chưa được chạy hàng nghìn video trong lượt này; tool đã có inventory/resume/patch để làm theo pilot và giữ provenance. Cần review của người sử dụng VSL trước khi gọi chuyển động là tự nhiên hoặc đưa record vào bản demo chính thức.
