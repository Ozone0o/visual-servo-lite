"""指标记录与 CSV 导出.

记录每帧的跟踪误差、丢失次数、可见比率等.
"""

from __future__ import annotations

import csv
import logging
import time
from pathlib import Path

from visual_servo_lite.models import Command, Detection, TargetState

logger = logging.getLogger(__name__)


class MetricsRecorder:
    """实验指标记录器.

    支持内存记录和 CSV 导出.
    """

    def __init__(self, output_path: str | Path | None = None) -> None:
        """初始化记录器.

        Args:
            output_path: CSV 输出路径，None 则不保存文件.
        """
        self._output_path = Path(output_path) if output_path else None
        self._rows: list[dict] = []

        # 累计统计
        self._total_frames: int = 0
        self._visible_frames: int = 0
        self._lost_count: int = 0
        self._sum_ex_sq: float = 0.0
        self._sum_ey_sq: float = 0.0
        self._sum_cmd_mag: float = 0.0

        logger.info("MetricsRecorder 初始化, 输出路径=%s", self._output_path)

    def record(self, detection: Detection, cmd: Command) -> None:
        """记录一帧数据.

        Args:
            detection: 当前检测结果.
            cmd: 当前控制指令.
        """
        self._total_frames += 1
        if detection.visible:
            self._visible_frames += 1
            self._sum_ex_sq += detection.ex ** 2
            self._sum_ey_sq += detection.ey ** 2
        else:
            self._lost_count += 1

        cmd_mag = abs(cmd.yaw) + abs(cmd.pitch)
        self._sum_cmd_mag += cmd_mag

        # 单帧记录
        self._rows.append({
            "frame": self._total_frames,
            "timestamp": detection.timestamp,
            "ex": detection.ex,
            "ey": detection.ey,
            "visible": detection.visible,
            "yaw": cmd.yaw,
            "pitch": cmd.pitch,
            "cmd_mag": cmd_mag,
        })

    @property
    def mean_tracking_error(self) -> float:
        """均方根跟踪误差（仅可见帧）."""
        if self._visible_frames == 0:
            return 0.0
        return float(
            ((self._sum_ex_sq + self._sum_ey_sq) / self._visible_frames) ** 0.5
        )

    @property
    def target_visible_ratio(self) -> float:
        """目标可见比率."""
        if self._total_frames == 0:
            return 0.0
        return self._visible_frames / self._total_frames

    @property
    def lost_count(self) -> int:
        return self._lost_count

    @property
    def command_rate(self) -> float:
        """平均指令频率（基于时间和帧数估算）."""
        if len(self._rows) < 2:
            return 0.0
        duration = self._rows[-1]["timestamp"] - self._rows[0]["timestamp"]
        if duration <= 0:
            return 0.0
        return (len(self._rows) - 1) / duration

    def save_csv(self) -> None:
        """保存指标到 CSV 文件."""
        if not self._output_path:
            logger.info("未配置输出路径，跳过 CSV 保存")
            return

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "frame", "timestamp", "ex", "ey",
            "visible", "yaw", "pitch", "cmd_mag",
        ]

        with open(self._output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self._rows)

        # 附加摘要
        summary_path = self._output_path.with_suffix(".summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(f"total_frames: {self._total_frames}\n")
            f.write(f"visible_frames: {self._visible_frames}\n")
            f.write(f"lost_count: {self._lost_count}\n")
            f.write(f"visible_ratio: {self.target_visible_ratio:.4f}\n")
            f.write(f"mean_tracking_error: {self.mean_tracking_error:.6f}\n")
            f.write(f"avg_command_rate: {self.command_rate:.2f} Hz\n")

        logger.info("指标已保存到: %s", self._output_path)

    def get_summary(self) -> dict:
        """获取摘要字典."""
        return {
            "total_frames": self._total_frames,
            "visible_frames": self._visible_frames,
            "lost_count": self._lost_count,
            "visible_ratio": round(self.target_visible_ratio, 4),
            "mean_tracking_error": round(self.mean_tracking_error, 6),
            "command_rate": round(self.command_rate, 2),
        }
