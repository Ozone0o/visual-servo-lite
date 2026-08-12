---
name: visual-servo-lite - project overview
description: 轻量级二维视觉伺服项目，面向 pan-tilt 云台，解耦 detector/controller/adapter
type: project
---

- 项目名 visual-servo-lite：二维云台/机器人头自动视觉跟踪
- 核心设计：Detector → Controller → OutputAdapter 完全解耦
- 默认 Color Detector（OpenCV），可选 YOLO 插件
- Controller 支持 P / P+DeadZone / P+EMA，预留 PID/Kalman
- ROS2 Node 仅负责消息转换，核心算法可独立测试
- Metrics 导出 CSV，记录 tracking error / lost count / visible ratio
