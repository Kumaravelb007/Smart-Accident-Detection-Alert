"""
Accident Detection Engine
CNN-based accident detection with OpenCV traffic analytics.
"""

from __future__ import annotations

import logging
import math
from itertools import combinations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import urlopen

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _center(box: tuple[int, int, int, int]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _iou(box_a: tuple[int, int, int, int], box_b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)

    inter_w = max(0, x2 - x1)
    inter_h = max(0, y2 - y1)
    inter = inter_w * inter_h
    if inter <= 0:
        return 0.0

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    union = area_a + area_b - inter
    return inter / float(max(union, 1))


@dataclass
class DetectionResult:
    """Unified output for detection runs."""

    accident_detected: bool = False
    confidence: float = 0.0
    frame: Optional[np.ndarray] = None
    frame_index: int = 0
    message: str = ""
    vehicle_count: int = 0
    severity: str = "Minor"
    strategy: str = ""
    traffic_analysis: dict = field(default_factory=dict)


class PretrainedVehicleObjectDetector:
    """
    Vehicle detector using pretrained MobileNet-SSD via OpenCV DNN.

    Falls back gracefully when model files are unavailable.
    """

    CLASS_NAMES = [
        "background",
        "aeroplane",
        "bicycle",
        "bird",
        "boat",
        "bottle",
        "bus",
        "car",
        "cat",
        "chair",
        "cow",
        "diningtable",
        "dog",
        "horse",
        "motorbike",
        "person",
        "pottedplant",
        "sheep",
        "sofa",
        "train",
        "tvmonitor",
    ]
    VEHICLE_CLASS_IDS = {2, 6, 7, 14, 19}

    def __init__(self, model_dir: Path, confidence_threshold: float = 0.35) -> None:
        self.model_dir = model_dir
        self.confidence_threshold = confidence_threshold
        self.net = None
        self._load()

    @property
    def is_available(self) -> bool:
        return self.net is not None

    def _load(self) -> None:
        prototxt_path = self.model_dir / "mobilenet_ssd_deploy.prototxt"
        weights_path = self.model_dir / "mobilenet_ssd.caffemodel"
        proto_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt"
        weights_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/mobilenet_iter_73000.caffemodel"

        try:
            self.model_dir.mkdir(parents=True, exist_ok=True)

            if not prototxt_path.exists():
                logger.info("Downloading MobileNet-SSD prototxt to %s", prototxt_path)
                with urlopen(proto_url, timeout=30) as response:
                    prototxt_path.write_bytes(response.read())

            if not weights_path.exists():
                logger.info("Downloading MobileNet-SSD caffemodel to %s", weights_path)
                with urlopen(weights_url, timeout=60) as response:
                    weights_path.write_bytes(response.read())

            self.net = cv2.dnn.readNetFromCaffe(str(prototxt_path), str(weights_path))
            logger.info("Pretrained vehicle detector loaded from MobileNet-SSD")
        except Exception as exc:
            logger.warning("Pretrained vehicle detector unavailable: %s", exc)
            self.net = None

    def detect(
        self,
        frame: np.ndarray,
        max_detections: int = 12,
    ) -> list[tuple[tuple[int, int, int, int], str, float]]:
        if self.net is None:
            return []

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)),
            scalefactor=0.007843,
            size=(300, 300),
            mean=127.5,
        )
        self.net.setInput(blob)
        detections = self.net.forward()

        objects: list[tuple[tuple[int, int, int, int], str, float]] = []
        for i in range(detections.shape[2]):
            score = float(detections[0, 0, i, 2])
            if score < self.confidence_threshold:
                continue

            class_id = int(detections[0, 0, i, 1])
            if class_id not in self.VEHICLE_CLASS_IDS:
                continue

            x1 = int(detections[0, 0, i, 3] * w)
            y1 = int(detections[0, 0, i, 4] * h)
            x2 = int(detections[0, 0, i, 5] * w)
            y2 = int(detections[0, 0, i, 6] * h)

            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(x1 + 1, min(x2, w))
            y2 = max(y1 + 1, min(y2, h))

            label = self.CLASS_NAMES[class_id] if class_id < len(self.CLASS_NAMES) else "vehicle"
            objects.append(((x1, y1, x2, y2), label, score))

        objects.sort(key=lambda item: item[2], reverse=True)
        return objects[:max_detections]


class MotionTrafficAnalyzer:
    """
    Lightweight traffic analytics using background subtraction and optical flow.

    This does not require YOLO and provides:
    - estimated vehicle count
    - density level
    - congestion indicator
    - motion anomaly score
    - rough speed estimate (relative)
    """

    def __init__(self) -> None:
        pretrained_dir = Path(__file__).resolve().parent / "pretrained"
        self.object_detector = PretrainedVehicleObjectDetector(pretrained_dir)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300,
            varThreshold=32,
            detectShadows=False,
        )

    @staticmethod
    def _resize_frame(frame: np.ndarray, max_width: int = 960) -> np.ndarray:
        h, w = frame.shape[:2]
        if w <= max_width:
            return frame
        scale = max_width / float(w)
        return cv2.resize(frame, (max_width, int(h * scale)))

    @staticmethod
    def _estimate_density(peak_count: int) -> str:
        if peak_count >= 12:
            return "High"
        if peak_count >= 6:
            return "Medium"
        return "Low"

    def _contour_fallback_boxes(self, frame: np.ndarray, max_boxes: int = 12) -> list[tuple[int, int, int, int]]:
        """Contour fallback for environments where DNN detector is unavailable."""
        h0, w0 = frame.shape[:2]
        resized = self._resize_frame(frame, max_width=960)
        hr, wr = resized.shape[:2]
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        fg_mask = self.bg_subtractor.apply(gray)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        boxes: list[tuple[int, int, int, int]] = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 450 or area > 120000:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if w < 20 or h < 20:
                continue

            ratio = w / float(max(h, 1))
            if ratio < 0.4 or ratio > 6.0:
                continue

            boxes.append((x, y, x + w, y + h))

        sx = w0 / float(max(wr, 1))
        sy = h0 / float(max(hr, 1))
        scaled_boxes: list[tuple[int, int, int, int]] = []
        for x1, y1, x2, y2 in boxes:
            scaled_boxes.append(
                (
                    int(x1 * sx),
                    int(y1 * sy),
                    int(x2 * sx),
                    int(y2 * sy),
                )
            )

        scaled_boxes = sorted(
            scaled_boxes,
            key=lambda b: max(1, (b[2] - b[0]) * (b[3] - b[1])),
            reverse=True,
        )
        return scaled_boxes[:max_boxes]

    def detect_vehicle_objects(
        self,
        frame: np.ndarray,
        max_boxes: int = 12,
    ) -> list[tuple[tuple[int, int, int, int], str, float]]:
        """Return detected vehicles as (box, label, confidence)."""
        dnn_objects = self.object_detector.detect(frame, max_detections=max_boxes)
        if dnn_objects:
            return dnn_objects

        fallback_boxes = self._contour_fallback_boxes(frame, max_boxes=max_boxes)
        return [(box, "vehicle", 0.0) for box in fallback_boxes]

    def detect_vehicle_boxes(self, frame: np.ndarray, max_boxes: int = 12) -> list[tuple[int, int, int, int]]:
        objects = self.detect_vehicle_objects(frame, max_boxes=max_boxes)
        return [box for box, _label, _score in objects]

    def analyze(self, frames: list[np.ndarray], fps_hint: float = 12.0) -> dict:
        if not frames:
            return {
                "average_vehicle_count": 0,
                "peak_vehicle_count": 0,
                "average_speed_kmh": 0.0,
                "peak_speed_kmh": 0.0,
                "speed_volatility_kmh": 0.0,
                "traffic_density": "Low",
                "congestion_detected": False,
                "anomaly_score": 0.0,
                "motion_spike_ratio": 0.0,
                "frames_analyzed": 0,
                "object_detector": "Unavailable",
            }

        frame_counts: list[int] = []
        speed_estimates: list[float] = []
        motion_energy: list[float] = []

        prev_gray: Optional[np.ndarray] = None
        prev_centers: list[tuple[float, float]] = []

        for frame in frames:
            resized = self._resize_frame(frame)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

            boxes = self.detect_vehicle_boxes(resized)
            frame_counts.append(len(boxes))

            centers = [((x1 + x2) / 2.0, (y1 + y2) / 2.0) for x1, y1, x2, y2 in boxes]

            if prev_centers and centers:
                displacements = []
                for center in centers:
                    nearest = min(
                        math.dist(center, prev) for prev in prev_centers
                    )
                    if nearest < 85:
                        displacements.append(nearest)

                if displacements:
                    # Rough conversion for dashboard-level trend analytics.
                    pixel_to_meter = 0.05
                    speed_kmh = float(np.mean(displacements) * fps_hint * pixel_to_meter * 3.6)
                    speed_estimates.append(speed_kmh)

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray,
                    gray,
                    None,
                    pyr_scale=0.5,
                    levels=3,
                    winsize=15,
                    iterations=3,
                    poly_n=5,
                    poly_sigma=1.2,
                    flags=0,
                )
                magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                motion_energy.append(float(np.mean(magnitude)))

            prev_gray = gray
            prev_centers = centers

        avg_count = float(np.mean(frame_counts)) if frame_counts else 0.0
        peak_count = max(frame_counts) if frame_counts else 0

        avg_speed = float(np.mean(speed_estimates)) if speed_estimates else 0.0
        peak_speed = max(speed_estimates) if speed_estimates else 0.0
        speed_volatility = float(np.std(speed_estimates)) if speed_estimates else 0.0

        density = self._estimate_density(peak_count)
        congestion = density == "High" and avg_speed < 18.0

        avg_motion = float(np.mean(motion_energy)) if motion_energy else 0.0
        max_motion = max(motion_energy) if motion_energy else 0.0
        spike_ratio = max_motion / max(avg_motion, 1e-4)

        count_variability = float(np.std(frame_counts)) / max(avg_count, 1.0)
        anomaly_score = _clamp(0.5 * min(spike_ratio / 4.0, 1.0) + 0.5 * min(count_variability, 1.0))

        return {
            "average_vehicle_count": int(round(avg_count)),
            "peak_vehicle_count": int(peak_count),
            "average_speed_kmh": round(avg_speed, 2),
            "peak_speed_kmh": round(peak_speed, 2),
            "speed_volatility_kmh": round(speed_volatility, 2),
            "traffic_density": density,
            "congestion_detected": congestion,
            "anomaly_score": round(anomaly_score, 4),
            "motion_spike_ratio": round(spike_ratio, 4),
            "frames_analyzed": len(frames),
            "object_detector": "MobileNet-SSD DNN" if self.object_detector.is_available else "ContourCV",
        }


class OpticalFlowSupportDetector:
    """Support detector that looks for crash-like motion patterns."""

    def __init__(self, confidence_threshold: float = 0.4) -> None:
        self.confidence_threshold = confidence_threshold

    def analyze(self, frames: list[np.ndarray]) -> DetectionResult:
        if len(frames) < 4:
            return DetectionResult(message="Not enough frames for motion support analysis")

        resized_frames = [MotionTrafficAnalyzer._resize_frame(frame, max_width=720) for frame in frames]

        prev_gray = cv2.cvtColor(resized_frames[0], cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.GaussianBlur(prev_gray, (9, 9), 0)

        energies: list[float] = []
        structural_changes: list[float] = []

        for frame in resized_frames[1:]:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (9, 9), 0)

            diff = cv2.absdiff(prev_gray, gray)
            energy = float(np.mean(diff) / 255.0)
            energies.append(energy)

            edges_prev = cv2.Canny(prev_gray, 70, 140)
            edges_curr = cv2.Canny(gray, 70, 140)
            edge_change = float(np.mean(cv2.absdiff(edges_prev, edges_curr)) / 255.0)
            structural_changes.append(edge_change)

            prev_gray = gray

        max_energy = max(energies) if energies else 0.0
        avg_energy = float(np.mean(energies)) if energies else 0.0
        spike_ratio = max_energy / max(avg_energy, 1e-4)

        max_structure = max(structural_changes) if structural_changes else 0.0

        confidence = 0.0
        reasons = []

        if spike_ratio > 2.0:
            confidence += min((spike_ratio - 2.0) * 0.16, 0.45)
            reasons.append(f"motion spike {spike_ratio:.1f}x")

        if max_energy > 0.12:
            confidence += min((max_energy - 0.12) * 1.8, 0.25)
            reasons.append("high abrupt motion")

        if max_structure > 0.18:
            confidence += min((max_structure - 0.18) * 1.2, 0.25)
            reasons.append("scene structure disruption")

        confidence = _clamp(confidence)
        max_index = int(np.argmax(energies)) + 1 if energies else 0

        return DetectionResult(
            accident_detected=confidence >= self.confidence_threshold,
            confidence=round(confidence, 4),
            frame=resized_frames[max_index].copy() if resized_frames else None,
            frame_index=max_index,
            message=" | ".join(reasons) if reasons else "No strong crash motion pattern",
            strategy="OpticalFlow-Support",
        )


class TrajectoryCollisionAnalyzer:
    """Collision-risk detector using object trajectories and overlap dynamics."""

    def __init__(self, traffic_analyzer: MotionTrafficAnalyzer, confidence_threshold: float = 0.4) -> None:
        self.traffic_analyzer = traffic_analyzer
        self.confidence_threshold = confidence_threshold

    @staticmethod
    def _pair_min_distance(centers: list[tuple[float, float]]) -> float:
        if len(centers) < 2:
            return 9999.0
        return min(math.dist(a, b) for a, b in combinations(centers, 2))

    @staticmethod
    def _max_iou(boxes: list[tuple[int, int, int, int]]) -> float:
        if len(boxes) < 2:
            return 0.0
        return max(_iou(a, b) for a, b in combinations(boxes, 2))

    def analyze(self, frames: list[np.ndarray]) -> DetectionResult:
        if len(frames) < 4:
            return DetectionResult(message="Not enough frames for trajectory analysis", strategy="Trajectory-Analysis")

        min_distances: list[float] = []
        overlaps: list[float] = []
        mean_displacements: list[float] = []
        event_scores: list[float] = []

        prev_centers: list[tuple[float, float]] = []
        reasons: list[str] = []

        for frame_idx, frame in enumerate(frames):
            boxes = self.traffic_analyzer.detect_vehicle_boxes(frame, max_boxes=8)
            centers = [_center(box) for box in boxes]

            min_dist = self._pair_min_distance(centers)
            overlap = self._max_iou(boxes)
            min_distances.append(min_dist)
            overlaps.append(overlap)

            if prev_centers and centers:
                displacements = []
                for c in centers:
                    nearest = min(math.dist(c, p) for p in prev_centers)
                    if nearest < 95:
                        displacements.append(nearest)
                mean_disp = float(np.mean(displacements)) if displacements else 0.0
            else:
                mean_disp = 0.0
            mean_displacements.append(mean_disp)

            score = 0.0

            # Sudden overlap spike in vehicles.
            if overlap > 0.12:
                score += min(overlap * 2.2, 0.45)

            # Rapid distance convergence between vehicles.
            if frame_idx > 0:
                prev_dist = min_distances[frame_idx - 1]
                if prev_dist > 0 and min_dist < prev_dist * 0.7 and min_dist < 110:
                    convergence = (prev_dist - min_dist) / max(prev_dist, 1e-4)
                    score += min(convergence * 0.45, 0.30)

            # Impact then deceleration pattern.
            if frame_idx > 1:
                prev_disp = mean_displacements[frame_idx - 1]
                if prev_disp > 4.0 and mean_disp < prev_disp * 0.45:
                    score += 0.18

            event_scores.append(_clamp(score))
            prev_centers = centers

        if not event_scores:
            return DetectionResult(message="No trajectory events computed", strategy="Trajectory-Analysis")

        raw_scores = np.array(event_scores, dtype=np.float32)
        if raw_scores.size >= 3:
            smooth_scores = np.convolve(raw_scores, np.array([0.25, 0.5, 0.25], dtype=np.float32), mode="same")
        else:
            smooth_scores = raw_scores

        max_score = float(np.max(smooth_scores))
        event_idx = int(np.argmax(smooth_scores))

        local_window = smooth_scores[max(0, event_idx - 1): min(len(smooth_scores), event_idx + 2)]
        persistence = float(np.mean(local_window)) if local_window.size else max_score
        confidence = _clamp((max_score * 0.6) + (persistence * 0.4))

        if confidence > 0.33:
            reasons.append("rapid vehicle convergence detected")
        if overlaps[event_idx] > 0.12:
            reasons.append(f"vehicle overlap IoU={overlaps[event_idx]:.2f}")
        if event_idx > 0 and min_distances[event_idx] < min_distances[event_idx - 1] * 0.75:
            reasons.append("distance collapse between tracked vehicles")
        if event_idx > 1 and mean_displacements[event_idx - 1] > 4.0 and mean_displacements[event_idx] < mean_displacements[event_idx - 1] * 0.45:
            reasons.append("post-impact sudden slowdown")

        return DetectionResult(
            accident_detected=confidence >= self.confidence_threshold,
            confidence=round(confidence, 4),
            frame=frames[event_idx].copy(),
            frame_index=event_idx,
            message=" | ".join(reasons) if reasons else "No high-risk trajectory collision pattern",
            strategy="Trajectory-Analysis",
        )


class CNNAccidentDetector:
    """
    CNN-based accident detector.

    Priority:
    1) Load a predefined trained Keras model from disk when available.
    2) Fallback to pretrained MobileNetV2 feature-spike detection.
    3) If TensorFlow is unavailable, fallback to predefined SqueezeNet ONNX CNN features.
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.4,
        input_size: int = 224,
    ) -> None:
        self.model_path = Path(model_path)
        self.confidence_threshold = confidence_threshold
        self.input_size = input_size

        self.tf = None
        self.custom_model = None
        self.feature_model = None
        self.onnx_net = None
        self.onnx_input_size = 227
        self.strategy_name = ""

        self._load_models()

    @property
    def is_available(self) -> bool:
        return (
            (self.tf is not None and (self.custom_model is not None or self.feature_model is not None))
            or self.onnx_net is not None
        )

    def _load_models(self) -> None:
        try:
            import tensorflow as tf

            self.tf = tf
        except Exception as exc:
            logger.warning("TensorFlow is unavailable: %s", exc)
            self._load_onnx_fallback()
            return

        if self.model_path.exists():
            try:
                self.custom_model = self.tf.keras.models.load_model(str(self.model_path), compile=False)
                self.strategy_name = "CNN-Pretrained(Custom)"
                logger.info("Loaded predefined CNN model from %s", self.model_path)
                return
            except Exception as exc:
                logger.warning("Custom CNN model load failed (%s). Falling back to MobileNetV2.", exc)

        try:
            self.feature_model = self.tf.keras.applications.MobileNetV2(
                input_shape=(self.input_size, self.input_size, 3),
                include_top=False,
                weights="imagenet",
                pooling="avg",
            )
            self.strategy_name = "CNN-Pretrained(MobileNetV2 Features)"
            logger.info("Using MobileNetV2 pretrained feature extractor fallback")
        except Exception as exc:
            logger.error("Failed to initialize fallback CNN model: %s", exc)
            self._load_onnx_fallback()

    def _load_onnx_fallback(self) -> None:
        """
        Load a predefined ONNX CNN fallback model when TensorFlow is unavailable.

        Uses SqueezeNet 1.1 from ONNX model zoo.
        """
        onnx_path = self.model_path.parent / "squeezenet1.1-7.onnx"
        model_url = (
            "https://github.com/onnx/models/raw/main/validated/vision/classification/"
            "squeezenet/model/squeezenet1.1-7.onnx"
        )

        try:
            if not onnx_path.exists():
                logger.info("Downloading predefined CNN fallback model to %s", onnx_path)
                with urlopen(model_url, timeout=30) as response:
                    data = response.read()
                onnx_path.parent.mkdir(parents=True, exist_ok=True)
                onnx_path.write_bytes(data)

            self.onnx_net = cv2.dnn.readNetFromONNX(str(onnx_path))
            self.strategy_name = "CNN-Predefined(SqueezeNet-ONNX)"
            logger.info("Loaded ONNX CNN fallback model: %s", onnx_path)
        except Exception as exc:
            logger.error("ONNX CNN fallback unavailable: %s", exc)

    def _prepare_batch(self, frames: list[np.ndarray]) -> np.ndarray:
        batch = []
        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (self.input_size, self.input_size))
            batch.append(resized.astype(np.float32))

        if not batch:
            return np.zeros((0, self.input_size, self.input_size, 3), dtype=np.float32)

        arr = np.stack(batch, axis=0)
        preprocess = self.tf.keras.applications.mobilenet_v2.preprocess_input
        return preprocess(arr)

    def _analyze_custom_model(self, frames: list[np.ndarray]) -> DetectionResult:
        batch = self._prepare_batch(frames)
        if batch.size == 0:
            return DetectionResult(message="No frames available for CNN analysis")

        raw = self.custom_model.predict(batch, verbose=0)
        probs = np.asarray(raw).reshape(-1)

        if probs.size == 0:
            return DetectionResult(message="Custom CNN produced no output", strategy=self.strategy_name)

        if np.any(probs > 1.0) or np.any(probs < 0.0):
            probs = 1.0 / (1.0 + np.exp(-probs))

        probs = np.clip(probs, 0.0, 1.0)
        idx = int(np.argmax(probs))
        confidence = float(probs[idx])

        severity = "Critical" if confidence >= 0.8 else "Moderate" if confidence >= 0.55 else "Minor"

        return DetectionResult(
            accident_detected=confidence >= self.confidence_threshold,
            confidence=round(confidence, 4),
            frame=frames[idx].copy(),
            frame_index=idx,
            message=f"CNN accident probability peak at frame {idx}",
            severity=severity,
            strategy=self.strategy_name,
        )

    def _analyze_feature_spike(self, frames: list[np.ndarray], traffic_analysis: dict) -> DetectionResult:
        batch = self._prepare_batch(frames)
        if batch.size == 0:
            return DetectionResult(message="No frames available for CNN analysis")

        features = self.feature_model.predict(batch, verbose=0)

        if len(features) < 2:
            return DetectionResult(
                accident_detected=False,
                confidence=0.1,
                frame=frames[0].copy() if frames else None,
                frame_index=0,
                message="Insufficient frame transitions for CNN feature analysis",
                severity="Minor",
                strategy=self.strategy_name,
            )

        feature_deltas = np.linalg.norm(features[1:] - features[:-1], axis=1)

        gray_frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
        intensity_deltas = [
            float(np.mean(cv2.absdiff(gray_frames[i - 1], gray_frames[i])) / 255.0)
            for i in range(1, len(gray_frames))
        ]

        delta_mean = float(np.mean(feature_deltas))
        delta_max = float(np.max(feature_deltas))
        spike_ratio = delta_max / max(delta_mean, 1e-4)

        motion_mean = float(np.mean(intensity_deltas)) if intensity_deltas else 0.0
        motion_max = float(np.max(intensity_deltas)) if intensity_deltas else 0.0
        motion_spike = motion_max / max(motion_mean, 1e-4) if motion_mean > 0 else 1.0

        score = 0.0
        reasons = []

        if spike_ratio > 1.8:
            score += min((spike_ratio - 1.8) * 0.24, 0.45)
            reasons.append(f"CNN feature spike {spike_ratio:.2f}x")

        if motion_spike > 1.9:
            score += min((motion_spike - 1.9) * 0.20, 0.25)
            reasons.append(f"motion spike {motion_spike:.2f}x")

        if traffic_analysis.get("anomaly_score", 0.0) > 0.45:
            score += min(float(traffic_analysis["anomaly_score"]) * 0.25, 0.2)
            reasons.append("traffic anomaly confirmation")

        if traffic_analysis.get("congestion_detected"):
            score += 0.1
            reasons.append("congestion context")

        confidence = _clamp(score)

        key_pair_idx = int(np.argmax(feature_deltas))
        frame_idx = min(key_pair_idx + 1, len(frames) - 1)

        severity = "Critical" if confidence >= 0.78 else "Moderate" if confidence >= 0.5 else "Minor"

        return DetectionResult(
            accident_detected=confidence >= self.confidence_threshold,
            confidence=round(confidence, 4),
            frame=frames[frame_idx].copy(),
            frame_index=frame_idx,
            message=" | ".join(reasons) if reasons else "No critical CNN anomaly pattern",
            severity=severity,
            strategy=self.strategy_name,
        )

    def _extract_onnx_vector(self, frame: np.ndarray) -> np.ndarray:
        resized = cv2.resize(frame, (self.onnx_input_size, self.onnx_input_size))
        blob = cv2.dnn.blobFromImage(
            resized,
            scalefactor=1.0 / 255.0,
            size=(self.onnx_input_size, self.onnx_input_size),
            mean=(0.0, 0.0, 0.0),
            swapRB=True,
            crop=True,
        )
        self.onnx_net.setInput(blob)
        out = self.onnx_net.forward()
        vector = out.reshape(-1).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if norm > 0:
            vector /= norm
        return vector

    def _analyze_onnx_spike(self, frames: list[np.ndarray], traffic_analysis: dict) -> DetectionResult:
        features = [self._extract_onnx_vector(frame) for frame in frames]
        if len(features) < 2:
            return DetectionResult(
                accident_detected=False,
                confidence=0.1,
                frame=frames[0].copy() if frames else None,
                frame_index=0,
                message="Insufficient ONNX CNN transitions",
                severity="Minor",
                strategy=self.strategy_name,
            )

        feature_deltas = np.linalg.norm(np.array(features[1:]) - np.array(features[:-1]), axis=1)

        gray_frames = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in frames]
        intensity_deltas = [
            float(np.mean(cv2.absdiff(gray_frames[i - 1], gray_frames[i])) / 255.0)
            for i in range(1, len(gray_frames))
        ]

        delta_mean = float(np.mean(feature_deltas))
        delta_max = float(np.max(feature_deltas))
        spike_ratio = delta_max / max(delta_mean, 1e-4)

        motion_mean = float(np.mean(intensity_deltas)) if intensity_deltas else 0.0
        motion_max = float(np.max(intensity_deltas)) if intensity_deltas else 0.0
        motion_spike = motion_max / max(motion_mean, 1e-4) if motion_mean > 0 else 1.0

        score = 0.0
        reasons = []

        if spike_ratio > 1.55:
            score += min((spike_ratio - 1.55) * 0.22, 0.46)
            reasons.append(f"ONNX CNN feature spike {spike_ratio:.2f}x")

        if motion_spike > 1.9:
            score += min((motion_spike - 1.9) * 0.2, 0.24)
            reasons.append(f"motion spike {motion_spike:.2f}x")

        if traffic_analysis.get("anomaly_score", 0.0) > 0.45:
            score += min(float(traffic_analysis["anomaly_score"]) * 0.22, 0.2)
            reasons.append("traffic anomaly confirmation")

        if traffic_analysis.get("congestion_detected"):
            score += 0.1
            reasons.append("congestion context")

        confidence = _clamp(score)
        frame_idx = min(int(np.argmax(feature_deltas)) + 1, len(frames) - 1)
        severity = "Critical" if confidence >= 0.78 else "Moderate" if confidence >= 0.5 else "Minor"

        return DetectionResult(
            accident_detected=confidence >= self.confidence_threshold,
            confidence=round(confidence, 4),
            frame=frames[frame_idx].copy(),
            frame_index=frame_idx,
            message=" | ".join(reasons) if reasons else "No critical ONNX CNN anomaly pattern",
            severity=severity,
            strategy=self.strategy_name,
        )

    def analyze(self, frames: list[np.ndarray], traffic_analysis: dict) -> DetectionResult:
        if not frames:
            return DetectionResult(message="No frames available")

        if not self.is_available:
            return DetectionResult(
                accident_detected=False,
                confidence=0.0,
                frame=frames[0].copy(),
                frame_index=0,
                message="CNN model unavailable",
                severity="Minor",
                strategy="CNN-Unavailable",
            )

        if self.custom_model is not None:
            return self._analyze_custom_model(frames)

        if self.feature_model is not None:
            return self._analyze_feature_spike(frames, traffic_analysis)

        if self.onnx_net is not None:
            return self._analyze_onnx_spike(frames, traffic_analysis)

        return DetectionResult(
            accident_detected=False,
            confidence=0.0,
            frame=frames[0].copy(),
            frame_index=0,
            message="CNN model unavailable",
            severity="Minor",
            strategy="CNN-Unavailable",
        )


class AccidentDetector:
    """Unified detector: CNN-first accident detection + OpenCV traffic analytics."""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.4,
        cnn_input_size: int = 224,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.traffic_analyzer = MotionTrafficAnalyzer()
        self.cnn_detector = CNNAccidentDetector(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            input_size=cnn_input_size,
        )
        self.motion_support = OpticalFlowSupportDetector(confidence_threshold=confidence_threshold)
        self.trajectory_support = TrajectoryCollisionAnalyzer(
            traffic_analyzer=self.traffic_analyzer,
            confidence_threshold=confidence_threshold,
        )

    @property
    def active_strategy(self) -> str:
        object_detector_name = "MobileNet-SSD DNN" if self.traffic_analyzer.object_detector.is_available else "ContourCV"
        if self.cnn_detector.is_available:
            return f"{self.cnn_detector.strategy_name} + Trajectory + OpticalFlow + {object_detector_name}"
        return f"Trajectory + OpticalFlow + {object_detector_name}"

    @staticmethod
    def _severity_from_confidence(confidence: float, congestion: bool) -> str:
        if confidence >= 0.8 or (confidence >= 0.68 and congestion):
            return "Critical"
        if confidence >= 0.5:
            return "Moderate"
        return "Minor"

    @staticmethod
    def _calibrate_signal(value: float, bias: float, gain: float) -> float:
        return _clamp((value - bias) * gain)

    def _dynamic_threshold(self, traffic_analysis: dict) -> float:
        threshold = float(self.confidence_threshold)
        peak_vehicles = int(traffic_analysis.get("peak_vehicle_count", 0))

        if peak_vehicles <= 1:
            threshold += 0.08
        elif peak_vehicles >= 5:
            threshold -= 0.02

        if traffic_analysis.get("object_detector") == "ContourCV":
            threshold += 0.03

        if float(traffic_analysis.get("anomaly_score", 0.0)) > 0.60:
            threshold -= 0.04

        if float(traffic_analysis.get("motion_spike_ratio", 0.0)) > 2.5:
            threshold -= 0.03

        if float(traffic_analysis.get("speed_volatility_kmh", 0.0)) > 14:
            threshold -= 0.02

        return _clamp(threshold, low=0.33, high=0.62)

    def _annotate_frame(
        self,
        frame: np.ndarray,
        confidence: float,
        severity: str,
        traffic_analysis: dict,
    ) -> np.ndarray:
        annotated = frame.copy()

        detections = self.traffic_analyzer.detect_vehicle_objects(annotated, max_boxes=8)
        for box, label, score in detections[:6]:
            x1, y1, x2, y2 = box
            color = (0, 0, 235) if confidence >= self.confidence_threshold else (0, 175, 235)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 1)

            # Small readable tag to avoid covering evidence.
            label_text = label if score <= 0 else f"{label} {score:.2f}"
            cv2.putText(
                annotated,
                label_text,
                (x1, max(10, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.36,
                color,
                1,
                cv2.LINE_AA,
            )

        # Compact translucent status chip for email evidence clarity.
        overlay = annotated.copy()
        h, w = annotated.shape[:2]
        chip_w = min(310, int(w * 0.52))
        chip_h = min(64, int(h * 0.18))
        x0, y0 = 10, 10
        x1, y1 = x0 + chip_w, y0 + chip_h
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (18, 18, 18), -1)
        cv2.addWeighted(overlay, 0.40, annotated, 0.60, 0, annotated)

        border_color = (30, 170, 240) if confidence < self.confidence_threshold else (0, 80, 230)
        cv2.rectangle(annotated, (x0, y0), (x1, y1), border_color, 1)

        cv2.putText(
            annotated,
            f"Conf {confidence * 100:.1f}% | {severity}",
            (x0 + 8, y0 + 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.43,
            (245, 245, 245),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            annotated,
            f"Traffic {traffic_analysis.get('traffic_density', 'Low')} | Veh {traffic_analysis.get('peak_vehicle_count', 0)}",
            (x0 + 8, y0 + 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            (235, 235, 235),
            1,
            cv2.LINE_AA,
        )

        return annotated

    def detect(self, frames: list[np.ndarray]) -> DetectionResult:
        if not frames:
            return DetectionResult(message="No frames extracted from video")

        traffic_analysis = self.traffic_analyzer.analyze(frames)

        cnn_result = self.cnn_detector.analyze(frames, traffic_analysis)
        support_result = self.motion_support.analyze(frames)
        trajectory_result = self.trajectory_support.analyze(frames)

        cnn_conf = self._calibrate_signal(cnn_result.confidence, bias=0.06, gain=1.05)
        support_conf = self._calibrate_signal(support_result.confidence, bias=0.05, gain=0.95)
        trajectory_conf = self._calibrate_signal(trajectory_result.confidence, bias=0.03, gain=1.05)

        final_confidence = (cnn_conf * 0.52) + (support_conf * 0.20) + (trajectory_conf * 0.28)
        final_confidence = _clamp(final_confidence)

        best_result = max(
            [cnn_result, support_result, trajectory_result],
            key=lambda result: result.confidence,
        )
        best_frame = best_result.frame if best_result.frame is not None else frames[0].copy()
        best_index = best_result.frame_index

        final_message_parts = []
        if cnn_result.message:
            final_message_parts.append(cnn_result.message)
        if trajectory_result.accident_detected:
            final_message_parts.append("Trajectory analysis confirms high collision risk")
        if support_result.accident_detected:
            final_message_parts.append("Optical-flow impact pattern detected")

        dynamic_threshold = self._dynamic_threshold(traffic_analysis)

        peak_indexes = [cnn_result.frame_index, support_result.frame_index, trajectory_result.frame_index]
        frame_spread = max(peak_indexes) - min(peak_indexes)
        if frame_spread <= 2:
            final_confidence = _clamp(final_confidence + 0.07)
            final_message_parts.append("Detector peaks are temporally aligned")
        elif frame_spread >= 7:
            final_confidence = _clamp(final_confidence - 0.06)
            final_message_parts.append("Detector peaks are temporally inconsistent")

        # Consensus boost for multi-signal agreement.
        agreeing_detectors = sum(
            1 for result in (cnn_result, support_result, trajectory_result) if result.accident_detected
        )
        if agreeing_detectors >= 2:
            final_confidence = _clamp(final_confidence + 0.10)
        if agreeing_detectors == 3:
            final_confidence = _clamp(final_confidence + 0.06)

        peak_vehicle_count = int(traffic_analysis.get("peak_vehicle_count", 0))
        if peak_vehicle_count < 2 and trajectory_conf < 0.25 and cnn_conf < 0.60:
            final_confidence = _clamp(final_confidence - 0.13)
            final_message_parts.append("Low multi-vehicle evidence reduced false-positive risk")

        if support_conf > 0.50 and trajectory_conf < 0.20 and peak_vehicle_count < 2:
            final_confidence = _clamp(final_confidence - 0.14)
            final_message_parts.append("High motion without collision geometry likely camera disturbance")

        if cnn_conf > 0.75 and trajectory_conf > 0.35:
            final_confidence = _clamp(final_confidence + 0.07)
            final_message_parts.append("CNN and trajectory strongly agree on impact event")

        congestion = bool(traffic_analysis.get("congestion_detected", False))
        severity = self._severity_from_confidence(final_confidence, congestion)

        annotated = self._annotate_frame(
            best_frame,
            final_confidence,
            severity,
            traffic_analysis,
        )

        is_accident = final_confidence >= dynamic_threshold
        if not is_accident and final_confidence >= dynamic_threshold - 0.04:
            final_message_parts.append("Borderline risk observed; manual review recommended")

        traffic_analysis["decision_threshold"] = round(dynamic_threshold, 4)
        traffic_analysis["signal_breakdown"] = {
            "cnn": round(cnn_conf, 4),
            "trajectory": round(trajectory_conf, 4),
            "optical_flow": round(support_conf, 4),
        }
        traffic_analysis["consensus_detectors"] = agreeing_detectors

        return DetectionResult(
            accident_detected=is_accident,
            confidence=round(final_confidence, 4),
            frame=annotated,
            frame_index=best_index,
            message=" | ".join(part for part in final_message_parts if part),
            vehicle_count=int(traffic_analysis.get("peak_vehicle_count", 0)),
            severity=severity,
            strategy=self.active_strategy,
            traffic_analysis=traffic_analysis,
        )
