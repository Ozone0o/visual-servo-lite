"""Command-line entry points for camera and simulation workflows."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from luma.camera import OpenCVCamera
from luma.config import build_components, load_config
from luma.core.pipeline import LumaPipeline
from luma.metrics import MetricsRecorder
from luma.simulation import run_simulation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="luma",
        description="Luma: Give robots eyes and motion.",
    )
    parser.add_argument("--config", help="YAML configuration file")
    parser.add_argument("--camera", default="0", help="OpenCV camera index or video path")
    parser.add_argument("--detector", help="override detector plugin name")
    parser.add_argument("--controller", help="override controller plugin name")
    parser.add_argument("--output", default="output/metrics.csv", help="metrics CSV path")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--display", action="store_true", help="show the camera window")
    parser.add_argument("--simulation", action="store_true", help="run without a camera or robot")
    parser.add_argument("--steps", type=int, default=30, help="simulation steps")
    return parser


def _camera_source(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    if args.simulation:
        return main_simulation(["--steps", str(args.steps)])

    config = load_config(args.config)
    if args.detector:
        config.setdefault("detector", {})["name"] = args.detector
    if args.controller:
        config.setdefault("controller", {})["name"] = args.controller
    detector, controller, adapter = build_components(config)
    metrics = MetricsRecorder(Path(args.output))
    pipeline_config = config.get("pipeline", {})
    pipeline = LumaPipeline(
        detector,
        controller,
        adapter,
        metrics=metrics,
        **pipeline_config,
    )

    camera = OpenCVCamera(_camera_source(args.camera))
    try:
        for result in pipeline.run(camera, max_steps=args.max_frames):
            if args.display:
                import cv2

                cv2.imshow("Luma", camera.last_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            logging.getLogger(__name__).debug(
                "error=(%.3f, %.3f) command=(%.3f, %.3f)",
                result.error.x,
                result.error.y,
                result.command.yaw,
                result.command.pitch,
            )
    except KeyboardInterrupt:
        logging.info("Stopping Luma")
    finally:
        camera.release()
        if args.display:
            import cv2

            cv2.destroyAllWindows()
        pipeline.shutdown()
    return 0


def main_simulation(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="luma-sim",
        description="Run the Luma closed-loop simulation",
    )
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--initial-ex", type=float, default=-0.75)
    parser.add_argument("--initial-ey", type=float, default=0.45)
    parser.add_argument("--plant-gain", type=float, default=0.08)
    args = parser.parse_args(argv)
    report = run_simulation(
        steps=args.steps,
        initial_error_x=args.initial_ex,
        initial_error_y=args.initial_ey,
        plant_gain=args.plant_gain,
    )
    print("Luma simulation")
    print(f"steps: {len(report.errors)}")
    print(f"initial tracking error: {report.initial_error:.4f}")
    print(f"final tracking error:   {report.final_error:.4f}")
    print(f"converged: {report.converged}")
    return 0 if report.converged else 1

if __name__ == "__main__":
    raise SystemExit(main())
