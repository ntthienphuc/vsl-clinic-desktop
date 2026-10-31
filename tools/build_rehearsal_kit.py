"""Two reproducible rehearsals; retain originals and keep expected labels out of inference."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sys
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.text_to_sign import TextPlanner


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def composite(paths, output):
    # Explicit holds expose word boundaries to the isolated-word model.
    # This is a transport rehearsal, never presented as natural sentence footage.
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot write {output}")
    count = 0
    for path in paths:
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = []
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            scale = min(640 / w, 480 / h)
            fitted = cv2.resize(frame, (round(w * scale), round(h * scale)))
            canvas = np.zeros((480, 640, 3), dtype=np.uint8)
            y, x = (480 - fitted.shape[0]) // 2, (640 - fitted.shape[1]) // 2
            canvas[y:y + fitted.shape[0], x:x + fitted.shape[1]] = fitted
            frames.append(canvas)
        cap.release()
        if len(frames) < 6 or fps <= 0:
            raise ValueError(f"Invalid source video {path}")
        for index in range(round(len(frames) * 30 / fps)):
            writer.write(frames[min(len(frames) - 1, round(index * fps / 30))])
            count += 1
        for _ in range(24):
            writer.write(frames[-1])
            count += 1
    for _ in range(60):
        writer.write(frames[-1])
        count += 1
    writer.release()
    cap = cv2.VideoCapture(str(output))
    decoded = 0
    while cap.read()[0]:
        decoded += 1
    cap.release()
    assert decoded == count
    return {"sha256": sha(output), "frames": count, "duration_ms": round(count / 30 * 1000)}


def main():
    catalog = read(ROOT / "demo/scenarios-v0.3.4.json")
    planner = TextPlanner(read(ROOT / "assets/vocabulary.json"), read(ROOT / "assets/phrases.json"), read(ROOT / "assets/semantic_bank.json"))
    sources = {str(w["model_id"]): w for w in read(ROOT / "research/source-manifest.json")["words"]}
    with (ROOT / "assets/gloss.csv").open(encoding="utf-8", newline="") as f:
        labels = dict(csv.reader(f))
    assert len(labels) == 400
    destination = ROOT / "demo/HAI_KICH_BAN_2026-10-31"
    destination.mkdir(exist_ok=True)
    for scenario in catalog["scenarios"]:
        folder = destination / scenario["id"]
        folder.mkdir(exist_ok=True)
        lines = [f"# {scenario['title']}", "", "Mỗi dòng là một lượt. Đợi avatar hoàn tất rồi bệnh nhân mới trả lời.", "", "| Lượt | Bác sĩ nói / nhập đúng câu | Avatar | Bệnh nhân ký theo thứ tự | Video tập |", "|---|---|---|---|---|"]
        for index, step in enumerate(scenario["steps"], 1):
            plan = planner.plan(step["doctor"])
            assert plan["supported"], (step["doctor"], plan)
            step["doctor_projection"] = plan["projection"]
            step["doctor_gloss_ids"] = [w["id"] for w in plan["glosses"]]
            step["patient_labels"] = [labels[str(i)] for i in step["patient_ids"]]
            target = folder / f"{index:02d}_Tra_loi"
            target.mkdir(exist_ok=True)
            clips = []
            for number, identity in enumerate(step["patient_ids"], 1):
                source = ROOT / f"assets/samples/{identity:03d}.mp4"
                original = sources[str(identity)]["demo_source"]
                assert original["gloss"] == labels[str(identity)]
                assert sha(source) == original["sha256"]
                output = target / f"{number}.mp4"
                if output.exists():
                    assert sha(output) == sha(source), f"Preserve modified file {output}"
                else:
                    shutil.copy2(source, output)
                clips.append({"file": output.relative_to(destination).as_posix(), "model_id": identity,
                              "label": labels[str(identity)], "source_video_id": original["video_id"], "sha256": sha(output)})
            step["clips"] = clips
            combined = target / "CAU_TRA_LOI.mp4"
            step["replay"] = {"file": combined.relative_to(destination).as_posix(), **composite([destination / c["file"] for c in clips], combined)}
            instruction = [f"# Lượt {index}", "", f"Bác sĩ: **{step['doctor']}**", "", f"Avatar: {' → '.join(step['doctor_projection'])}", "", "Bệnh nhân tập theo đúng thứ tự:", ""]
            instruction += [f"{n}. [{n}.mp4]({n}.mp4) — **{c['label']}**, model ID {c['model_id']}." for n, c in enumerate(clips, 1)]
            instruction += ["", "Hạ/giữ tay 0,7–1 giây giữa các từ; nghỉ khoảng 1,5 giây sau từ cuối. Thấy rõ mặt, vai, khuỷu tay và hai bàn tay.", "", "CAU_TRA_LOI.mp4 là clip ghép có nhịp nghỉ nhân tạo, để mở qua Camera / video → Mở video trên máy. Các file số là video gốc để học; không coi clip ghép là câu ký tự nhiên."]
            (target / "HUONG_DAN.md").write_text("\n".join(instruction) + "\n", encoding="utf-8")
            lines.append(f"| {index} | {step['doctor']} | {' → '.join(step['doctor_projection'])} | {' → '.join(step['patient_labels'])} | [{index:02d}_Tra_loi]({index:02d}_Tra_loi/HUONG_DAN.md) |")
        lines += ["", "**Cách trình diễn:** Bác sĩ có thể nhập nguyên văn câu trên. Nếu thử giọng nói, đọc từng câu rồi ngừng; kiểm tra chữ nhận được. Tự động chỉ phát câu đủ ký hiệu; câu ngoài bank cần nói lại. Không đọc cả bảng thành một câu.", "", "**Nếu chưa có webcam:** Mở lần lượt CAU_TRA_LOI.mp4 ở từng lượt qua Camera / video → Mở video trên máy. Hệ thống thực sự chạy detector và model trên video, không gán sẵn đáp án.", "", "**Nếu nhận sai người diễn:** mở Đối chiếu từ vừa nhận, xác nhận/sửa hoặc dùng video dự phòng. Kết quả video không bảo đảm người ký mới luôn được nhận đúng."]
        (folder / "KICH_BAN.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    catalog["video_note"] = "Composite clips append 800 ms holds per word and a 2 s final hold; source videos and hashes retained. Not a natural continuous signing benchmark."
    (destination / "manifest.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"folder": str(destination), "scenarios": len(catalog["scenarios"]), "turns": sum(len(s["steps"]) for s in catalog["scenarios"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
