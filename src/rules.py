"""Luật an ninh: vùng cấm (polygon) + thời gian lưu lại tối thiểu (dwell time)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


def to_pixel_polygon(norm_points, width, height):
    """Đổi toạ độ chuẩn hoá (0-1) sang pixel."""
    return np.array([[x * width, y * height] for x, y in norm_points], dtype=np.float32)


def anchor_point(box, mode="center"):
    """Điểm đại diện của bounding box: 'center' (tâm) hoặc 'bottom' (chân đối tượng)."""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, y2 if mode == "bottom" else (y1 + y2) / 2)


def inside(polygon, point):
    contour = np.asarray(polygon, dtype=np.float32).reshape(-1, 1, 2)
    return cv2.pointPolygonTest(contour, (float(point[0]), float(point[1])), False) >= 0


@dataclass
class Event:
    ts: float            # thời điểm trong video (giây)
    event_type: str      # vd: person_in_restricted_zone, crowd_in_restricted_zone
    track_id: int
    cls: str
    conf: float
    dwell: float         # đã ở trong vùng bao lâu khi phát cảnh báo (giây)
    box: tuple


class ZoneMonitor:
    """Phát cảnh báo khi một đối tượng (có track ID) ở trong vùng cấm liên tục >= dwell_seconds.

    - grace_seconds: cho phép mất dấu/ra khỏi vùng ngắn mà không reset bộ đếm.
    - crowd_min > 0: thêm cảnh báo tụ tập khi >= crowd_min người cùng ở trong vùng liên tục dwell_seconds.
    - dwell_seconds = 0: cảnh báo ngay khung hình đầu tiên (dùng làm mốc "trước khi có cơ chế N giây").
    """

    def __init__(self, polygon, dwell_seconds=2.0, alert_classes=("person",),
                 anchor="center", grace_seconds=1.0, crowd_min=0):
        self.polygon = np.asarray(polygon, dtype=np.float32)
        self.dwell = float(dwell_seconds)
        self.alert_classes = set(alert_classes)
        self.anchor = anchor
        self.grace = float(grace_seconds)
        self.crowd_min = int(crowd_min)
        self._tracks: dict[int, dict] = {}
        self._crowd_since = None
        self._crowd_alerted = False
        self.stats = {"frames": 0, "frames_with_object_in_zone": 0}

    def update(self, ts, detections):
        """detections: list[dict(track_id, cls, conf, box)]. Trả về (events, ids_in_zone, ids_alerting)."""
        events, in_zone = [], set()
        self.stats["frames"] += 1
        for d in detections:
            tid = d.get("track_id")
            if tid is None or tid < 0 or d["cls"] not in self.alert_classes:
                continue
            if not inside(self.polygon, anchor_point(d["box"], self.anchor)):
                continue
            in_zone.add(tid)
            st = self._tracks.get(tid)
            if st is None or ts - st["last"] > self.grace:
                st = {"first": ts, "last": ts, "alerted": False, "cls": d["cls"]}
                self._tracks[tid] = st
            else:
                st["last"] = ts
            dwell = ts - st["first"]
            if not st["alerted"] and dwell >= self.dwell:
                st["alerted"] = True
                events.append(Event(ts, f"{d['cls']}_in_restricted_zone", tid, d["cls"],
                                    float(d["conf"]), dwell, tuple(d["box"])))
        if in_zone:
            self.stats["frames_with_object_in_zone"] += 1

        if self.crowd_min > 0:
            n_persons = sum(1 for t in in_zone if self._tracks[t]["cls"] == "person")
            if n_persons >= self.crowd_min:
                if self._crowd_since is None:
                    self._crowd_since = ts
                if not self._crowd_alerted and ts - self._crowd_since >= self.dwell:
                    self._crowd_alerted = True
                    events.append(Event(ts, "crowd_in_restricted_zone", -1, "person", 1.0,
                                        ts - self._crowd_since, (0, 0, 0, 0)))
            else:
                self._crowd_since, self._crowd_alerted = None, False

        alerting = {t for t in in_zone if self._tracks[t]["alerted"]}
        return events, in_zone, alerting


def replay(log, polygon, **kwargs):
    """Chạy lại luật trên chuỗi phát hiện đã lưu [(t, dets), ...] -> (events, stats). Dùng để so sánh các giá trị N."""
    mon = ZoneMonitor(polygon, **kwargs)
    events = []
    for t, dets in log:
        ev, _, _ = mon.update(t, dets)
        events.extend(ev)
    return events, mon.stats
