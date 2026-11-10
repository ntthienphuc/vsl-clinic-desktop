"""Keep observed multimodal lead-in without postponing the word decision."""
from dataclasses import replace

from server.segmentation import BoundaryConfig, ElbowBoundaries, extend_observed_context


def make_gate(manifest):
    config = BoundaryConfig()
    if manifest.get("profile") == "slgcn-avhubert":
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
