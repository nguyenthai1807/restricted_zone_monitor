"""Đánh giá mức sự kiện trên video kiểm thử + so sánh N giây + đo FPS.

  python evaluate.py --videos data/test --zones data/zones.json --gt data/ground_truth.csv --dwell 0 2 3
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from src.processor import iter_detections, probe
from src.rules import replay, to_pixel_polygon

EXT = {".mp4", ".avi", ".mov", ".mkv"}


def load_gt(path):
    gt = defaultdict(list)
    if path and Path(path).exists():
        with open(path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                gt[r["video"]].append((float(r["start_s"]), float(r["end_s"])))
    return gt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--videos", default="data/test")
    ap.add_argument("--zones", default="data/zones.json")
    ap.add_argument("--gt", default="data/ground_truth.csv")
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--dwell", type=float, nargs="+", default=[0, 2])
    ap.add_argument("--tolerance", type=float, default=2.0, help="sai số thời gian khi ghép cảnh báo với sự kiện thật (giây)")
    ap.add_argument("--classes", nargs="+", default=["person"])
    ap.add_argument("--out", default="outputs/eval_results.csv")
    a = ap.parse_args()

    zones, gt = json.loads(Path(a.zones).read_text(encoding="utf-8")), load_gt(a.gt)
    videos = sorted(p for p in Path(a.videos).iterdir() if p.suffix.lower() in EXT)
    assert videos, f"Không có video trong {a.videos}"

    logs, infer_ms, total_hours = {}, [], 0.0
    for v in videos:  # chạy mô hình MỘT lần, sau đó phát lại luật với từng N
        info = probe(v)
        poly = to_pixel_polygon(zones.get(v.name, zones.get("default")), info["width"], info["height"])
        log = []
        for _, t, _, dets, ms in iter_detections(v, a.model, a.conf, a.imgsz):
            log.append((t, dets)); infer_ms.append(ms)
        logs[v.name] = (log, poly)
        total_hours += info["duration"] / 3600
        print(f"đã xử lý {v.name}: {len(log)} khung")

    fps = 1000 / (sum(infer_ms) / len(infer_ms))
    rows = []
    for n in a.dwell:
        n_alerts = tp_alerts = 0
        n_gt = detected = 0
        for name, (log, poly) in logs.items():
            events, _ = replay(log, poly, dwell_seconds=n, alert_classes=a.classes)
            intervals = gt.get(name, [])
            hit = [False] * len(intervals)
            for e in events:
                n_alerts += 1
                match = [i for i, (s, t_end) in enumerate(intervals) if s - a.tolerance <= e.ts <= t_end + a.tolerance]
                if match:
                    tp_alerts += 1
                    for i in match: hit[i] = True
            n_gt += len(intervals); detected += sum(hit)
        fp = n_alerts - tp_alerts
        rows.append({"N_giay": n, "so_canh_bao": n_alerts, "canh_bao_dung": tp_alerts, "canh_bao_sai": fp,
                     "precision": round(tp_alerts / n_alerts, 3) if n_alerts else None,
                     "recall": round(detected / n_gt, 3) if n_gt else None,
                     "canh_bao_sai_moi_gio": round(fp / total_hours, 1) if total_hours else None,
                     "FPS_suy_luan": round(fps, 1)})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print("\n| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]))
    for r in rows:
        print("| " + " | ".join(str(v) for v in r.values()) + " |")
    print(f"\nĐã lưu: {a.out}")


if __name__ == "__main__":
    main()
