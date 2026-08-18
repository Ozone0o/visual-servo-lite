# Build your first Luma tracker

Luma keeps the application loop small:

```text
frame → detector.detect(frame) → controller.compute(error) → adapter.send(command)
```

## 1. Pick a detector

Start with the deterministic colour detector while bringing up a camera:

```python
from luma.detectors import ColorDetector

detector = ColorDetector(lower_h=0, upper_h=20, lower_v=80)
```

Every detector returns a `Target`. A target can expose pixel coordinates and
confidence, while Luma converts its centre to a normalised
`TrackingError(x, y)` in `[-1, 1]`.

When the detector is ready, replace it with `AprilTagDetector`, `YOLODetector`
or `CustomDetector` without changing the controller.

## 2. Choose control behaviour

```python
from luma.controllers import SmoothController

controller = SmoothController(kp=8.0, alpha=0.25, max_output=5.0)
```

Use `PController` for predictable bring-up, `PIDController` when steady-state
error matters, and `SmoothController` when the detector is noisy.

## 3. Connect a robot

During development, keep the output safe:

```python
from luma.adapters import MockAdapter

adapter = MockAdapter()
```

When the command shape is validated, wrap the robot SDK:

```python
from luma.adapters import CustomRobotAdapter

adapter = CustomRobotAdapter(
    lambda command: robot.set_pan_tilt(command.yaw, command.pitch)
)
```

## 4. Assemble and run

```python
from luma import LumaPipeline

pipeline = LumaPipeline(detector, controller, adapter)
for frame in camera:
    result = pipeline.step_and_send(frame)
    print(result.error.magnitude)
```

If the target disappears, the default safety behaviour emits a zero command
after `lost_timeout`. Set `lost_behavior="hold"` only when a short occlusion
should preserve the previous motion.

## 5. Measure behaviour

Attach a recorder to the pipeline:

```python
from luma.metrics import MetricsRecorder

metrics = MetricsRecorder("output/metrics.csv")
pipeline = LumaPipeline(detector, controller, adapter, metrics=metrics)
```

Call `pipeline.shutdown()` when the run ends. The recorder writes per-frame
error, visibility, command and state fields plus a summary file.
