import numpy as np
try:
    from mediapipe.python.solutions import pose
except ImportError:  # Android already supplies landmark ordering in edge mode.
    pose = None


POSE_INDEXES = {
    "left_shoulder": 11,
    "left_elbow": 13,
    "left_wrist": 15,
    "left_hip": 23,
    "right_shoulder": 12,
    "right_elbow": 14,
    "right_wrist": 16,
    "right_hip": 24,
}


def calculate_angle(a: tuple, b: tuple, c: tuple) -> float:
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = (
        np.arctan2(c[1] - b[1], c[0] - b[0])
        - np.arctan2(a[1] - b[1], a[0] - b[0])
    )
    angle = abs(radians * 180.0 / np.pi)
    if angle > 180:
        angle = 360 - angle
    return angle


class Arm:
    def __init__(self, side: str, visibility: float = 0.3) -> None:
        self.side = side
        if side == "left":
            self.shoulder_idx = pose.PoseLandmark.LEFT_SHOULDER.value if pose else POSE_INDEXES["left_shoulder"]
            self.elbow_idx = pose.PoseLandmark.LEFT_ELBOW.value if pose else POSE_INDEXES["left_elbow"]
            self.wrist_idx = pose.PoseLandmark.LEFT_WRIST.value if pose else POSE_INDEXES["left_wrist"]
            self.hip_idx = pose.PoseLandmark.LEFT_HIP.value if pose else POSE_INDEXES["left_hip"]
        elif side == "right":
            self.shoulder_idx = pose.PoseLandmark.RIGHT_SHOULDER.value if pose else POSE_INDEXES["right_shoulder"]
            self.elbow_idx = pose.PoseLandmark.RIGHT_ELBOW.value if pose else POSE_INDEXES["right_elbow"]
            self.wrist_idx = pose.PoseLandmark.RIGHT_WRIST.value if pose else POSE_INDEXES["right_wrist"]
            self.hip_idx = pose.PoseLandmark.RIGHT_HIP.value if pose else POSE_INDEXES["right_hip"]
        else:
            raise ValueError("Side must be either 'left' or 'right'.")

        # Backward compatibility for old diagnostics code.
        self.shoulde_idx = self.shoulder_idx

        self.visibility = visibility
        self.reset_state()

    def reset_state(self) -> None:
        self.is_up = False
        self.num_up_frames = 0
        self.num_down_frames = 0
        self.start_time = 0
        self.end_time = 0
        self.start_down_time = 0
        self.shoulder = None
        self.elbow = None
        self.wrist = None
        self.hip = None
        self.angle = 180.0

    def set_pose(self, landmarks) -> bool:
        if not landmarks:
            self._mark_missing()
            return False

        required_indexes = (self.shoulder_idx, self.elbow_idx, self.wrist_idx)
        if any(index >= len(landmarks) for index in required_indexes):
            self._mark_missing()
            return False

        shoulder_lm = landmarks[self.shoulder_idx]
        elbow_lm = landmarks[self.elbow_idx]
        wrist_lm = landmarks[self.wrist_idx]

        if (
            shoulder_lm.visibility < self.visibility
            or elbow_lm.visibility < self.visibility
            or wrist_lm.visibility < self.visibility
        ):
            self._mark_missing()
            return False

        self.shoulder = (shoulder_lm.x, shoulder_lm.y)
        self.elbow = (elbow_lm.x, elbow_lm.y)
        self.wrist = (wrist_lm.x, wrist_lm.y)
        self.angle = calculate_angle(self.shoulder, self.elbow, self.wrist)

        self.hip = None
        if self.hip_idx < len(landmarks):
            hip_lm = landmarks[self.hip_idx]
            self.hip = (hip_lm.x, hip_lm.y) if hip_lm.visibility >= self.visibility else None

        return True

    def _mark_missing(self) -> None:
        self.shoulder = None
        self.elbow = None
        self.wrist = None
        self.hip = None
        self.angle = 180.0

    def to_dict(self):
        return {
            "is_up": bool(self.is_up),
            "num_up_frames": int(self.num_up_frames),
            "num_down_frames": int(self.num_down_frames),
            "start_time": int(self.start_time),
            "end_time": int(self.end_time),
            "start_down_time": int(self.start_down_time),
            "shoulder": [float(x) for x in self.shoulder] if self.shoulder else None,
            "elbow": [float(x) for x in self.elbow] if self.elbow else None,
            "wrist": [float(x) for x in self.wrist] if self.wrist else None,
            "hip": [float(x) for x in self.hip] if self.hip else None,
            "angle": float(self.angle),
        }

    @classmethod
    def from_dict(cls, data, side, visibility):
        arm = cls(side, visibility)
        arm.is_up = data["is_up"]
        arm.num_up_frames = data["num_up_frames"]
        arm.num_down_frames = data["num_down_frames"]
        arm.start_time = data["start_time"]
        arm.end_time = data["end_time"]
        arm.start_down_time = data.get("start_down_time", 0)
        arm.shoulder = tuple(data["shoulder"]) if data["shoulder"] else None
        arm.elbow = tuple(data["elbow"]) if data["elbow"] else None
        arm.wrist = tuple(data["wrist"]) if data["wrist"] else None
        arm.hip = tuple(data.get("hip")) if data.get("hip") else None
        arm.angle = data["angle"]
        return arm


def is_arm_active(
    arm: Arm,
    angle_threshold: int,
    hand_visible: bool = False,
) -> bool:
    """Return whether an arm is inside the signing space.

    Elbow angle alone misses one-handed signs made with a nearly straight arm.
    A detected hand whose wrist is clearly above the hip is also a useful sign
    signal, while the hand visibility requirement prevents an idle pose wrist
    from keeping a segment open by itself.
    """
    elbow_active = 0 < arm.angle < angle_threshold
    if elbow_active or not hand_visible or arm.wrist is None:
        return elbow_active

    if arm.hip is not None:
        torso_height = (
            abs(arm.hip[1] - arm.shoulder[1])
            if arm.shoulder is not None
            else 0.0
        )
        hip_margin = max(0.04, torso_height * 0.12)
        return arm.wrist[1] < arm.hip[1] - hip_margin

    if arm.shoulder is not None:
        return arm.wrist[1] < arm.shoulder[1] + 0.30

    return False


def ok_to_get_frame(
    arm: Arm,
    angle_threshold: int,
    min_num_up_frames: int,
    min_num_down_frames: int,
    current_time: int,
    delay: int,
    min_down_time_ms: int = 400,
    hand_visible: bool = False,
) -> bool:
    is_active = is_arm_active(arm, angle_threshold, hand_visible)

    if is_active:
        # "Up" logic
        if arm.is_up:
            arm.num_down_frames = 0
            arm.end_time = 0
            arm.start_down_time = 0
        else:
            arm.num_up_frames += 1
            if arm.num_up_frames >= min_num_up_frames:
                arm.is_up = True
                arm.num_up_frames = 0
            else:
                if arm.num_up_frames == 1:
                    arm.start_time = current_time - delay
                return False
    else:
        # "Down" logic
        if arm.is_up:
            if arm.num_down_frames == 0:
                arm.start_down_time = current_time
                arm.end_time = current_time + delay
            arm.num_down_frames += 1
            
            # Check if hand has been down long enough in milliseconds AND enough frames have passed
            elapsed_down_ms = current_time - arm.start_down_time
            if elapsed_down_ms >= min_down_time_ms and arm.num_down_frames >= min_num_down_frames:
                arm.is_up = False
                arm.num_down_frames = 0
                arm.start_down_time = 0
            else:
                return True
        else:
            arm.num_up_frames = 0
            arm.start_time = 0
            arm.start_down_time = 0

    return arm.is_up
