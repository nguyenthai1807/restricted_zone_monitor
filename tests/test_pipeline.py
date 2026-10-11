"""Kiểm thử không cần YOLO thật: giả lập ultralytics để kiểm tra luật vùng cấm, dwell time, lưu sự kiện, ghi video."""
import sys
import types
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

W, H, FPS, N = 640, 360, 20, 100


class _A:
    def __init__(self, a): self.a = np.asarray(a)
    def cpu(self): return self
    def numpy(self): return self.a


class _Boxes:
    def __init__(self, xyxy, conf, cls, ids):
        self.xyxy, self.conf, self.cls, self.id = _A(xyxy), _A(conf), _A(cls), _A(ids)
    def __len__(self): return len(self.xyxy.a)


class _Res:
    names = {0: "person", 2: "car"}
    def __init__(self, boxes): self.boxes = boxes


class FakeYOLO:
    """'Phát hiện' ô trắng trên nền đen và gán track_id=1 (giống ByteTrack giữ ID ổn định)."""
    names = {0: "person", 2: "car"}
    def __init__(self, path): self.predictor = None
    def track(self, frame, **kw):
        ys, xs = np.where(frame.min(axis=2) > 250)
        if len(xs) == 0:
            return [_Res(None)]
        box = [xs.min(), ys.min(), xs.max(), ys.max()]
        return [_Res(_Boxes([box], [0.9], [0], [1]))]


def make_video(path):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(N):  # ô trắng đi từ trái sang phải, tâm x: 40 -> 600
        f = np.zeros((H, W, 3), np.uint8)
        cx = int(40 + i * 5.6)
        cv2.rectangle(f, (cx - 15, 150), (cx + 15, 210), (255, 255, 255), -1)
        w.write(f)
    w.release()


def test_pipeline(tmp_path):
    sys.modules["ultralytics"] = types.SimpleNamespace(YOLO=FakeYOLO)
    from src.processor import process_video
    from src.rules import replay, to_pixel_polygon
    from src.storage import EventStore

    video = tmp_path / "walk.mp4"
    make_video(video)
    poly = to_pixel_polygon([(0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.5, 1.0)], W, H)  # nửa phải khung hình
    store = EventStore(tmp_path / "e.db", tmp_path / "snaps")

    res = process_video(video, poly, out_path=str(tmp_path / "out.mp4"), store=store,
                        run_id="t1", dwell=2.0)
    assert res["frames"] == N
    assert len(res["events"]) == 1, res["events"]
    ev = res["events"][0]
    assert ev.event_type == "person_in_restricted_zone" and ev.track_id == 1
    assert 4.3 <= ev.ts <= 4.7, ev.ts          # vào vùng ~2.5s + 2s dwell
    assert Path(res["out_path"]).exists()
    rows = store.list("t1")
    assert len(rows) == 1 and Path(rows[0]["snapshot"]).exists()
    store.export_csv(tmp_path / "e.csv", "t1")

    # So sánh trước/sau cơ chế N giây trên cùng chuỗi phát hiện
    ev0, st0 = replay(res["log"], poly, dwell_seconds=0)
    ev3, _ = replay(res["log"], poly, dwell_seconds=3.0)
    assert len(ev0) == 1 and 2.3 <= ev0[0].ts <= 2.7   # N=0: báo ngay khi chạm vùng
    assert len(ev3) == 0                                # chỉ ở trong vùng ~2.5s < 3s => không báo
    assert st0["frames_with_object_in_zone"] >= 45

    # Vùng không chứa đối tượng => không cảnh báo
    far = to_pixel_polygon([(0.0, 0.8), (0.2, 0.8), (0.2, 1.0), (0.0, 1.0)], W, H)
    assert replay(res["log"], far, dwell_seconds=0)[0] == []


if __name__ == "__main__":
    import tempfile
    test_pipeline(Path(tempfile.mkdtemp()))
    print("OK")
