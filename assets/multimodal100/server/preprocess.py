"""The locked MediaPipe + custom ROI contract, with reproducible frame storage."""
import json
import os
import subprocess
import time
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import cv2
import mediapipe as mp
import numpy as np
from .engine import ROOT
from .vendor.crop_geometry import filter_points, crops

FFMPEG = Path(r"C:\\Users\thien\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe")


def crops_from_gray(gray, points, reference):
    """Same affine arithmetic as locked crops(), bypass repeated RGB decode."""
    target = np.vstack([reference[36:42].mean(0), reference[42:48].mean(0),
                        reference[31:36].mean(0), reference[48:68].mean(0)])
    valid = np.array([i for i,p in enumerate(points) if p is not None])
    if len(valid)<2:
        raise ValueError("Insufficient anchors after geometry filtering")
    pts=np.array([points[i] for i in valid])
    interpolated=np.stack([np.interp(np.arange(len(points)),valid,pts[:,j,k])
                            for j in range(4) for k in range(2)],1).reshape(-1,4,2)
    result=[]
    for i,frame in enumerate(gray):
        margin=min(6,i,len(gray)-1-i)
        smooth=interpolated[i-margin:i+margin+1].mean(0)
        smooth+=interpolated[i].mean(0)-smooth.mean(0)
        matrix,_=cv2.estimateAffinePartial2D(smooth,target,method=cv2.LMEDS)
        if matrix is None:
            raise ValueError("Alignment failed")
        warped=cv2.warpAffine(frame,matrix,(256,256),flags=cv2.INTER_LINEAR)
        center=smooth[3]@matrix[:,:2].T+matrix[:,2];x,y=np.rint(center).astype(int)
        crop=warped[y-48:y+48,x-48:x+48]
        if crop.shape!=(96,96):
            raise ValueError("Out-of-frame crop")
        result.append(crop)
    return np.stack(result)


def canonical_square(rgb):
    h, w = rgb.shape[:2]
    if (h, w) == (1080, 1080):
        return rgb
    # Preserve aspect and handedness. Camera orientation is corrected by client.
    scale = 1080 / max(h, w)
    nw, nh = round(w * scale), round(h * scale)
    canvas = np.zeros((1080, 1080, 3), np.uint8)
    x, y = (1080-nw)//2, (1080-nh)//2
    canvas[y:y+nh, x:x+nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return canvas


class FrameSequence:
    def __init__(self, paths, indices):
        self.paths, self.indices = paths, indices
    def __len__(self):
        return len(self.indices)
    def __getitem__(self, i):
        if i >= len(self):
            raise IndexError(i)
        image = cv2.imdecode(np.fromfile(self.paths[self.indices[i]], np.uint8), cv2.IMREAD_COLOR)
        return canonical_square(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


class Processor:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        cv2.setNumThreads(1)
        self.face = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=.5)
        self.holistic = mp.solutions.holistic.Holistic(
            static_image_mode=False, model_complexity=1, smooth_landmarks=True,
            min_detection_confidence=.5, min_tracking_confidence=.5)
        self.poses, self.points, self.paths, self.meta = [], [], [], []
        self.gray = []
        self.elapsed_ms = 0
        self.closed = False

    def append(self, encoded, frame_id, capture_ms, exact_rgb=None):
        start = time.perf_counter()
        if self.closed:
            raise ValueError("trial_closed")
        if len(self.paths) >= 300:
            raise ValueError("frame_limit")
        if self.meta and (frame_id <= self.meta[-1]["frame_id"] or capture_ms <= self.meta[-1]["capture_ms"]):
            raise ValueError("out_of_order_frame")
        rgb = exact_rgb
        if rgb is None:
            bgr = cv2.imdecode(np.frombuffer(encoded, np.uint8), cv2.IMREAD_COLOR)
            if bgr is None:
                raise ValueError("invalid_image")
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb = canonical_square(rgb)
        path = self.directory / f"{frame_id:06d}.jpg"
        if encoded:
            # Preserve incoming bytes: decoding + canonical_square is deterministic.
            path.write_bytes(encoded)
        else:
            # Video replay already keeps source.mp4; retain exact frames for diagnostics.
            path = path.with_suffix(".png")
            ok, png = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_PNG_COMPRESSION, 1])
            if not ok:
                raise ValueError("encode_failed")
            path.write_bytes(png.tobytes())
        self.gray.append(cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY))
        save_ms=(time.perf_counter()-start)*1000
        detections = self.face.process(rgb).detections or []
        points = np.array([[p.x*1080, p.y*1080] for p in detections[0].location_data.relative_keypoints[:4]], np.float32) if len(detections) == 1 else None
        result = self.holistic.process(rgb)
        pose = np.zeros((75, 4), np.float32)
        for field, a, b in [("pose_landmarks",0,33), ("left_hand_landmarks",33,54), ("right_hand_landmarks",54,75)]:
            group = getattr(result, field)
            if group:
                pose[a:b] = [[v.x, v.y, v.z, v.visibility if field == "pose_landmarks" else 1.] for v in group.landmark]
        self.poses.append(pose)
        self.points.append(points)
        self.paths.append(path)
        ms = (time.perf_counter()-start)*1000
        self.elapsed_ms += ms
        self.meta.append(dict(frame_id=frame_id, capture_ms=capture_ms, faces=len(detections), preprocess_ms=ms,
                              decode_save_gray_ms=save_ms, detector_ms=ms-save_ms))
        return dict(frame_id=frame_id, preprocess_ms=ms, valid_face=len(detections)==1, valid_pose=bool((pose[:33,3]>.5).any()))

    def finish(self, resample=True):
        if len(self.paths) < 6:
            raise ValueError("insufficient_frames")
        start = time.perf_counter()
        times = np.array([m["capture_ms"] for m in self.meta])
        targets = np.arange(times[0], times[-1]+.01, 40.)
        indices = np.abs(times[:, None]-targets[None]).argmin(0) if resample else np.arange(len(times))
        pose = np.stack(self.poses)[indices]
        points = [self.points[i] for i in indices]
        # Sign validity is assessed independently of face availability.
        sign_valid = bool((pose[:, :33, 3] >= .5).any() and (pose[:, 33:, 3] > 0).any())
        mouth = None
        geometry = {}
        try:
            filtered, geometry = filter_points(points, pose)
            mouth = crops_from_gray([self.gray[i] for i in indices], filtered, np.load(ROOT / "models/assets/mean_face.npy"))
        except ValueError as exc:
            geometry["unavailable_reason"] = str(exc)
        info = dict(frame_count=len(times), sampled_frames=len(indices),
                    capture_span_ms=float(times[-1]-times[0]), input_fps=float((len(times)-1)*1000/(times[-1]-times[0])),
                    frame_ids=[self.meta[i]["frame_id"] for i in indices], geometry=geometry,
                    sign_valid=sign_valid, mouth_valid=mouth is not None,
                    preprocess_ms=self.elapsed_ms, roi_ms=(time.perf_counter()-start)*1000,
                    sampling="nearest capture timestamp at 25fps" if resample else "ffmpeg fps=25",
                    frames=self.meta)
        np.savez_compressed(self.directory.parent / "pixels.npz", keypoints=pose,
                            mouth=np.empty((0,96,96), np.uint8) if mouth is None else mouth, fps=np.float32(25))
        (self.directory.parent / "preprocessing.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), "utf8")
        return pose if sign_valid else None, mouth, info

    def close(self):
        if not self.closed:
            self.closed = True
            self.face.close()
            self.holistic.close()


def prepare_video(path, directory):
    processor = Processor(Path(directory) / "frames")
    probe = cv2.VideoCapture(str(path))
    width, height = int(probe.get(cv2.CAP_PROP_FRAME_WIDTH)), int(probe.get(cv2.CAP_PROP_FRAME_HEIGHT))
    probe.release()
    if width < 1 or height < 1:
        raise ValueError("invalid_video")
    # ffmpeg honors display rotation. Use square output so raw shape is explicit.
    vf = "fps=25,scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2"
    command = [str(FFMPEG), "-loglevel","error","-threads","1","-filter_threads","1",
               "-i", str(path), "-vf",vf, "-pix_fmt","rgb24","-f","rawvideo","pipe:1"]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        i = 0
        while True:
            data = proc.stdout.read(1080*1080*3)
            if not data:
                break
            if len(data) != 1080*1080*3:
                raise ValueError("truncated_decode")
            processor.append(b"", i, i*40., np.frombuffer(data,np.uint8).reshape(1080,1080,3))
            i += 1
        error = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise ValueError(error)
        return processor.finish(resample=False)
    finally:
        if proc.poll() is None:
            proc.kill()
        processor.close()
