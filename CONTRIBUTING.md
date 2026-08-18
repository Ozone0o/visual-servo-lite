# Contributing to Luma

Thanks for helping improve Luma. Keep perception, control, transport, and the
safety gate independently testable. Any change that can affect a robot command
must include a test for the safe and rejected paths.

## Development

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/pytest -q
.venv/bin/ruff check src tests examples ros2
```

CI covers Python 3.10 through 3.13. The simulation and offline tests must not
require ROS 2. ROS 2 nodes require a sourced ROS 2 environment and a matching
`rclpy`/`colcon` toolchain. Hardware use additionally requires an independent
safety supervisor.

Update the README or `CHANGELOG.md` for public API, configuration, or command
changes. Do not commit caches, wheels, `__pycache__`, ROS `build/`, `install/`,
or `log/` output. Pull requests should include a reproducible simulation or
fixture for new detector/controller/adapter behavior.
