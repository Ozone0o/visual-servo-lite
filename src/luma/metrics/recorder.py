"""Tracking metrics and CSV/JSON export."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

from luma.models import MotionCommand, Target, TrackingError


class MetricsRecorder:
    """Collect per-frame tracking data with near-zero pipeline overhead."""

    def __init__(self, output_path: str | Path | None = None) -> None:
        self._output_path = Path(output_path) if output_path else None
        self._rows: list[dict[str, Any]] = []
        self._total_frames = 0
        self._visible_frames = 0
        self._lost_count = 0
        self._sum_error_sq = 0.0
        self._sum_command_mag = 0.0

    def record(
        self,
        target: Target,
        command: MotionCommand,
        *,
        state: str | None = None,
    ) -> None:
        """Record one target/command pair."""

        if not isinstance(target, Target):
            raise TypeError("target must be a luma.models.Target")
        if not isinstance(command, MotionCommand):
            raise TypeError("command must be a luma.models.MotionCommand")
        error = target.error if target.visible else TrackingError()
        self._total_frames += 1
        if target.visible:
            self._visible_frames += 1
            self._sum_error_sq += error.x**2 + error.y**2
        else:
            self._lost_count += 1
        self._sum_command_mag += command.magnitude
        self._rows.append(
            {
                "frame": self._total_frames,
                "timestamp": target.timestamp,
                "ex": error.x,
                "ey": error.y,
                "error_magnitude": error.magnitude,
                "visible": target.visible,
                "confidence": target.confidence,
                "label": target.label or "",
                "yaw": command.yaw,
                "pitch": command.pitch,
                "command_magnitude": command.magnitude,
                "state": state or ("tracking" if target.visible else "lost"),
            }
        )

    @property
    def rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    @property
    def total_frames(self) -> int:
        return self._total_frames

    @property
    def visible_frames(self) -> int:
        return self._visible_frames

    @property
    def lost_count(self) -> int:
        return self._lost_count

    @property
    def target_visible_ratio(self) -> float:
        return self._visible_frames / self._total_frames if self._total_frames else 0.0

    @property
    def mean_tracking_error(self) -> float:
        if self._visible_frames == 0:
            return 0.0
        return math.sqrt(self._sum_error_sq / self._visible_frames)

    @property
    def mean_command_magnitude(self) -> float:
        if not self._total_frames:
            return 0.0
        return self._sum_command_mag / self._total_frames

    @property
    def command_rate(self) -> float:
        if len(self._rows) < 2:
            return 0.0
        duration = self._rows[-1]["timestamp"] - self._rows[0]["timestamp"]
        return (len(self._rows) - 1) / duration if duration > 0 else 0.0

    def get_summary(self) -> dict[str, Any]:
        return {
            "total_frames": self._total_frames,
            "visible_frames": self._visible_frames,
            "lost_count": self._lost_count,
            "visible_ratio": round(self.target_visible_ratio, 4),
            "mean_tracking_error": round(self.mean_tracking_error, 6),
            "mean_command_magnitude": round(self.mean_command_magnitude, 6),
            "command_rate": round(self.command_rate, 2),
        }

    def save_csv(self) -> None:
        if self._output_path is None:
            return
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "frame",
            "timestamp",
            "ex",
            "ey",
            "error_magnitude",
            "visible",
            "confidence",
            "label",
            "yaw",
            "pitch",
            "command_magnitude",
            "state",
        ]
        with self._output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(self._rows)
        summary_path = self._output_path.with_suffix(".summary.txt")
        with summary_path.open("w", encoding="utf-8") as handle:
            for key, value in self.get_summary().items():
                handle.write(f"{key}: {value}\n")

    def save_json(self, path: str | Path | None = None) -> Path:
        destination = Path(path) if path else self._output_path
        if destination is None:
            raise ValueError("a JSON output path is required")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(
                {"summary": self.get_summary(), "rows": self._rows},
                indent=2,
            ),
            encoding="utf-8",
        )
        return destination


Metrics = MetricsRecorder


__all__ = ["Metrics", "MetricsRecorder"]
