"""视觉伺服核心数据模型."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# 检测结果
# ---------------------------------------------------------------------------

@dataclass
class Detection:
    """单次目标检测结果.

    坐标以图像左上角为原点，单位：像素.
    """

    timestamp: float = field(default_factory=time.time)
    target_x: float = 0.0          # 目标中心 x 像素坐标
    target_y: float = 0.0          # 目标中心 y 像素坐标
    confidence: float = 0.0        # 检测置信度 [0, 1]
    visible: bool = True           # 是否检测到目标
    width: float = 0.0             # 目标宽度（可选）
    height: float = 0.0            # 目标高度（可选）

    # ——— 归一化误差（由 pipeline 填充）——————————————
    ex: float = 0.0                # 归一化 x 误差 [-1, 1]
    ey: float = 0.0                # 归一化 y 误差 [-1, 1]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "target_x": self.target_x,
            "target_y": self.target_y,
            "confidence": self.confidence,
            "visible": self.visible,
            "ex": self.ex,
            "ey": self.ey,
        }


# ---------------------------------------------------------------------------
# 控制指令
# ---------------------------------------------------------------------------

@dataclass
class Command:
    """发送给执行机构的控制指令."""

    timestamp: float = field(default_factory=time.time)
    yaw: float = 0.0               # 水平角度（度）
    pitch: float = 0.0             # 垂直角度（度）


# ---------------------------------------------------------------------------
# 云台配置
# ---------------------------------------------------------------------------

@dataclass
class PanTiltConfig:
    """云台硬件参数."""

    max_yaw: float = 90.0          # 水平最大角度（度）
    max_pitch: float = 45.0        # 垂直最大角度（度）
    min_yaw: float = -90.0
    min_pitch: float = -45.0
    max_cmd_rate: float = 30.0     # 最大指令频率 (Hz)


# ---------------------------------------------------------------------------
# 控制器配置
# ---------------------------------------------------------------------------

@dataclass
class ControllerConfig:
    """控制器参数，全部通过 YAML 配置."""

    # ——— 增益 ————————————————————————————————
    yaw_gain: float = 1.0          # 水平方向增益
    pitch_gain: float = 1.0        # 垂直方向增益

    # ——— 死区（归一化误差）——————————————
    dead_zone: float = 0.05        # 死区阈值 [-1, 1]

    # ——— EMA 滤波 ———————————————————————
    ema_alpha: float = 0.3         # EMA 平滑系数 (0, 1]

    # ——— 限幅 ———————————————————————————————
    max_single_cmd_yaw: float = 5.0      # 单次指令最大 yaw 变化（度）
    max_single_cmd_pitch: float = 5.0    # 单次指令最大 pitch 变化（度）

    # ——— 频率限制 ———————————————————————
    command_rate: float = 30.0     # 指令发布频率 (Hz)


# ---------------------------------------------------------------------------
# 目标丢失状态
# ---------------------------------------------------------------------------

class TargetState(Enum):
    """目标跟踪状态."""

    TRACKING = auto()   # 正常跟踪
    SHORT_LOST = auto() # 短暂丢失，保持上一帧
    LOST = auto()       # 长时间丢失，进入丢失状态


@dataclass
class LostConfig:
    """目标丢失检测参数."""

    short_lost_timeout: float = 1.0    # 短暂丢失超时（秒）
    long_lost_timeout: float = 3.0     # 长时间丢失超时（秒）
