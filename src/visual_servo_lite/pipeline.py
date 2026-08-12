"""视觉伺服主管线.

串联 Detector → Controller → Adapter，处理目标丢失状态机.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from visual_servo_lite.adapters.base import BaseAdapter
from visual_servo_lite.controllers.base import BaseController
from visual_servo_lite.detectors.base import BaseDetector
from visual_servo_lite.filters import EMAFilter
from visual_servo_lite.metrics import MetricsRecorder
from visual_servo_lite.models import (
    Command,
    ControllerConfig,
    Detection,
    LostConfig,
    PanTiltConfig,
    TargetState,
)

logger = logging.getLogger(__name__)


class ServoPipeline:
    """视觉伺服主循环管线.

    流程:
        frame → Detector → Detection → Controller → Command → Adapter
    """

    def __init__(
        self,
        detector: BaseDetector,
        controller: BaseController,
        adapter: BaseAdapter,
        metrics: MetricsRecorder | None = None,
        lost_cfg: LostConfig | None = None,
    ) -> None:
        """初始化管线.

        Args:
            detector: 目标检测器.
            controller: 控制器.
            adapter: 机器人/云台适配器.
            metrics: 指标记录器，None 则不记录.
            lost_cfg: 目标丢失检测参数.
        """
        self.detector = detector
        self.controller = controller
        self.adapter = adapter
        self.metrics = metrics or MetricsRecorder()
        self.lost_cfg = lost_cfg or LostConfig()

        # 状态机
        self._state = TargetState.TRACKING
        self._last_visible_time: float = time.time()
        self._hold_command: Command | None = None

        # 用于 EMA 平滑丢失时的误差输出
        self._error_ema_x = EMAFilter(alpha=0.5, initial=0.0)
        self._error_ema_y = EMAFilter(alpha=0.5, initial=0.0)

        logger.info(
            "ServoPipeline 初始化: state=%s, lost_cfg=%s",
            self._state, self.lost_cfg,
        )

    def step(self, frame) -> Command:
        """执行一步伺服循环.

        Args:
            frame: 摄像头帧（格式由 Detector 决定）.

        Returns:
            控制指令.
        """
        ts = time.time()

        # 1. 检测
        detection = self.detector.detect(frame)

        # 2. 更新目标丢失状态机
        self._update_lost_state(detection, ts)

        # 3. 控制器计算
        if detection.visible:
            # 目标可见，重置 EMA
            self._error_ema_x.update(detection.ex)
            self._error_ema_y.update(detection.ey)
            detection.ex = self._error_ema_x.value
            detection.ey = self._error_ema_y.value
            cmd = self.controller.compute(detection, self._hold_command)
            self._hold_command = cmd
        else:
            # 目标丢失，根据状态决定行为
            cmd = self._handle_lost(ts)

        # 4. 记录指标
        self.metrics.record(detection, cmd)

        return cmd

    def _update_lost_state(self, detection: Detection, now: float) -> None:
        """更新目标丢失状态机.

        Args:
            detection: 当前检测结果.
            now: 当前时间戳.
        """
        if detection.visible:
            if self._state != TargetState.TRACKING:
                logger.info("目标重新捕获 -> TRACKING")
            self._state = TargetState.TRACKING
            self._last_visible_time = now
        else:
            elapsed = now - self._last_visible_time
            if elapsed > self.lost_cfg.long_lost_timeout:
                if self._state != TargetState.LOST:
                    logger.warning("目标长时间丢失 -> LOST")
                self._state = TargetState.LOST
            elif elapsed > self.lost_cfg.short_lost_timeout:
                if self._state != TargetState.SHORT_LOST:
                    logger.info("目标短暂丢失 -> SHORT_LOST")
                self._state = TargetState.SHORT_LOST

    def _handle_lost(self, now: float) -> Command:
        """目标丢失时的控制策略.

        Args:
            now: 当前时间戳.

        Returns:
            保持上一指令或零指令.
        """
        if self._state == TargetState.SHORT_LOST:
            # 短暂丢失，保持上一指令
            logger.debug("短暂丢失，保持上一指令")
            return self._hold_command or Command()
        # LOST 状态，发送零指令停止运动
        logger.debug("目标丢失，发送零指令")
        return Command()

    def run(self, frame_generator) -> None:
        """运行主循环.

        Args:
            frame_generator: 产生帧的迭代器（如 OpenCV VideoCapture）.
        """
        logger.info("开始主循环")
        for frame in frame_generator:
            cmd = self.step(frame)
            self.adapter.send(cmd)

    def shutdown(self) -> None:
        """关闭管线，保存指标."""
        logger.info("关闭管线")
        self.metrics.save_csv()
        self.adapter.close()
        summary = self.metrics.get_summary()
        logger.info("实验摘要: %s", summary)
