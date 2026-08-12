"""命令行入口."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import cv2

from visual_servo_lite.adapters.mock import MockPanTiltAdapter
from visual_servo_lite.config import build_configs, load_config
from visual_servo_lite.controllers.p_controller import DeadZonePController
from visual_servo_lite.detectors.color import ColorDetector
from visual_servo_lite.metrics import MetricsRecorder
from visual_servo_lite.pipeline import ServoPipeline


def main_mock() -> None:
    """Mock Demo 入口: 使用摄像头 + 模拟云台."""
    parser = argparse.ArgumentParser(description="visual-servo-lite Mock Demo")
    parser.add_argument("--config", type=str, default=None, help="YAML 配置文件路径")
    parser.add_argument("--camera", type=int, default=0, help="摄像头编号")
    parser.add_argument(
        "--output-dir", type=str, default="./output", help="CSV 指标输出目录"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # 加载配置
    cfg = load_config(args.config)
    pt_cfg, ctl_cfg, lost_cfg = build_configs(cfg)

    # 初始化模块
    detector = ColorDetector()
    adapter = MockPanTiltAdapter()
    metrics = MetricsRecorder(output_path=Path(args.output_dir) / "metrics.csv")
    controller = DeadZonePController(config=ctl_cfg, pan_tilt=pt_cfg)

    # 管线
    pipeline = ServoPipeline(
        detector=detector,
        controller=controller,
        adapter=adapter,
        metrics=metrics,
        lost_cfg=lost_cfg,
    )

    # 打开摄像头
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        logging.error("无法打开摄像头 %d", args.camera)
        sys.exit(1)

    logger = logging.getLogger(__name__)
    logger.info("Mock Demo 启动, 按 q 退出")

    try:
        pipeline.run(cap)
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        pipeline.shutdown()


if __name__ == "__main__":
    main_mock()
