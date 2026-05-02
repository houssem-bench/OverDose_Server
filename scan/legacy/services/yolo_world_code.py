from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

try:
    from ultralytics import YOLO  # type: ignore[import-not-found]

    try:
        from ultralytics import YOLOWorld  # type: ignore[import-not-found]
    except ImportError:
        YOLOWorld = None  # type: ignore[assignment]

    ULTRALYTICS_AVAILABLE = True
except ImportError:
    YOLO = None  # type: ignore[assignment]
    YOLOWorld = None  # type: ignore[assignment]
    ULTRALYTICS_AVAILABLE = False


logger = logging.getLogger(__name__)


def yolo_box_filter_reason(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    image_height: int,
    image_width: int,
    max_area_ratio: float = 0.25,
    max_dim_ratio: float = 0.7,
    edge_threshold: int = 20,
) -> Optional[str]:
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)
    area = w * h
    image_area = image_height * image_width

    if area > image_area * max_area_ratio:
        return "area"

    width_ratio = w / max(1, image_width)
    height_ratio = h / max(1, image_height)
    if width_ratio > max_dim_ratio or height_ratio > max_dim_ratio:
        return "dimensions"

    touches_top = y1 < edge_threshold
    touches_bottom = y2 > (image_height - edge_threshold)
    touches_left = x1 < edge_threshold
    touches_right = x2 > (image_width - edge_threshold)
    if touches_top and touches_bottom and touches_left and touches_right:
        return "full_frame"

    return None


class YOLOWorldProductWorkflow:
    def __init__(
        self,
        model_name: str = "yolov8l-world.pt",
        world_classes: Optional[List[str]] = None,
        conf_threshold: float = 0.02,
        iou_threshold: float = 0.2,
        nested_containment_threshold: float = 0.9,
    ) -> None:
        self.model_name = model_name
        self.world_classes = world_classes or [
            "food product",
            "package",
            "box",
            "bottle",
            "can",
            "carton",
            "jar",
            "pouch",
        ]
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.nested_containment_threshold = nested_containment_threshold

        self.model = self._load_model() if ULTRALYTICS_AVAILABLE else None

    def _load_model(self):
        model_name_lower = Path(self.model_name).name.lower()
        wants_world_model = "world" in model_name_lower

        if not wants_world_model:
            logger.warning(
                "YOLO-World disabled: model '%s' is not a '*-world*' checkpoint; falling back to contour detection",
                self.model_name,
            )
            return None

        model = None
        if YOLOWorld is not None:
            model = YOLOWorld(self.model_name)
        elif YOLO is not None:
            model = YOLO(self.model_name)

        if model is None:
            return None

        try:
            if hasattr(model, "set_classes"):
                model.set_classes(self.world_classes)
        except AttributeError:
            logger.exception(
                "YOLO-World load failed for model '%s': set_classes is not supported by this checkpoint",
                self.model_name,
            )
            return None

        return model

    def _merge_confidence(self, base_conf: float, nested_conf: float) -> float:
        base = min(1.0, max(0.0, float(base_conf)))
        nested = min(1.0, max(0.0, float(nested_conf)))
        return min(1.0, base + nested - (base * nested))

    def _merge_detection_geometry(self, container: Dict[str, object], inner: Dict[str, object]) -> None:
        x1c, y1c, x2c, y2c = container["xyxy"]
        x1i, y1i, x2i, y2i = inner["xyxy"]

        container["xyxy"] = (
            min(x1c, x1i),
            min(y1c, y1i),
            max(x2c, x2i),
            max(y2c, y2i),
        )

        container_mask = container.get("mask")
        inner_mask = inner.get("mask")
        if isinstance(container_mask, np.ndarray) and isinstance(inner_mask, np.ndarray):
            container["mask"] = np.logical_or(container_mask > 0, inner_mask > 0).astype(np.uint8)
        elif not isinstance(container_mask, np.ndarray) and isinstance(inner_mask, np.ndarray):
            container["mask"] = inner_mask.copy()

    def _suppress_nested_detections(self, detections: List[Dict[str, object]]) -> List[Dict[str, object]]:
        if len(detections) < 2:
            return detections

        merged = [dict(det) for det in detections]
        suppressed_indices: set[int] = set()

        for i, det_i in enumerate(merged):
            if i in suppressed_indices:
                continue

            x1i, y1i, x2i, y2i = det_i["xyxy"]
            area_i = max(1, (x2i - x1i) * (y2i - y1i))

            for j, det_j in enumerate(merged):
                if i == j:
                    continue
                if j in suppressed_indices:
                    continue

                x1j, y1j, x2j, y2j = det_j["xyxy"]

                ix1 = max(x1i, x1j)
                ix2 = min(x2i, x2j)
                iy1 = max(y1i, y1j)
                iy2 = min(y2i, y2j)
                if ix2 <= ix1 or iy2 <= iy1:
                    continue

                inter_area = (ix2 - ix1) * (iy2 - iy1)
                containment = inter_area / area_i

                if containment >= self.nested_containment_threshold:
                    merged_conf = self._merge_confidence(
                        float(det_j["confidence"]),
                        float(det_i["confidence"]),
                    )
                    det_j["confidence"] = merged_conf
                    self._merge_detection_geometry(det_j, det_i)
                    suppressed_indices.add(i)
                    break

        return [det for idx, det in enumerate(merged) if idx not in suppressed_indices]

    def _suppress_high_overlap_conflicts(self, detections: List[Dict[str, object]]) -> List[Dict[str, object]]:
        if len(detections) < 2:
            return detections

        sorted_detections = sorted(detections, key=lambda d: float(d["confidence"]), reverse=True)
        kept: List[Dict[str, object]] = []

        for candidate in sorted_detections:
            x1c, y1c, x2c, y2c = candidate["xyxy"]
            area_c = max(1, (x2c - x1c) * (y2c - y1c))
            skip_candidate = False

            for existing in kept:
                x1e, y1e, x2e, y2e = existing["xyxy"]
                area_e = max(1, (x2e - x1e) * (y2e - y1e))

                ix1 = max(x1c, x1e)
                ix2 = min(x2c, x2e)
                iy1 = max(y1c, y1e)
                iy2 = min(y2c, y2e)
                if ix2 <= ix1 or iy2 <= iy1:
                    continue

                inter_area = (ix2 - ix1) * (iy2 - iy1)
                iou = inter_area / max(1, area_c + area_e - inter_area)
                containment_c = inter_area / area_c

                if iou >= 0.8 or containment_c >= 0.9:
                    skip_candidate = True
                    break

            if not skip_candidate:
                kept.append(candidate)

        return kept

    def _detect_with_yolo_world(self, image) -> List[Dict[str, object]]:
        if self.model is None:
            return []

        result = self.model.predict(
            source=image,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )[0]

        names = result.names if hasattr(result, "names") else {}
        image_height = image.shape[0]
        image_width = image.shape[1]

        detections: List[Dict[str, object]] = []
        for box in result.boxes:
            confidence = float(box.conf[0])
            class_idx = int(box.cls[0])
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]

            reason = yolo_box_filter_reason(x1, y1, x2, y2, image_height, image_width)
            if reason is not None:
                continue

            detections.append(
                {
                    "label": str(names.get(class_idx, "product")),
                    "confidence": confidence,
                    "xyxy": (x1, y1, x2, y2),
                    "mask": None,
                }
            )

        detections = self._suppress_nested_detections(detections)
        return self._suppress_high_overlap_conflicts(detections)

    def _detect_with_contours(self, image) -> List[Dict[str, object]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        thresh = cv2.adaptiveThreshold(
            blurred,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2,
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)

        contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        raw_boxes: List[List[int]] = []
        confidences: List[float] = []
        image_area = image.shape[0] * image.shape[1]
        image_height = image.shape[0]
        image_width = image.shape[1]
        min_area = max(1200, int(image_area * 0.008))
        max_product_area = image_area * 0.15

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            if area < min_area:
                continue

            aspect_ratio = w / max(1, h)
            if aspect_ratio > 5 or aspect_ratio < 0.2:
                continue

            if area > max_product_area:
                continue

            width_ratio = w / image_width
            height_ratio = h / image_height
            if width_ratio > 0.7 or height_ratio > 0.7:
                continue

            reason = yolo_box_filter_reason(
                x,
                y,
                x + w,
                y + h,
                image_height=image_height,
                image_width=image_width,
            )
            if reason is not None:
                continue

            raw_boxes.append([x, y, w, h])
            confidence = min(0.95, 0.4 + (area / max(1, image_area)) * 0.5)
            confidences.append(confidence)

        if len(raw_boxes) == 0:
            return []

        indices = cv2.dnn.NMSBoxes(raw_boxes, confidences, 0.3, self.iou_threshold)
        if len(indices) == 0:
            return []

        detections: List[Dict[str, object]] = []
        for idx in indices.flatten().tolist():
            x, y, w, h = raw_boxes[idx]
            detections.append(
                {
                    "label": "product",
                    "confidence": float(confidences[idx]),
                    "xyxy": (x, y, x + w, y + h),
                    "mask": None,
                }
            )

        return detections

    def detect_products(self, image) -> List[Dict[str, object]]:
        if self.model is not None:
            detections = self._detect_with_yolo_world(image)
            if detections:
                return detections
        return self._detect_with_contours(image)
