"""ROS 2 node that connects camera images to the Luma pipeline."""

from __future__ import annotations

import signal
import time

import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Image

from luma.adapters import BaseAdapter, ROS2Adapter
from luma.config import build_components, load_config
from luma.core.pipeline import LumaPipeline
from luma.metrics import MetricsRecorder
from luma.models import MotionCommand


class LumaNode(Node):
    """Subscribe to camera images and publish safe Luma motion commands."""

    def __init__(
        self,
        config_path: str | None = None,
        camera_topic: str = "/camera/image_raw",
        output_topic: str = "/pantilt_command",
    ) -> None:
        super().__init__("luma")

        config = load_config(config_path)
        component_config = dict(config)
        component_config["adapter"] = {"name": "mock"}
        self.detector, self.controller, _ = build_components(component_config)

        self.adapter: BaseAdapter = ROS2Adapter(
            self,
            topic=output_topic,
            command_to_message=self._command_to_twist,
        )
        self.metrics = MetricsRecorder()
        pipeline_config = dict(config.get("pipeline", {}))
        safety_limits = pipeline_config.pop("safety_limits", None)
        self.pipeline = LumaPipeline(
            detector=self.detector,
            controller=self.controller,
            adapter=self.adapter,
            metrics=self.metrics,
            lost_timeout=float(pipeline_config.pop("lost_timeout", 1.0)),
            lost_behavior=pipeline_config.pop("lost_behavior", "stop"),
            short_lost_timeout=pipeline_config.pop("short_lost_timeout", None),
            long_lost_timeout=pipeline_config.pop("long_lost_timeout", None),
            safety_limits=safety_limits,
            **pipeline_config,
        )

        self.bridge = CvBridge()
        self._shutdown = False
        self.image_sub = self.create_subscription(Image, camera_topic, self._image_callback, 10)
        self.get_logger().info("Luma ROS 2 node started")

    def _image_callback(self, msg: Image) -> None:
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except Exception as exc:
            self.get_logger().error("image conversion failed: %s", exc)
            self._send_stop(f"image_conversion_error:{type(exc).__name__}")
            return
        timestamp, frame_age = _message_timestamp(msg, self.get_clock().now().nanoseconds)
        self.pipeline.step_and_send(frame, timestamp=timestamp, frame_age=frame_age)

    @staticmethod
    def _command_to_twist(command: MotionCommand) -> Twist:
        """Explicitly map Luma pan/tilt channels to Twist angular axes."""

        if command.angular_y or command.angular_z:
            raise ValueError("use either pan/tilt yaw/pitch or angular_y/angular_z, not both")
        message = Twist()
        message.linear.x = command.linear_x
        message.linear.y = command.linear_y
        message.linear.z = command.linear_z
        message.angular.x = command.angular_x
        message.angular.y = command.pitch
        message.angular.z = command.yaw
        return message

    def _send_stop(self, reason: str) -> None:
        try:
            self.adapter.send(MotionCommand.stop(metadata={"safety_fault": reason}))
        except Exception as exc:
            self.get_logger().error("unable to publish stop command: %s", exc)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self.pipeline.shutdown()


def _message_timestamp(msg: Image, now_nanoseconds: int) -> tuple[float, float | None]:
    """Return a ROS stamp and age measured in the same ROS clock domain."""

    stamp = getattr(getattr(msg, "header", None), "stamp", None)
    seconds = getattr(stamp, "sec", None)
    nanoseconds = getattr(stamp, "nanosec", None)
    if seconds is None or nanoseconds is None:
        return time.time(), None
    timestamp = float(seconds) + float(nanoseconds) * 1e-9
    if timestamp <= 0 or now_nanoseconds <= 0:
        return time.time(), None
    now = float(now_nanoseconds) * 1e-9
    return timestamp, max(0.0, now - timestamp)


def main(args: list[str] | None = None) -> None:
    """Run the Luma ROS 2 node until shutdown."""

    rclpy.init(args=args)
    node = LumaNode()

    def signal_handler(_sig: int, _frame: object) -> None:
        node.get_logger().info("Shutting down Luma ROS 2 node")
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    signal.signal(signal.SIGINT, signal_handler)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
