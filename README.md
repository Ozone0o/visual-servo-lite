# Luma

**Luma is a lightweight visual intelligence and servo control framework for robots.**

> Give robots eyes and motion.

Luma is a research/development SDK and is not an independent robot safety
layer. Real deployments need a device-level watchdog, validated units, and
hardware-in-the-loop tests.

Luma turns any vision detector into a robot tracking system:

```text
Camera → Detector → Controller → Robot Adapter
```

It is deliberately small, modular and practical. Luma gives a robot developer
one stable loop to build visual-servoing behaviour without coupling the vision
model to a specific robot or transport.

## Install

```bash
pip install luma
```

Optional integrations are kept out of the core install:

```bash
pip install "luma[vision]"   # OpenCV colour detector and camera support
pip install "luma[yolo]"       # Ultralytics YOLO
pip install "luma[apriltag]"   # pupil-apriltags
pip install "luma[dev]"         # tests and linting
```

For local development:

```bash
pip install -e ".[dev]"
```

## Quick start: closed-loop simulation

The simulation uses a synthetic camera, a colour detector, a P controller and
a simulated pan/tilt robot. The robot applies each command to the scene, so
the tracking error visibly decreases without a camera or hardware:

```bash
python -m luma --simulation --steps 30
```

Typical output:

```text
Luma simulation
steps: 30
initial tracking error: 0.8746
final tracking error:   0.0020
converged: True
```

The same demo is available as `examples/simulation_demo.py`.

## Use with a real camera

```bash
luma --camera 0 --detector color --controller smooth
```

The default detector looks for a red HSV region and the default adapter is a
safe in-memory mock. Point the detector/controller at a real robot adapter in
your application, or configure the pipeline in YAML:

```yaml
detector:
  name: color
  lower_h: 0
  upper_h: 20
  min_area: 100

controller:
  name: pid
  kp: 2.0
  ki: 0.05
  kd: 0.1
  max_output: 5.0

pipeline:
  lost_timeout: 1.0
  lost_behavior: stop       # stop or hold
  safety_limits:
    max_yaw: 30.0
    max_pitch: 20.0
    max_command_rate_hz: 30.0
    max_frame_age: 0.5
```

```bash
luma --camera 0 --config examples/configs/luma.yaml \
  --output output/metrics.csv
```

## Architecture

The public package is split by responsibility:

```text
luma/
├── core/          stable Detector / Controller / RobotAdapter contracts
│   ├── pipeline   camera → detector → controller → adapter loop
│   └── registry   small name-based plugin registry
├── detectors/     color, AprilTag, YOLO and CustomDetector
├── controllers/   P, PID and SmoothController
├── adapters/      Mock, PanTilt, ROS2 and CustomRobotAdapter
├── metrics/       per-frame tracking metrics and CSV/JSON export
├── camera.py      OpenCV camera source
└── simulation.py  deterministic camera + robot plant
```

The core data flow is intentionally explicit:

```text
Target (detector output)
        ↓
TrackingError (normalised x/y image error in [-1, 1])
        ↓
MotionCommand (yaw/pitch or linear/angular channels)
        ↓
RobotAdapter.send(command)
```

## Detector plugins

Every detector implements one method:

```python
from luma import Target
from luma.detectors import BaseDetector


class BrightSpotDetector(BaseDetector):
    def detect(self, frame) -> Target:
        # Return pixel coordinates; Luma computes normalised error when needed.
        return Target(x=320, y=240, confidence=1.0)
```

Built-ins:

| Plugin | Use | Extra dependency |
| --- | --- | --- |
| `color` | deterministic HSV blob tracking | none |
| `apriltag` | tag ID tracking | `luma[apriltag]` |
| `yolo` | object detection boxes | `luma[yolo]` |
| `custom` | wrap a function or detector object | none |

Register an application detector by name:

```python
from luma.registry import detector_registry

detector_registry.register("bright-spot", BrightSpotDetector)
detector = detector_registry.create("bright-spot")
```

## Controllers

Controllers consume `TrackingError` and return `MotionCommand`:

```python
from luma.controllers import PIDController
from luma.models import TrackingError

controller = PIDController(kp=2.0, ki=0.05, kd=0.1, max_output=5.0)
command = controller.compute(TrackingError(x=-0.3, y=0.1), dt=1 / 30)
```

Available strategies:

- `PController`: simple, predictable proportional control.
- `PIDController`: integral and derivative terms with output and integral limits.
- `SmoothController`: exponential smoothing around any controller.

The sign convention is consistent across the SDK: a target left of centre
produces positive yaw, which turns the view toward the target.

## Robot adapters

Use a mock during development:

```python
from luma.adapters import MockAdapter

adapter = MockAdapter()
adapter.send(command)
print(adapter.last_command)
```

For hardware, choose `PanTiltAdapter` for a callable/device API,
`ROS2Adapter` for a ROS2 `geometry_msgs/Twist` publisher, or wrap any robot SDK
with `CustomRobotAdapter`. `ROS2Adapter` does not implicitly combine pan/tilt
`yaw`/`pitch` with Twist angular velocities; provide an explicit
`command_to_message` converter when using those channels and document the
unit conversion:

```python
from luma.adapters import CustomRobotAdapter

adapter = CustomRobotAdapter(lambda cmd: robot.set_pan_tilt(cmd.yaw, cmd.pitch))
```

## Build a pipeline in Python

```python
from luma import LumaPipeline
from luma.adapters import MockAdapter
from luma.controllers import SmoothController
from luma.detectors import ColorDetector
from luma.metrics import MetricsRecorder

pipeline = LumaPipeline(
    detector=ColorDetector(lower_v=50),
    controller=SmoothController(kp=8.0, alpha=0.25, max_output=5.0),
    adapter=MockAdapter(),
    metrics=MetricsRecorder("output/metrics.csv"),
)

# In a camera loop:
# result = pipeline.step_and_send(frame)
# print(result.error.magnitude, result.command)
```

`pipeline.step(frame)` computes a command without sending it, which is useful
for replay and testing. `pipeline.run(camera)` sends every command and yields
the full `PipelineResult`. If the target disappears, the default safe behaviour
is to send a zero command after `lost_timeout`; `lost_behavior="hold"` is
available for short occlusions.

Every command passes through a finite-value, pan/tilt-limit, frame-age and
rate gate. Detector/controller exceptions and adapter rejection are converted
to a stop attempt and recorded in command metadata. Hardware integrations
should still provide an independent watchdog and configure limits for their
actual actuator units.

## Examples and tutorial

- `examples/simulation_demo.py` — end-to-end closed-loop simulation.
- `examples/quickstart.py` — the smallest Python pipeline.
- `examples/demo.py` — detector/controller/adapter smoke example.
- `examples/configs/luma.yaml` — detector/controller/pipeline configuration.
- `tutorials/01-first-tracker.md` — build a tracker one component at a time.

Run the test suite from this directory:

```bash
pytest -q
```

## Public API

Luma is the only supported package and command surface. Applications should
import `Target`, `TrackingError`, `MotionCommand`, `LumaPipeline` and
`RobotAdapter` from `luma` and configure the runtime through the canonical
`luma` command.

## License

MIT
