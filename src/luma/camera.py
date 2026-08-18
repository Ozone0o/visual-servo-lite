"""Small camera sources used by the CLI and examples."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


class OpenCVCamera:
    """Iterator over frames from an OpenCV camera or video source."""

    def __init__(
        self,
        source: int | str = 0,
        *,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        import cv2

        self.capture = cv2.VideoCapture(source)
        if width is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height is not None:
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError(f"unable to open camera source: {source}")
        self.last_frame: Any | None = None

    def read(self) -> Any:
        ok, frame = self.capture.read()
        if not ok:
            raise StopIteration
        self.last_frame = frame
        return frame

    def __iter__(self) -> Iterator[Any]:
        while True:
            try:
                yield self.read()
            except StopIteration:
                return

    def release(self) -> None:
        self.capture.release()

    close = release

    def __enter__(self) -> OpenCVCamera:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()


__all__ = ["OpenCVCamera"]
