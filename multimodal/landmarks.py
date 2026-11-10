"""Original Holistic pose/hands graph, without its unused face mesh branch.

The source model obtains four face points from its separate FaceDetection graph.
Holistic's 468-point mesh never contributes to either encoder. Removing that
terminal branch leaves the pose/hand calculators, tracking and options intact.
See the paired-frame probe before accepting any graph/runtime change.
"""
from pathlib import Path

import mediapipe as mp
from mediapipe.framework import calculator_pb2
from mediapipe.python.solution_base import SolutionBase
from mediapipe.modules.face_detection import face_detection_pb2
from mediapipe.calculators.tensor import inference_calculator_pb2


class BoundedSolution(SolutionBase):
    # XNNPACK defaults to -1 (automatic cores) per inference node. Bound each
    # kernel while the two graph threads can still overlap left/right hands.
    # Model files, precision, calculators and tensor values stay unchanged.
    def _initialize_graph_interface(self, *args, **kwargs):
        graph = super()._initialize_graph_interface(*args, **kwargs)
        for node in graph.node:
            if node.calculator == "InferenceCalculatorCpu":
                options = node.options.Extensions[inference_calculator_pb2.InferenceCalculatorOptions.ext]
                if options.delegate.HasField("xnnpack"):
                    options.delegate.xnnpack.num_threads = 1
        return graph


class FacePoints(BoundedSolution):
    def __init__(self):
        graph = calculator_pb2.CalculatorGraphConfig()
        graph.ParseFromString((Path(mp.__file__).parent /
            "modules/face_detection/face_detection_full_range_cpu.binarypb").read_bytes())
        graph.num_threads = 2
        super().__init__(graph_config=graph, graph_options=self.create_graph_options(
            face_detection_pb2.FaceDetectionOptions(), {"min_score_thresh": .5}), outputs=["detections"])

    def process(self, image):
        return super().process(input_data={"image": image})


class PoseHands(BoundedSolution):
    def __init__(self):
        graph = calculator_pb2.CalculatorGraphConfig()
        graph.ParseFromString((Path(mp.__file__).parent /
            "modules/holistic_landmark/holistic_landmark_cpu.binarypb").read_bytes())
        assert [n.calculator for n in graph.node] == [
            "PoseLandmarkCpu", "HandLandmarksLeftAndRightCpu",
            "SplitNormalizedLandmarkListCalculator", "FaceLandmarksFromPoseCpu"]
        del graph.node[2:]
        graph.output_stream.remove("FACE_LANDMARKS:face_landmarks")
        graph.input_side_packet.remove("REFINE_FACE_LANDMARKS:refine_face_landmarks")
        graph.num_threads = 2
        super().__init__(graph_config=graph, side_inputs={
            "model_complexity": 1, "smooth_landmarks": True,
            "enable_segmentation": False, "smooth_segmentation": True,
            "use_prev_landmarks": True,
        }, calculator_params={
            "poselandmarkcpu__posedetectioncpu__TensorsToDetectionsCalculator.min_score_thresh": .5,
            "poselandmarkcpu__poselandmarkbyroicpu__tensorstoposelandmarksandsegmentation__ThresholdingCalculator.threshold": .5,
        }, outputs=["pose_landmarks", "left_hand_landmarks", "right_hand_landmarks"])

    def process(self, image):
        return super().process(input_data={"image": image})
