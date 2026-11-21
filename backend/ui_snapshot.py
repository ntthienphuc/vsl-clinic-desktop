"""Copy conversation state without retransmitting model traces to both windows."""
from __future__ import annotations


def ui_copy(value):
    if isinstance(value, dict):
        return {key: ({name: item[name] for name in ('inference_ms', 'generation', 'segment_id', 'stream_id') if name in item}
                      if key == 'metrics' and isinstance(item, dict) else ui_copy(item))
                for key, item in value.items()}
    if isinstance(value, list):
        return [ui_copy(item) for item in value]
    return value
