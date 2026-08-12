"""测试指标记录器."""

from __future__ import annotations

from visual_servo_lite.metrics import MetricsRecorder
from visual_servo_lite.models import Command, Detection


class TestMetricsRecorder:
    def test_initial_values(self):
        recorder = MetricsRecorder()
        assert recorder.mean_tracking_error == 0.0
        assert recorder.target_visible_ratio == 0.0
        assert recorder.lost_count == 0

    def test_record_visible_target(self):
        recorder = MetricsRecorder()
        det = Detection(ex=0.1, ey=0.2, visible=True)
        cmd = Command(yaw=1.0, pitch=2.0)
        recorder.record(det, cmd)

        assert recorder.lost_count == 0
        assert recorder.target_visible_ratio == 1.0
        assert recorder._total_frames == 1

    def test_record_lost_target(self):
        recorder = MetricsRecorder()
        det = Detection(visible=False)
        cmd = Command()
        recorder.record(det, cmd)

        assert recorder.lost_count == 1
        assert recorder.target_visible_ratio == 0.0

    def test_mean_tracking_error(self):
        recorder = MetricsRecorder()
        for _ in range(10):
            det = Detection(ex=0.1, ey=0.2, visible=True)
            cmd = Command()
            recorder.record(det, cmd)

        expected = (0.1**2 + 0.2**2) ** 0.5
        assert abs(recorder.mean_tracking_error - expected) < 1e-10

    def test_csv_save(self, tmp_path):
        recorder = MetricsRecorder(output_path=tmp_path / "test.csv")
        det = Detection(ex=0.1, ey=0.1, visible=True)
        cmd = Command(yaw=1.0, pitch=0.0)
        recorder.record(det, cmd)
        recorder.save_csv()

        assert tmp_path.joinpath("test.csv").exists()
        assert tmp_path.joinpath("test.summary.txt").exists()

    def test_summary_dict(self):
        recorder = MetricsRecorder()
        det = Detection(ex=0.05, ey=0.05, visible=True)
        cmd = Command()
        recorder.record(det, cmd)

        summary = recorder.get_summary()
        assert summary["total_frames"] == 1
        assert summary["visible_ratio"] == 1.0
        assert summary["lost_count"] == 0
