"""Keep observed multimodal lead-in without postponing the word decision."""
from dataclasses import replace

from server.segmentation import BoundaryConfig, ElbowBoundaries, extend_observed_context

MIN_ACTIVE_CORE_MS = 300


def insufficient_active_core(boundary):
    """Padding and the neutral endpoint wait are not evidence of a new sign.

    A four-frame elbow flick can otherwise become a >1s classifier input once
    shared context is added, producing an unrelated word from a return motion.
    Apply to the observed active span, before context; no label or score rule.
    """
    first = boundary.get("first_active_capture_ms")
    last = boundary.get("last_active_capture_ms")
    return first is None or last is None or last - first < MIN_ACTIVE_CORE_MS


def make_gate(manifest):
    config = BoundaryConfig()
    if manifest.get("profile") in {"slgcn-avhubert", "slgcn-autoavsr"}:
        config = replace(config, version="clinic-r3-elbow140-context500-400-v1",
                         context_before_ms=500, context_after_ms=400)
    return ElbowBoundaries(config)


def extend_context(boundary, metadata):
    value = extend_observed_context(boundary, metadata)
    config = value["boundary_config"]
    value["trim"] = (
        f'Active core plus observed {config["context_before_ms"]}-ms lead-in and '
        f'{config["context_after_ms"]}-ms tail; capped at unchanged boundary decision')
    return value
