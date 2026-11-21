"""Clinic commit policy, separate from the unchanged closed-set model.

Scores remain uncalibrated. This policy is NOT an out-of-vocabulary or trained
non-sign detector. Its version and reasons travel with every result.
"""
POLICY = "clinic-fusion-quality-v5"
MIN_SCORE = .70  # Owner-requested 0.75 -> 0.70; softmax is not calibrated accuracy.
MIN_MARGIN = .15  # Previously .20. Modality/sampling guards remain enforced.


def decide(result, info, boundary, *, require_continuity=False):
    reasons = []
    if result.get("status") != "ok":
        return dict(version=POLICY, committed=False, disposition="unavailable",
                    reasons=[result.get("reason", "model_unavailable")],
                    prompt="Chưa thấy rõ mặt và tay. Bạn có thể ký lại hoặc nhập chữ.")
    if boundary.get("reason") != "arms_returned_to_neutral":
        reasons.append("incomplete_word_boundary")
    if not info.get("sign_valid") or not info.get("mouth_valid"):
        reasons.append("fusion_requires_both")
    if info.get("hand_coverage", 0) < .6:
        reasons.append("insufficient_hand_observation")
    if info.get("single_face_fraction", 0) < .6:
        reasons.append("insufficient_single_face_observation")
    if info.get("input_fps", 0) < 10 or info.get("max_capture_gap_ms", 1e9) > 300:
        reasons.append("insufficient_temporal_sampling")
    top = result["top_k"]
    if require_continuity and info.get("sampling_complete") is not True:
        reasons.append("interrupted_temporal_sampling")
    if require_continuity and info.get("model_cadence_observed") is not True:
        reasons.append("insufficient_model_cadence")
    if top[0]["score"] < MIN_SCORE or top[0]["score"] - top[1]["score"] < MIN_MARGIN:
        reasons.append("ambiguous_closed_set_prediction")
    return dict(version=POLICY, committed=not reasons,
                disposition="review" if reasons else "committed", reasons=reasons,
                prompt="Chưa nhận chắc. Bạn ký lại hoặc nhờ bác sĩ đối chiếu." if reasons else "",
                scores="uncalibrated_softmax", thresholds=dict(score=MIN_SCORE, margin=MIN_MARGIN))


def recognition_event(result, info, boundary, mapping, model, segment_id, timing):
    policy = decide(result, info, boundary,
                    require_continuity=model["contract"].startswith("vsl100-r3-"))
    predictions = []
    for entry in result.get("top_k", []):
        label = mapping[entry["index"]]
        if entry["class_id"] != label["class_id"] or entry["gloss"] != label["original_gloss"]:
            raise ValueError("class_order_mismatch")
        predictions.append(dict(gloss=label["display_text"], score=entry["score"],
            model_id=None, class_id=label["class_id"], class_index=label["class_index"],
            original_gloss=label["original_gloss"], canonical_concept_id=label["canonical_concept_id"],
            legacy_label_candidate=label["legacy_label_candidate"], voice_key=label["voice_key"],
            engine_family="multimodal100"))
    return dict(type="recognition" if predictions else "recognition_unavailable",
        segment_id=segment_id, segment_number=int(segment_id.rsplit(":", 1)[-1]),
        request_id=segment_id, engine_family="multimodal100",
        contract=model["contract"], manifest_sha256=model["manifest_sha256"],
        checkpoint_sha256=model["fusion_sha256"], actual_mode="fusion", requested_mode="fusion",
        fallback_reason=None, predictions=predictions, policy=policy,
        quality_warning=policy["prompt"] or None, quality=info,
        boundary=boundary, timing=timing, inference_ms=timing.get("inference_wall_ms"),
        raw_logits=result.get("logits"))
