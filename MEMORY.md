---
name: Luma - project overview
description: Lightweight visual intelligence and servo control SDK for robots
type: project
---

- 项目名 Luma：Give robots eyes and motion
- 核心设计：Camera → Detector → Controller → Robot Adapter
- Detector 插件：Color / AprilTag / YOLO / Custom，统一返回 Target
- Controller 支持 P / PID / Smooth，输入 TrackingError，输出 MotionCommand
- Adapter 支持 Mock / PanTilt / ROS2 / Custom，核心算法独立于硬件
- Metrics 导出 CSV/JSON；Simulation mode 可验证闭环误差收敛
- Luma is the sole public package and command surface
