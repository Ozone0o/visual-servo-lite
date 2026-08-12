# visual-servo-lite

这个项目可以让一个二维云台/机器人头根据摄像头自动跟踪目标。

核心流程：**Camera → Detector → Controller → Pan/Tilt Command**

项目重点不是 Demo，而是提供**清晰的模块结构**和**可替换的组件**：
- 替换检测器：`detectors/`
- 替换控制器：`controllers/`
- 替换机器人适配器：`adapters/`

不绑定任何具体机器人厂商。Webcam + Mock 即可运行。

---

## 安装

```bash
# 核心依赖
pip install -e .

# 可选：YOLO 检测器（默认不安装）
pip install -e ".[yolo]"

# 开发依赖
pip install -e ".[dev]"
```

## 快速开始

### Mock Demo（Webcam）

```bash
python -m visual_servo_lite.cli --camera 0
```

按 `q` 或 `Ctrl+C` 退出。指标自动保存到 `output/metrics.csv`。

### 使用自定义配置

```bash
python -m visual_servo_lite.cli --camera 0 --config examples/configs/default.yaml
```

## ROS2 用法

```bash
# 编译
cd ros2/visual_servo_lite_node
source /opt/ros/rolling/setup.bash
colcon build && source install/setup.bash

# 运行（需要摄像头节点发布 /camera/image_raw）
ros2 run visual_servo_lite_node visual_servo_lite_node
```

发布的指令通过 `/pantilt_command`（Joy 消息）输出。

## 配置说明

所有参数在 `examples/configs/default.yaml` 中配置。

### 修改增益

```yaml
controller:
  yaw_gain: 2.0       # 增大 → 反应更激进
  pitch_gain: 0.8     # 减小 → 垂直方向更平稳
```

增益过大可能导致抖动，过小则跟踪迟缓。建议从 1.0 开始微调。

### 修改死区

```yaml
controller:
  dead_zone: 0.1      # 增大 → 更稳定，但中心精度降低
```

死区内不发送指令，减少云台频繁微调。

### 查看实验指标

退出后查看 `output/metrics.summary.txt`：

```
total_frames: 3600
visible_frames: 3450
lost_count: 150
visible_ratio: 0.9583
mean_tracking_error: 0.052341
avg_command_rate: 29.80 Hz
```

CSV 文件 `output/metrics.csv` 包含每帧数据，可直接用 Python/Matlab 画图。

## 替换组件

### 替换 Detector

在 `detectors/` 下新建文件，继承 `BaseDetector`：

```python
from visual_servo_lite.detectors.base import BaseDetector
from visual_servo_lite.models import Detection

class MyDetector(BaseDetector):
    def detect(self, frame):
        # 返回 Detection 实例
        return Detection(target_x=..., target_y=..., visible=True, confidence=...)
```

然后在 `cli.py` 中替换：

```python
detector = MyDetector()
```

### 替换 Controller

在 `controllers/` 下新建文件，继承 `BaseController`：

```python
from visual_servo_lite.controllers.base import BaseController
from visual_servo_lite.models import Command, Detection

class MyController(BaseController):
    def compute(self, detection, last_command):
        # 返回 Command 实例
        return Command(yaw=..., pitch=...)
```

然后在 `cli.py` 中替换。

### 连接自己的机器人

**通常不需要改 Detector 和 Controller，只需要新增一个 Adapter。**

在 `adapters/` 下新建文件，继承 `BaseAdapter`：

```python
from visual_servo_lite.adapters.base import BaseAdapter
from visual_servo_lite.models import Command

class MyRobotAdapter(BaseAdapter):
    def send(self, cmd: Command) -> bool:
        # 将 cmd.yaw, cmd.pitch 发送给你的机器人
        return True
```

然后在 `cli.py` 中替换：

```python
adapter = MyRobotAdapter()
```

如果你通过 ROS2 通信，可以参考 `ros2/visual_servo_lite_node/` 中的 `Ros2Adapter`。

## 修改核心逻辑

| 文件 | 用途 |
|------|------|
| `detectors/` | 新增/修改检测器 |
| `controllers/` | 新增/修改控制器 |
| `adapters/` | 新增/修改机器人适配器 |
| `pipeline.py` | 修改主循环逻辑 |
| `metrics.py` | 修改指标记录 |
| `config.py` | 修改默认配置项 |

## 测试

```bash
pytest tests/ -v
```

测试覆盖：
- 目标在中心 / 左 / 右 / 上 / 下
- 死区行为
- 输出限幅
- EMA 滤波
- 目标丢失
- 指令安全范围

## 模块结构

```
visual-servo-lite/
├── src/visual_servo_lite/
│   ├── models.py          # 数据模型
│   ├── pipeline.py        # 主循环管线
│   ├── config.py          # 配置加载
│   ├── metrics.py         # 指标记录
│   ├── filters.py         # 滤波工具
│   ├── detectors/         # 检测器
│   │   ├── base.py
│   │   └── color.py
│   ├── controllers/       # 控制器
│   │   ├── base.py
│   │   └── p_controller.py
│   └── adapters/          # 机器人适配器
│       ├── base.py
│       └── mock.py
├── ros2/                  # ROS2 包装节点
├── examples/configs/      # 配置示例
├── tests/                 # 单元测试
├── pyproject.toml
└── README.md
```

## 开源协议

MIT
