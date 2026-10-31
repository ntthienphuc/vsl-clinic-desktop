"""Build a numbered patient practice kit from verified local 400-gloss videos."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.text_to_sign import TextPlanner


SCENES = [
    ("01_Dong_y_kham_benh", "Bắt đầu trao đổi", "Bác sĩ khám bệnh.", "Đồng ý.", [395]),
    ("02_Dau", "Hỏi triệu chứng", "Bạn có đau bụng không?", "Đau.", [379]),
    ("03_Met_Can_Nghi_ngoi", "Nêu nhu cầu nghỉ", "Bạn có mệt không?", "Mệt. Cần nghỉ ngơi.", [204, 87, 210]),
    ("04_Dong_y_do_nhiet_do", "Giải thích bước tiếp theo", "Y tá đo nhiệt độ.", "Đồng ý.", [395]),
    ("05_Can_Giup_do", "Đề nghị hỗ trợ", "Y tá giúp đỡ.", "Cần giúp đỡ.", [87, 116]),
    ("06_Can_Nuoc", "Nêu nhu cầu nước", "Ngồi nghỉ ngơi.", "Cần nước.", [87, 243]),
    ("07_Dong_y_Cam_on", "Xác nhận đã hiểu", "Uống nước.", "Đồng ý. Cảm ơn.", [395, 86]),
    ("08_Cam_on", "Kết thúc demo", "Cảm ơn.", "Cảm ơn.", [86]),
]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_video(path):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = capture.get(cv2.CAP_PROP_FPS)
    frames = 0
    size = None
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames += 1
        size = [frame.shape[1], frame.shape[0]]
    capture.release()
    if frames < 6 or frames != declared or fps <= 0:
        raise ValueError(f"Incomplete video decode: {path}, {frames}/{declared}")
    return {"frames": frames, "fps": fps, "resolution": size, "duration_ms": round(frames / fps * 1000)}


def main():
    destination = ROOT / "demo"
    destination.mkdir(exist_ok=True)
    with (ROOT / "assets/gloss.csv").open(encoding="utf-8", newline="") as handle:
        labels = {int(identity): label for identity, label in csv.reader(handle)}
    if set(labels) != set(range(400)):
        raise ValueError("Expected the unchanged 400-label model vocabulary")
    sources = read(ROOT / "research/source-manifest.json")
    words = {word["model_id"]: word for word in sources["words"]}
    vocabulary = read(ROOT / "assets/vocabulary.json")
    planner = TextPlanner(vocabulary, read(ROOT / "assets/phrases.json"))
    scenes = []
    for index, (folder, title, doctor, response, identities) in enumerate(SCENES, 1):
        plan = planner.plan(doctor)
        if not plan["supported"]:
            raise ValueError(f"Doctor sentence is not supported: {doctor}")
        target = destination / "benh_nhan" / folder
        target.mkdir(parents=True, exist_ok=True)
        clips = []
        for number, identity in enumerate(identities, 1):
            word = words[identity]
            source = word["demo_source"]
            if word["label"] != labels[identity] or source["gloss"] != labels[identity]:
                raise ValueError(f"Vocabulary lineage mismatch: {identity}")
            original = Path(source["path"])
            sample = ROOT / word["demo"].lstrip("/")
            checksum = source["sha256"]
            if digest(original) != checksum or digest(sample) != checksum:
                raise ValueError(f"Source video changed: {identity}")
            output = target / f"{number}.mp4"
            if output.exists() and digest(output) != checksum:
                raise FileExistsError(f"Keep existing changed practice video: {output}")
            if not output.exists():
                shutil.copy2(sample, output)
            decoded = decode_video(output)
            if digest(output) != checksum:
                raise ValueError(f"Copy mismatch: {output}")
            clips.append({"number": number, "file": output.relative_to(destination).as_posix(),
                          "label": labels[identity], "model_id": identity,
                          "source_video_id": source["video_id"], "declared_signer_id": source["signer_id"],
                          "original_path": str(original), "sha256": checksum, **decoded})
        expected_files = {f"{number}.mp4" for number in range(1, len(clips) + 1)}
        if {path.name for path in target.glob("*.mp4")} != expected_files:
            raise ValueError(f"Unexpected or missing practice clips in {target}")
        glosses = [item["label"] for item in plan["glosses"]]
        instructions = [f"# {index:02d}. {title}", "", f"**Bác sĩ nói hoặc nhập:** {doctor}", "",
                        f"**Avatar phát:** {' → '.join(glosses)}", "",
                        f"**Ý bệnh nhân muốn trả lời:** {response}", "",
                        "## Tập từng ký hiệu theo thứ tự", ""]
        for clip in clips:
            instructions.append(f"{clip['number']}. [{clip['number']}.mp4]({clip['number']}.mp4) — **{clip['label']}** (nhãn model {clip['model_id']}).")
        instructions.extend(["", "Xem hết video, tập đúng tay và hướng lòng bàn tay. Video không lật gương.", "",
                             "Khi thử camera: bác sĩ bấm Bắt đầu cuộc trao đổi; bệnh nhân chỉ cần làm ký hiệu. Giữ/hạ tay khoảng 0,7–1 giây giữa các từ; mỗi từ hiện ngay bên bác sĩ. Nghỉ khoảng 1,5 giây sau từ cuối để gom lượt. Cần thấy cả mặt, vai, khuỷu tay và hai bàn tay.", "",
                             "Mỗi nhãn là một đơn vị từ vựng: “Nghỉ ngơi”, “Giúp đỡ”, “Đồng ý” mỗi cụm chỉ có một video. Model nhận các từ riêng lẻ; phần gom lượt/diễn đạt không phải model dịch câu ký hiệu liên tục. Không cần chờ hết lượt mới thấy từ.", "",
                             "Chưa có webcam: ở UI bác sĩ mở Camera / video → Video mẫu, chọn nhãn rồi Bắt đầu. Lặp lại với từng nhãn trên. Bác sĩ đối chiếu top-1/n-best, sửa hoặc xác nhận theo video đã xem; không coi nhãn mẫu là kết quả model. Đổi nguồn/video sẽ kết thúc lượt hiện tại.", ""])
        (target / "HUONG_DAN.md").write_text("\n".join(instructions), encoding="utf-8")
        scenes.append({"step": index, "title": title, "folder": target.relative_to(destination).as_posix(),
                       "doctor_text": doctor, "doctor_glosses": glosses, "patient_meaning": response,
                       "patient_glosses": [item["label"] for item in clips], "clips": clips})
    manifest = {"schema": "clinic-demo-kit-v1", "created_at": datetime.now(timezone.utc).isoformat(),
                "scope": "Local practice kit; patient vocabulary is exactly a subset of the 400 model labels. Not a clinical protocol or continuous sentence recognition benchmark.",
                "vocabulary_sha256": digest(ROOT / "assets/gloss.csv"),
                "source_manifest_sha256": digest(ROOT / "research/source-manifest.json"),
                "source_metadata_sha256": sources["metadata_sha256"],
                "scenes": scenes, "validated_clips": sum(len(scene["clips"]) for scene in scenes),
                "validation": "Every original, runtime sample and copied MP4 has the declared SHA-256; every copied video decodes fully; numbered file set is exact; every doctor sentence is supported by the current planner."}
    (destination / "demo-script.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Kịch bản demo VSL Clinic — bác sĩ và bệnh nhân", "",
             "Demo giao tiếp khoảng 5–8 phút, trên một máy tính với hai cửa sổ. Các lời thoại dưới đây là tình huống diễn thử, không phải quy trình chẩn đoán/điều trị.", "",
             "## Chuẩn bị", "",
             "1. Đóng phiên Clinic cũ rồi mở bản 0.3.1: `release/desktop-v0.3.1/win-unpacked/VSL Clinic.exe` tính từ thư mục dự án. Để nguyên cả thư mục portable.",
             "2. Bác sĩ mở cửa sổ Bác sĩ; người diễn bệnh nhân mở cửa sổ Bệnh nhân. Khi có hai màn hình, đặt mỗi cửa sổ trên một màn hình.",
             "3. Học video trong `benh_nhan/` trước. Bác sĩ mở Camera / video để chọn nguồn. Chưa có webcam: chọn Video mẫu và một nhãn. Chọn câu / từ mở danh sách 65 từ và 58 mẫu câu.",
             "4. Bác sĩ chọn Tự động hoặc Xác nhận trước khi gửi, rồi Bắt đầu cuộc trao đổi. Camera theo dõi liên tục, micro bác sĩ mở nếu có thiết bị/quyền. Tự động: nói câu có sẵn rồi ngắt khoảng nửa giây, app gửi ngay khi nhận xong. Manual: đọc/sửa câu rồi Gửi ký hiệu. Câu thiếu từ/mẫu câu có cảnh báo Nói lại; bấm để bỏ bản nháp đó và nói câu ngắn hơn. Gửi chữ chỉ khi bác sĩ chủ động chọn.",
             "5. Đợi avatar phát xong rồi bệnh nhân trả lời, không cần bấm nút. Giữ/hạ tay 0,7–1 giây giữa các từ; bác sĩ thấy từng từ ngay. Nghỉ khoảng 1,5 giây sau từ cuối để gom lượt vào lịch sử. Để thử từng MP4 khi chưa có webcam: bác sĩ chọn video và Bắt đầu trong hộp Camera / video.", "",
             "## Lời thoại và thứ tự tập", "",
             "| Lượt | Bác sĩ nói/nhập | Avatar theo thứ tự | Bệnh nhân thực hiện | Video học |",
             "|---|---|---|---|---|"]
    for scene in scenes:
        links = ", ".join(f"[{clip['number']}.mp4 = {clip['label']}]({clip['file']})" for clip in scene["clips"])
        lines.append(f"| {scene['step']} | {scene['doctor_text']} | {' → '.join(scene['doctor_glosses'])} | {' → '.join(scene['patient_glosses'])} | {links} |")
    lines.extend(["", "## Điểm cần thể hiện trong demo", "",
                  "- Lượt 3: bệnh nhân thực hiện **Mệt → Cần → Nghỉ ngơi**, khung Người bệnh đang nói hiện Mệt trước, rồi thêm Cần, rồi Nghỉ ngơi; không đợi hết lượt. Nghỉ lâu hơn thì gom thành một lượt trong Nội dung trao đổi. Thư mục có `1.mp4 = Mệt`, `2.mp4 = Cần`, `3.mp4 = Nghỉ ngơi`.",
                  "- Để xem phép thử hai từ đã chuẩn bị khi chưa có webcam: bác sĩ mở video `research/live-turn-379-204.mp4` từ mã nguồn. Đau phải hiện trước Mệt, cuối lượt có gợi ý Đau và mệt. Clip này ghép hai mẫu từ rời và thêm 800 ms nghỉ, không phải video câu ký tự nhiên; không nằm trong portable.",
                  "- Lượt 4: bác sĩ nói **Y tá đo nhiệt độ.** Avatar phát **Y tá → Nhiệt độ → Đo** trong một lượt, không cần bấm gửi từng từ.",
                  "- Muốn thử nhiều câu bác sĩ trong một lượt: nhập **Ngồi nghỉ ngơi. Uống nước.** Avatar lần lượt phát **Ngồi → Nghỉ ngơi**, ngắt câu ngắn, rồi **Nước → Uống**. Thử tạm dừng, tiếp tục, phát lại và tốc độ 0,75×.",
                  "- Thử ngoài phạm vi bằng **Không đau** hoặc **Uống 2 viên**: app phải giữ nguyên nội dung, không phát phần câu thiếu. Dùng Chỉ gửi chữ nếu muốn chuyển nguyên văn cho bệnh nhân.", "",
                  "## Phạm vi cần hiểu đúng", "",
                  "- Tất cả video bệnh nhân lấy từ dữ liệu local có nhãn đúng trong **400 lớp**; không có từ QIPEDC ngoài model trong thư mục này.",
                  "- Số video theo nhãn ký hiệu, không theo số tiếng Việt. “Nghỉ ngơi” là một nhãn, nên một video.",
                  "- Ví dụ “Tôi ăn cơm” chưa dùng cho phía bệnh nhân vì nhãn Tôi/Cơm không nằm trong bộ 400 hiện tại. Không thay bằng từ gần nghĩa rồi báo là model đã nhận câu.",
                  "- Ở phía bác sĩ, bank mở rộng có một số từ từ QIPEDC như Bụng, Nhiệt độ, Đo. Đây là chuyển động tham chiếu cho avatar; không làm tăng số lớp nhận dạng bệnh nhân.",
                  "- Câu hỏi về bụng chỉ được trả lời bằng ký hiệu **Đau** trong kịch bản này; hệ thống không tự thêm vị trí bụng vào kết quả model. Bác sĩ đọc cùng ngữ cảnh câu vừa hỏi.",
                  "- Thứ tự ký hiệu là mẫu câu demo đã khai báo. Người ký VSL cần thẩm định nghĩa, nét mặt và độ tự nhiên trước khi dùng cho giao tiếp y tế thực tế.",
                  "- Video là mẫu để học, không bảo đảm model luôn nhận đúng người diễn. Nếu sai: đối chiếu video, xem n-best và sửa/xác nhận; đừng giấu lỗi nhận dạng trong demo.", "",
                  "## Nguồn và kiểm tra file", "",
                  "`demo-script.json` lưu từng nhãn, model ID, video ID gốc, đường dẫn, SHA-256, số frame, fps và thứ tự. Script `tools/build_demo_kit.py` kiểm tra toàn bộ video, nhãn và câu bác sĩ khi tạo bộ này. Giữ video local để tập/demo; không tự công bố dữ liệu của người ký.", ""])
    (destination / "KICH_BAN_DEMO.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"folder": str(destination), "scenes": len(scenes), "clips": manifest["validated_clips"],
                      "patient_model_ids": sorted({clip["model_id"] for scene in scenes for clip in scene["clips"]})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
