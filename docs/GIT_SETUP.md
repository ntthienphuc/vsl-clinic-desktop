# Source checkout và dữ liệu cục bộ

VSL Clinic desktop dùng Electron, React/TypeScript, Three.js/VRM và backend Python/FastAPI. Đây là repo độc lập, không kèm mã Android/Flutter hoặc lịch sử Git của dự án Translator.

## Clone repo riêng

Repo `ntthienphuc/vsl-clinic-desktop` hiện để private. Dùng tài khoản GitHub có quyền truy cập:

```powershell
gh repo clone ntthienphuc/vsl-clinic-desktop
cd vsl-clinic-desktop
```

`package.json`, `src/`, `backend/`, `desktop/`, `assets/` và `tools/` nằm ngay thư mục gốc. Không cần checkout dự án Android để chạy app.

Git chứa mã nguồn, lockfile, test, cấu hình build, bank chuyển động, avatar được cấp phép, kịch bản và bằng chứng kiểm thử dạng JSON. Các video dữ liệu, trọng số nhận dạng/ASR, cache, môi trường Python/Node và EXE không nằm trong Git. `local-assets-manifest.json` lưu đường dẫn tương đối, dung lượng và SHA-256 của những đầu vào cần giữ riêng để chạy lại đúng demo. Đây không phải bản sao lưu đầy đủ dữ liệu huấn luyện hoặc toàn bộ thư mục nghiên cứu.

## Khôi phục trên máy đang có bộ dữ liệu được phép sử dụng

Chạy từ thư mục `vsl-clinic-desktop` của checkout mới:

```powershell
py -3.11 tools/restore_local_assets.py --from "D:\ban-sao-day-du\vsl-clinic-desktop"
./tools/setup.ps1
npm start
```

Thay đường dẫn mẫu bằng thư mục Clinic đầy đủ hiện có. Công cụ chỉ chép các file được liệt kê trong manifest, kiểm tra hash trước/sau và từ chối ghi đè file đã khác. Không tự tải dữ liệu hoặc suy ra quyền phân phối từ việc có URL nguồn. Nếu thiếu file, giữ nguyên các đầu vào đang có và báo danh sách cần bổ sung.

Có thể kiểm tra lại đầu vào mà không chép gì:

```powershell
py -3.11 tools/restore_local_assets.py
```

Sau khi khôi phục đủ, chạy `.venv/Scripts/python.exe -m pytest -q`, `npm test` và `npm run build`. Bản portable đã đóng gói trên máy dùng được độc lập với checkout; hướng dẫn nằm trong `docs/DEMO_0.3.4.md`. Giữ nguyên cả thư mục portable khi sao chép EXE.

Các script nghiên cứu/tạo lại bank như `prepare_assets.py`, `expand_vocabulary.py`, `build_qipedc_bank.py` và `research_qipedc.py` vẫn có đường dẫn mặc định tới corpus của dự án gốc. Chúng là công cụ xây dựng dữ liệu riêng, không thuộc luồng setup hoặc chạy app. Muốn tạo lại bank từ đầu cần cung cấp corpus gốc phù hợp; bản bank đã kiểm thử nằm sẵn trong repo.

Provenance của mã nhận dạng kế thừa được kiểm tra bằng hash cố định tại `backend/legacy/provenance.json`. Test không phụ thuộc vào việc checkout cha đang ở phiên bản Android/server nào. Video QIPEDC để kiểm tra nguồn được đọc từ `assets/reference-source/qipedc` sau khi khôi phục, thay vì đường dẫn tuyệt đối của máy đã tạo bank.
