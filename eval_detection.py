"""Precision/Recall của việc phát hiện người trên tập ảnh có nhãn YOLO (bạn tự gán nhãn ~100-200 khung).

  python eval_detection.py --data data/person.yaml --model yolov8n.pt
data/person.yaml (ví dụ):
  path: data/labeled
  val: images/val
  names: {0: person}
"""
import argparse

from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--data", required=True)
ap.add_argument("--model", default="yolov8n.pt")
ap.add_argument("--conf", type=float, default=0.35)
ap.add_argument("--iou", type=float, default=0.5)
a = ap.parse_args()

r = YOLO(a.model).val(data=a.data, conf=a.conf, iou=a.iou, verbose=False)
p, rc = float(r.box.mp), float(r.box.mr)
print(f"Precision={p:.3f}  Recall={rc:.3f}  F1={2*p*rc/max(1e-9, p+rc):.3f}  mAP50={float(r.box.map50):.3f}")
