"""Pipeline: OpenCV đọc video -> YOLO (Ultralytics) -> ByteTrack -> luật vùng cấm -> video chú thích."""
from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from .rules import ZoneMonitor

DEFAULT_CLASSES = ("person", "car", "motorcycle", "bus", "truck")
COLOR_NORMAL, COLOR_IN_ZONE, COLOR_ALERT = (80, 200, 80), (0, 165, 255), (0, 0, 255)
_MODELS: dict = {}


def get_model(path):
    if path not in _MODELS:
        from ultralytics import YOLO  # import trễ để các phần khác dùng được khi chưa cài
        _MODELS[path] = YOLO(path)
    return _MODELS[path]


def probe(video_path):
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    info = dict(fps=fps, width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    info["duration"] = info["frames"] / fps if fps else 0.0
    cap.release()
    return info


def first_frame(video_path):
    cap = cv2.VideoCapture(str(video_path))
    ok, frame = cap.read()
    cap.release()
    return frame if ok else None


def iter_detections(video_path, model_path="yolov8n.pt", conf=0.35, imgsz=640,
                    classes=DEFAULT_CLASSES, vid_stride=1, tracker="bytetrack.yaml", device=None):
    """Sinh (idx, t_giây, frame, dets, infer_ms). dets = list[dict(track_id, cls, conf, box)]."""
    model = get_model(model_path)
    try:
        model.predictor = None  # reset bộ theo dõi giữa các video
    except Exception:
        pass
    wanted = [i for i, n in model.names.items() if n in classes] if hasattr(model, "names") else None
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    idx = -1
    while cap.grab():
        idx += 1
        if idx % vid_stride:
            continue
        ok, frame = cap.retrieve()
        if not ok:
            break
        t0 = time.perf_counter()
        res = model.track(frame, persist=True, tracker=tracker, conf=conf, imgsz=imgsz,
                          classes=wanted, verbose=False, device=device)[0]
        infer_ms = (time.perf_counter() - t0) * 1000
        dets, boxes = [], res.boxes
        if boxes is not None and len(boxes):
            xyxy = boxes.xyxy.cpu().numpy()
            confs = boxes.conf.cpu().numpy()
            clss = boxes.cls.cpu().numpy().astype(int)
            ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [-1] * len(xyxy)
            for b, c, k, i in zip(xyxy, confs, clss, ids):
                dets.append(dict(track_id=int(i), cls=res.names[int(k)], conf=float(c),
                                 box=tuple(float(v) for v in b)))
        yield idx, idx / fps, frame, dets, infer_ms
    cap.release()


def draw_zone(frame, polygon, alert=False):
    out = frame.copy()
    pts = np.asarray(polygon, dtype=np.int32).reshape(-1, 1, 2)
    overlay = out.copy()
    cv2.fillPoly(overlay, [pts], COLOR_ALERT if alert else COLOR_IN_ZONE)
    out = cv2.addWeighted(overlay, 0.22, out, 0.78, 0)
    cv2.polylines(out, [pts], True, COLOR_ALERT if alert else COLOR_IN_ZONE, 2)
    return out


def annotate(frame, polygon, dets, in_zone, alerting, t, banner=False):
    out = draw_zone(frame, polygon, alert=bool(alerting))
    for d in dets:
        x1, y1, x2, y2 = map(int, d["box"])
        tid = d["track_id"]
        color = COLOR_ALERT if tid in alerting else COLOR_IN_ZONE if tid in in_zone else COLOR_NORMAL
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{d['cls']} #{tid} {d['conf']:.2f}"
        cv2.putText(out, label, (x1, max(14, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    cv2.putText(out, f"t={t:6.2f}s", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    if banner:
        cv2.rectangle(out, (0, out.shape[0] - 38), (out.shape[1], out.shape[0]), COLOR_ALERT, -1)
        cv2.putText(out, "CANH BAO: XAM NHAP VUNG CAM", (10, out.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return out


def _ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def to_h264(src, dst):
    """Chuyển sang H.264 để trình duyệt phát được; nếu không có ffmpeg thì giữ nguyên file gốc."""
    exe = _ffmpeg_exe()
    if not exe:
        return src
    r = subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(src), "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst)])
    return dst if r.returncode == 0 and Path(dst).exists() else src


def process_video(video_path, polygon_px, *, out_path=None, store=None, run_id=None,
                  model_path="yolov8n.pt", conf=0.35, imgsz=640, dwell=2.0,
                  alert_classes=("person",), track_classes=DEFAULT_CLASSES, crowd_min=0,
                  anchor="center", vid_stride=1, tracker="bytetrack.yaml", device=None,
                  progress=None):
    """Chạy toàn bộ pipeline. Trả về dict tóm tắt (kèm log phát hiện để so sánh các giá trị N)."""
    run_id = run_id or uuid.uuid4().hex[:8]
    info = probe(video_path)
    monitor = ZoneMonitor(polygon_px, dwell, alert_classes, anchor, crowd_min=crowd_min)
    writer, raw_path, events, log = None, None, [], []
    infer_total, n, t_start, banner_until = 0.0, 0, time.perf_counter(), -1.0
    total = max(1, info["frames"] // vid_stride)

    for idx, t, frame, dets, infer_ms in iter_detections(
            video_path, model_path, conf, imgsz, track_classes, vid_stride, tracker, device):
        new_events, in_zone, alerting = monitor.update(t, dets)
        events.extend(new_events)
        log.append((t, dets))
        if new_events:
            banner_until = t + 2.0
        vis = annotate(frame, polygon_px, dets, in_zone, alerting, t, banner=t <= banner_until)
        for ev in new_events:
            if store is not None:
                store.add(run_id, Path(video_path).name, ev, vis)
        if out_path:
            if writer is None:
                raw_path = str(Path(out_path).with_suffix(".raw.mp4"))
                writer = cv2.VideoWriter(raw_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                         info["fps"] / vid_stride, (vis.shape[1], vis.shape[0]))
            writer.write(vis)
        infer_total += infer_ms
        n += 1
        if progress and n % 5 == 0:
            progress(min(1.0, n / total), n)
    if writer is not None:
        writer.release()
        final = to_h264(raw_path, out_path)
        if final != raw_path:
            Path(raw_path).unlink(missing_ok=True)
        out_path = final
    wall = time.perf_counter() - t_start
    return dict(run_id=run_id, frames=n, duration=info["duration"], events=events, log=log,
                stats=monitor.stats, out_path=out_path,
                infer_ms=infer_total / max(1, n), fps_infer=1000 * n / max(1e-9, infer_total),
                fps_e2e=n / max(1e-9, wall), info=info)
