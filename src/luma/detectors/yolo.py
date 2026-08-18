"""Optional Ultralytics YOLO detector plugin."""

from __future__ import annotations

from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover - depends on the installation
    np = None

from luma.detectors.base import BaseDetector
from luma.models import Target


class YOLODetector(BaseDetector):
    """Detect the best matching YOLO box in a frame.

    Pass ``model_instance`` in tests or when the application already owns a
    loaded model; otherwise Ultralytics is imported lazily on first use.
    """

    def __init__(
        self,
        model: str = "yolo11n.pt",
        *,
        class_name: str | None = None,
        class_id: int | None = None,
        confidence: float = 0.25,
        device: str | None = None,
        model_instance: Any | None = None,
    ) -> None:
        self.model_name = model
        self.class_name = class_name
        self.class_id = class_id
        self.confidence = confidence
        self.device = device
        self._model = model_instance

    def _backend(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "YOLODetector requires 'ultralytics'. Install with: pip install luma[yolo]"
            ) from exc
        self._model = YOLO(self.model_name)
        return self._model

    def detect(self, frame: np.ndarray) -> Target:
        if np is None:
            raise ImportError("YOLODetector requires NumPy")
        height, width = frame.shape[:2]
        kwargs: dict[str, Any] = {"verbose": False, "conf": self.confidence}
        if self.device is not None:
            kwargs["device"] = self.device
        results = self._backend().predict(frame, **kwargs)
        if not results:
            return Target.empty()
        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return Target.empty()
        coordinates = self._array(getattr(boxes, "xyxy", []))
        scores = self._array(getattr(boxes, "conf", []))
        classes = self._array(getattr(boxes, "cls", []))
        if coordinates.size == 0:
            return Target.empty()
        names = getattr(result, "names", getattr(self._backend(), "names", {}))
        candidates: list[tuple[int, float, str | None]] = []
        for index, box in enumerate(coordinates.reshape(-1, 4)):
            score = float(scores.reshape(-1)[index]) if scores.size else 1.0
            class_index = int(classes.reshape(-1)[index]) if classes.size else None
            label = self._label(names, class_index)
            if self.class_id is not None and class_index != self.class_id:
                continue
            if self.class_name is not None and label != self.class_name:
                continue
            candidates.append((index, score, label))
        if not candidates:
            return Target.empty()
        index, score, label = max(candidates, key=lambda item: item[1])
        x1, y1, x2, y2 = map(float, coordinates.reshape(-1, 4)[index])
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        ex, ey = self.normalize_error(cx, cy, width, height)
        return Target(
            x=cx,
            y=cy,
            width=max(0.0, x2 - x1),
            height=max(0.0, y2 - y1),
            confidence=score,
            label=label,
            ex=ex,
            ey=ey,
            metadata={
                "class_id": (
                    self._array(getattr(boxes, "cls", []))[index] if classes.size else None
                )
            },
        )

    @staticmethod
    def _array(value: Any) -> np.ndarray:
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            value = value.numpy()
        return np.asarray(value)

    @staticmethod
    def _label(names: Any, class_id: int | None) -> str | None:
        if class_id is None:
            return None
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and class_id < len(names):
            return str(names[class_id])
        return str(class_id)


YOLO = YOLODetector


__all__ = ["YOLO", "YOLODetector"]
