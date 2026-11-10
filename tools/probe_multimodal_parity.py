"""Small paired test: identical saved camera bytes/times/selected intervals.

Original Processor writes only the explicitly named QA fixture directory.
Clinic MemoryProcessor writes nothing. No training or checkpoint selection.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/parity"
FIXTURE = Path(r"E:\\Project\VSL Projects\vsl-translator-multimodal-v2\sessions\52a61c5f2579456593a97d4aa8d94ae3")
STREAM = FIXTURE / "streams/continuous_1794126988793226"


def main():
    import cv2
    import numpy as np
    from multimodal.runtime import load_contract, sha256
    Engine, deployment = load_contract(ROOT / "assets/multimodal100")
    from multimodal.preprocessing import MemoryProcessor
    from server.preprocess import Processor
    from server.segmentation import ElbowBoundaries, extend_observed_context

    OUT.mkdir(parents=True, exist_ok=True)
    report = dict(scope="Three prespecified first live-build16 intervals; paired technical parity, not new signer accuracy.",
                  contract=deployment["contract"], checks={}, segments=[], errors=[])
    reference = Processor(OUT / "reference/frames")
    candidate = MemoryProcessor(ROOT / "assets/multimodal100")
    original_gate, new_gate = ElbowBoundaries(), ElbowBoundaries()
    boundaries = [json.loads(p.read_text("utf8")) for p in sorted((FIXTURE / "trials").glob("*/boundary.json"))[:3]]
    metadata = [json.loads(line) for line in (STREAM / "frames.jsonl").read_text("utf8").splitlines()]
    metadata = [m for m in metadata if m["capture_ms"] <= boundaries[-1]["decision_capture_ms"]]
    inputs = hashlib.sha256()
    engine = None
    original_boundaries, candidate_boundaries = [], []
    try:
        assert len(metadata) < 300
        for m in metadata:
            encoded = (STREAM / "frames" / f'{m["frame_id"]:06d}.jpg').read_bytes()
            inputs.update(encoded)
            bgr = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
            reference.append(encoded, m["frame_id"], m["capture_ms"])
            frame = candidate.append(bgr, m["frame_id"], m["capture_ms"])
            assert np.array_equal(reference.poses[-1], frame.pose), f'pose {m["frame_id"]}'
            assert np.array_equal(reference.gray[-1], frame.gray)
            if reference.points[-1] is None:
                assert frame.points is None
            else:
                assert np.array_equal(reference.points[-1], frame.points)
            a = original_gate.feed(reference.poses[-1], m["capture_ms"], m["frame_id"])
            b = new_gate.feed(frame.pose, m["capture_ms"], m["frame_id"])
            assert a == b
            if a:
                original_boundaries.append(extend_observed_context(a, reference.meta))
                candidate_boundaries.append(extend_observed_context(b, [f.meta() for f in candidate.frames]))
        report["checks"]["all_observed_pose_face_gray_frames_exact"] = True
        report["checks"]["boundary_and_shared_context_exact"] = original_boundaries == candidate_boundaries
        report["observed_frames"] = len(metadata)
        report["preprocess_timing_ms"] = dict(original_mean=float(np.mean([m["preprocess_ms"] for m in reference.meta])),
            clinic_mean=float(np.mean([f.preprocess_ms for f in candidate.frames])),
            clinic_face_mean=float(np.mean([f.face_ms for f in candidate.frames])),
            clinic_pose_hands_mean=float(np.mean([f.pose_hands_ms for f in candidate.frames])))
        report["input_bytes_sha256"] = inputs.hexdigest()
        report["metadata_sha256"] = sha256(STREAM / "frames.jsonl")
        engine = Engine()
        report["device"] = engine.device
        for n, boundary in enumerate(boundaries):
            indices = [i for i, m in enumerate(reference.meta) if m["frame_id"] in set(boundary["selected_frame_ids"])]
            frozen = Processor.__new__(Processor)
            frozen.directory = OUT / f"reference/segment{n + 1}/frames"
            frozen.directory.mkdir(parents=True, exist_ok=True)
            for field in ["poses", "points", "paths", "meta", "gray"]:
                setattr(frozen, field, [getattr(reference, field)[i] for i in indices])
            frozen.elapsed_ms = sum(m["preprocess_ms"] for m in frozen.meta)
            a_pose, a_mouth, a_info = frozen.finish()
            b_pose, b_mouth, b_info = candidate.snapshot(boundary["selected_frame_ids"]).finish()
            assert np.array_equal(a_pose, b_pose)
            assert np.array_equal(a_mouth, b_mouth)
            assert a_info["frame_ids"] == b_info["frame_ids"]
            a_sign, a_lip, _ = engine.features(a_pose, a_mouth)
            b_sign, b_lip, timing = engine.features(b_pose, b_mouth)
            row = dict(segment=n + 1, sampled_frames=len(a_pose), tensor_max_abs=0,
                       sign_feature_max_abs=float(np.max(np.abs(a_sign - b_sign))),
                       lip_feature_max_abs=float(np.max(np.abs(a_lip - b_lip))),
                       timing=timing, heads={})
            for mode in ["sign_only", "mouth_only", "fusion"]:
                a = engine.predict(a_sign, a_lip, mode)
                b = engine.predict(b_sign, b_lip, mode)
                difference = float(np.max(np.abs(np.array(a["logits"]) - np.array(b["logits"]))))
                row["heads"][mode] = dict(max_logit_abs=difference, top1=b["top_k"][0])
                assert difference <= 1e-6
            report["segments"].append(row)
        report["checks"]["same_frames_timestamp_resampling_pixels_features_logits"] = True
        report["passed"] = all(report["checks"].values())
    except Exception as exc:
        report["errors"].append(repr(exc))
        report["passed"] = False
        raise
    finally:
        reference.close()
        candidate.close()
        if engine:
            engine.close()
        (OUT / "PARITY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
