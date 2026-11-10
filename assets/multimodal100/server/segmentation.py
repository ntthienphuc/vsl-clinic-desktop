"""V1 elbow/raised-wrist state machine, adapted to continuous V2 frame IDs."""
from dataclasses import asdict, dataclass
from types import SimpleNamespace
import numpy as np
from .vendor.legacy_arm_utils import Arm, is_arm_active, ok_to_get_frame

@dataclass(frozen=True)
class BoundaryConfig:
    version: str = 'elbow140_up4_down4_300ms_context250_v3'
    use_raised_wrist_fallback: bool = False
    angle_threshold: int = 140
    visibility: float = .5
    min_num_up_frames: int = 4
    min_num_down_frames: int = 4
    min_down_time_ms: int = 300
    delay_ms: int = 400
    min_segment_frames: int = 6
    max_segment_ms: int = 8000
    max_candidate_frames: int = 10
    context_before_ms: int = 250
    context_after_ms: int = 250


def extend_observed_context(boundary, frame_meta):
    """Keep short shared context already available at the gate decision.

    Margin chosen on 20 validation clips, never from the test predictions.
    The sign core and the endpoint decision remain auditable separately.
    """
    value = dict(boundary)
    config = value['boundary_config']
    low = value['start_capture_ms'] - config.get('context_before_ms', 0)
    high = min(value['decision_capture_ms'], value['end_capture_ms'] + config.get('context_after_ms', 0))
    chosen = [m for m in frame_meta if low <= m['capture_ms'] <= high]
    if not chosen:
        return value
    value.update(core_start_capture_ms=value['start_capture_ms'],
                 core_end_capture_ms=value['end_capture_ms'],
                 core_frame_ids=value['selected_frame_ids'],
                 start_capture_ms=chosen[0]['capture_ms'],
                 end_capture_ms=chosen[-1]['capture_ms'],
                 selected_frame_ids=[m['frame_id'] for m in chosen],
                 trim='V1 active core plus shared observed 250-ms context on either side; capped at decision')
    return value

class ElbowBoundaries:
    def __init__(self, config=None):
        self.config=config or BoundaryConfig()
        self.left=Arm('left',self.config.visibility)
        self.right=Arm('right',self.config.visibility)
        self.previous=None
        self.buffer=[]
        self.candidate=[]
        self.state='listening'
        self.diagnostics={}
        self.cooldown=False

    def feed(self,pose,timestamp,frame_id=None):
        if not np.isfinite(timestamp) or (self.previous is not None and timestamp<=self.previous):
            raise ValueError('non_monotonic_boundary_clock')
        self.previous=timestamp
        c=self.config
        points=[SimpleNamespace(x=float(v[0]),y=float(v[1]),visibility=float(v[3])) for v in pose[:33]]
        self.left.set_pose(points)
        self.right.set_pose(points)
        visible=[bool((pose[33:54,3]>0).any()),bool((pose[54:75,3]>0).any())]
        # A visible lowered hand can remain above an estimated/cropped hip.
        # Keep the legacy fallback opt-in; the live default uses elbow flexion.
        gate_visible=[h and c.use_raised_wrist_fallback for h in visible]
        raw=[bool(is_arm_active(a,c.angle_threshold,h)) for a,h in zip([self.left,self.right],gate_visible)]
        self.diagnostics=dict(left_angle=float(self.left.angle),right_angle=float(self.right.angle),
                              left_active=raw[0],right_active=raw[1],left_hand_visible=visible[0],right_hand_visible=visible[1])
        up=[ok_to_get_frame(a,c.angle_threshold,c.min_num_up_frames,c.min_num_down_frames,
             timestamp,c.delay_ms,c.min_down_time_ms,h) for a,h in zip([self.left,self.right],gate_visible)]
        pending=self.left.num_up_frames>0 or self.right.num_up_frames>0
        item=dict(capture_ms=timestamp,frame_id=frame_id,active=any(raw))
        if self.cooldown:
            self.state='return_to_neutral'
            if not any(up) and not pending:
                self.cooldown=False
                self.left.reset_state();self.right.reset_state()
                self.state='listening'
            return None
        if any(up):
            if not self.buffer and self.candidate:
                self.buffer.extend(self.candidate);self.candidate=[]
            self.buffer.append(item)
            self.state='signing' if any(raw) else 'waiting_for_boundary'
            if timestamp-self.buffer[0]['capture_ms']>c.max_segment_ms:
                result=self._end(timestamp,'gesture_duration_limit')
                self.cooldown=True
                return result
        elif pending:
            self.candidate.append(item)
            self.candidate=self.candidate[-c.max_candidate_frames:]
            self.state='priming'
        elif self.buffer:
            return self._end(timestamp,'arms_returned_to_neutral')
        else:
            self.candidate=[]
            self.state='listening'
        return None

    def _end(self,decision,reason):
        original=self.buffer
        active=[i for i,m in enumerate(original) if m['active']]
        start=max(0,active[0]-1) if active else 0
        end=min(len(original),active[-1]+2) if active else len(original)
        selected=original[start:end]
        value=dict(start_capture_ms=selected[0]['capture_ms'],end_capture_ms=selected[-1]['capture_ms'],
            first_active_capture_ms=original[active[0]]['capture_ms'] if active else None,
            last_active_capture_ms=original[active[-1]]['capture_ms'] if active else None,
            decision_capture_ms=decision,reason=reason,buffered_frame_count=len(original),
            selected_frame_ids=[m['frame_id'] for m in selected],
            boundary_config=asdict(self.config),
            boundary_source=('V1 elbow-or-visible-raised-wrist' if self.config.use_raised_wrist_fallback else 'Elbow flexion only')+'; shared sign-guided boundaries for every mode',
            trim='V1 SPOTER active core plus one context frame on each side')
        if len(original)<self.config.min_segment_frames:
            value['reason']='insufficient_segment_frames'
        self.buffer=[];self.candidate=[]
        self.left.reset_state();self.right.reset_state()
        self.state='listening'
        return value

    def flush(self):
        if not self.buffer:return None
        return self._end(self.previous,'operator_stop')
