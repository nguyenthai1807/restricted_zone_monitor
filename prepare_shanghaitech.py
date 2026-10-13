"""Chọn vài video ShanghaiTech Campus, ghép ảnh -> mp4, chia vào data/normal, data/event, data/test.

  .venv\\Scripts\\python.exe prepare_shanghaitech.py --src "C:\\...\\shanghaitech"

- normal: video training (cảnh bình thường), mỗi cảnh 1 video.
- event : video testing có bất thường (dùng để chỉnh tham số).
- test  : video testing có bất thường + vài video không bất thường, KHÔNG dùng để chỉnh tham số.
- data/ground_truth.csv: khoảng thời gian bất thường lấy từ test_frame_mask (chỉ là ứng viên, xem ghi chú cuối).
"""
import argparse
import csv
import random
import shutil
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from src.processor import to_h264

VID_EXT = {".avi", ".mp4", ".mov", ".mkv"}


def spread_by_scene(names, n, rng):
    """Chọn n tên, luân phiên giữa các cảnh (tiền tố trước dấu '_') để đa dạng."""
    groups = defaultdict(list)
    for nm in sorted(names):
        groups[nm.split("_")[0]].append(nm)
    for g in groups.values():
        rng.shuffle(g)
    out, keys = [], sorted(groups)
    while len(out) < n and any(groups.values()):
        for k in keys:
            if groups[k] and len(out) < n:
                out.append(groups[k].pop())
    return out


def frames_to_mp4(frames_dir, dst, fps, max_frames):
    files = sorted(p for p in Path(frames_dir).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})[:max_frames]
    if not files:
        return False
    first = cv2.imread(str(files[0]))
    h, w = first.shape[:2]
    raw = Path(dst).with_suffix(".raw.mp4")
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for f in files:
        img = cv2.imread(str(f))
        if img is not None:
            vw.write(img if img.shape[:2] == (h, w) else cv2.resize(img, (w, h)))
    vw.release()
    final = to_h264(raw, dst)
    if str(final) != str(raw):
        raw.unlink(missing_ok=True)
    else:
        shutil.move(str(raw), str(dst))
    return True


def mask_intervals(mask, fps):
    m = np.asarray(mask).astype(int).ravel() > 0
    out, start = [], None
    for i, v in enumerate(m):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append((start / fps, i / fps)); start = None
    if start is not None:
        out.append((start / fps, len(m) / fps))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="thư mục shanghaitech (chứa training, testing)")
    ap.add_argument("--dst", default="data")
    ap.add_argument("--n-normal", type=int, default=4)
    ap.add_argument("--n-event", type=int, default=4)
    ap.add_argument("--n-test", type=int, default=4, help="số video bất thường dành cho kiểm thử")
    ap.add_argument("--n-test-normal", type=int, default=2, help="số video không bất thường đưa vào test")
    ap.add_argument("--fps", type=float, default=0, help="0 = đọc từ video training")
    ap.add_argument("--max-frames", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    src, dst, rng = Path(a.src), Path(a.dst), random.Random(a.seed)
    for d in ("normal", "event", "test"):
        (dst / d).mkdir(parents=True, exist_ok=True)

    train = {p.stem: p for p in (src / "training" / "videos").iterdir() if p.suffix.lower() in VID_EXT}
    fps = a.fps
    if not fps and train:
        cap = cv2.VideoCapture(str(next(iter(train.values()))))
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cap.release()
    fps = fps or 24.0
    print(f"FPS dùng để đổi khung -> giây: {fps}")

    for nm in spread_by_scene(train, a.n_normal, rng):
        shutil.copy(train[nm], dst / "normal" / train[nm].name)
        print("normal:", train[nm].name)

    frames_root, mask_root = src / "testing" / "frames", src / "testing" / "test_frame_mask"
    anomalous, clean, masks = [], [], {}
    for d in sorted(p for p in frames_root.iterdir() if p.is_dir()):
        mp = mask_root / f"{d.name}.npy"
        if not mp.exists():
            continue
        masks[d.name] = np.load(mp)
        (anomalous if masks[d.name].max() > 0 else clean).append(d.name)
    print(f"testing: {len(anomalous)} video có bất thường, {len(clean)} video không có")

    picked = spread_by_scene(anomalous, a.n_event + a.n_test, rng)
    plan = [(n, "event") for n in picked[:a.n_event]] + [(n, "test") for n in picked[a.n_event:]]
    plan += [(n, "test") for n in spread_by_scene(clean, a.n_test_normal, rng)]

    rows = []
    for nm, kind in plan:
        out = dst / kind / f"{nm}.mp4"
        if frames_to_mp4(frames_root / nm, out, fps, a.max_frames):
            iv = mask_intervals(masks[nm][:a.max_frames], fps)
            rows += [(out.name, round(s, 2), round(e, 2)) for s, e in iv]
            print(f"{kind}: {out.name}  ({len(iv)} khoảng bất thường)")

    gt = dst / "ground_truth.csv"
    with open(gt, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["video", "start_s", "end_s"]); w.writerows(rows)
    print(f"\nĐã ghi {gt}")
    print("LƯU Ý: nhãn của ShanghaiTech là bất thường CHUNG (chạy, xe đạp, đánh nhau...), không phải 'vào vùng cấm'.\n"
          "Hãy xem từng video, vẽ vùng cấm đúng chỗ sự kiện xảy ra, và sửa start_s/end_s trong ground_truth.csv\n"
          "thành khoảng thời gian đối tượng THỰC SỰ ở trong vùng cấm của bạn.")


if __name__ == "__main__":
    main()
