"""The smallest useful Luma pipeline.

Run from this directory after ``pip install -e .``:

    python examples/quickstart.py
"""

from __future__ import annotations

import cv2
import numpy as np

from luma import LumaPipeline
from luma.adapters import MockAdapter
from luma.controllers import PController
from luma.detectors import ColorDetector


def main() -> None:
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.circle(frame, (440, 200), 30, (0, 0, 255), -1)

    adapter = MockAdapter()
    pipeline = LumaPipeline(
        detector=ColorDetector(lower_v=50),
        controller=PController(kp=5.0, max_output=5.0),
        adapter=adapter,
    )
    result = pipeline.step_and_send(frame)
    print(f"target error: ({result.error.x:.3f}, {result.error.y:.3f})")
    print(f"motion command: yaw={result.command.yaw:.3f}, pitch={result.command.pitch:.3f}")
    pipeline.shutdown()


if __name__ == "__main__":
    main()
