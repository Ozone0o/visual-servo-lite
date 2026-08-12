"""ROS2 包装节点.

负责:
- 订阅摄像头图像
- 调用 ServoPipeline
- 发布云台控制指令
"""

from __future__ import annotations

import logging
import signal
import sys

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image, Joy
from std_msgs.msg import Float32

from visual_servo_lite.adapters.base import BaseAdapter
from visual_servo_lite.adapters.mock import MockPanTiltAdapter
from visual_servo_lite.config import build_configs, load_config
from visual_servo_lite.controllers.p_controller import DeadZonePController
from visual_servo_lite.detectors.color import ColorDetector
from visual_servo_lite.metrics import MetricsRecorder
from visual_servo_lite.models import Command
from visual_servo_lite.pipeline import ServoPipeline


class Ros2Adapter(BaseAdapter):
    """ROS2 输出适配器：通过 Joy 消息发送指令.

    用户可替换为自定义 Topic 或硬件驱动.
    """

    def __init__(self, node: Node, topic: str = "/pantilt_command") -> None:
        self.node = node
        self.publisher = node.create_publisher(Joy, topic, 10)
        self._topic = topic
        logging.getLogger(__name__).info("Ros2Adapter 初始化: topic=%s", topic)

    def send(self, cmd: Command) -> bool:
        msg = Joy()
        msg.linear.x = cmd.yaw
        msg.linear.y = cmd.pitch
        msg.linear.z = 0.0
        msg.angular.x = 0.0
        msg.angular.y = 0.0
        msg.angular.z = 0.0
        self.publisher.publish(msg)
        return True


class VisualServoNode(Node):
    """视觉伺服 ROS2 节点.

    订阅 /camera/image_raw，发布 /pantilt_command.
    """

    def __init__(
        self,
        config_path: str | None = None,
        camera_topic: str = "/camera/image_raw",
        output_topic: str = "/pantilt_command",
        use_ros_adapter: bool = True,
    ) -> None:
        super().__init__("visual_servo_node")

        # 加载配置
        cfg = load_config(config_path)
        pt_cfg, ctl_cfg, lost_cfg = build_configs(cfg)

        # 核心模块
        self.detector = ColorDetector()
        self.adapter: BaseAdapter
        if use_ros_adapter:
            self.adapter = Ros2Adapter(self, topic=output_topic)
        else:
            self.adapter = MockPanTiltAdapter()

        self.metrics = MetricsRecorder()
        self.controller = DeadZonePController(config=ctl_cfg, pan_tilt=pt_cfg)

        self.pipeline = ServoPipeline(
            detector=self.detector,
            controller=self.controller,
            adapter=self.adapter,
            metrics=self.metrics,
            lost_cfg=lost_cfg,
        )

        # 桥接
        self.bridge = CvBridge()

        # 订阅图像
        self.image_sub = self.create_subscription(
            Image, camera_topic, self._image_callback, 10
        )

        self.get_logger().info("VisualServoNode 启动")

    def _image_callback(self, msg: Image) -> None:
        """图像回调：转换为 numpy 数组并调用 pipeline."""
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as e:
            self.get_logger().error("图像转换失败: %s", e)
            return

        cmd = self.pipeline.step(frame)
        self.adapter.send(cmd)

    def shutdown(self) -> None:
        self.pipeline.shutdown()


def main(args: list[str] | None = None) -> None:
    """节点入口."""
    rclpy.init(args=args)
    node = VisualServoNode()

    # 处理中断
    def signal_handler(sig, frame):
        node.get_logger().info("收到中断信号，关闭节点")
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()

    signal.signal(signal.SIGINT, signal_handler)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
