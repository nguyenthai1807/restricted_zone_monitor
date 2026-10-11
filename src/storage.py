"""Lưu lịch sử cảnh báo vào SQLite + ảnh khung hình; xuất CSV / báo cáo HTML."""
from __future__ import annotations

import base64
import csv
import html
import sqlite3
import time
from pathlib import Path

import cv2

SCHEMA = """CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, video TEXT, video_time REAL,
    created_at TEXT, event_type TEXT, track_id INTEGER, cls TEXT, conf REAL,
    dwell REAL, snapshot TEXT)"""
FIELDS = ["id", "run_id", "video", "video_time", "created_at", "event_type",
          "track_id", "cls", "conf", "dwell", "snapshot"]


class EventStore:
    def __init__(self, db_path="outputs/events.db", snap_dir="outputs/snapshots"):
        self.db_path, self.snap_dir = Path(db_path), Path(snap_dir)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.snap_dir.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute(SCHEMA)

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, run_id, video, event, frame=None):
        snap = ""
        if frame is not None:
            snap = str(self.snap_dir / f"{run_id}_t{event.ts:07.2f}_id{event.track_id}.jpg")
            cv2.imwrite(snap, frame)
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO events(run_id,video,video_time,created_at,event_type,track_id,cls,conf,dwell,snapshot)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (run_id, video, round(event.ts, 2), time.strftime("%Y-%m-%d %H:%M:%S"),
                 event.event_type, event.track_id, event.cls, round(event.conf, 3),
                 round(event.dwell, 2), snap))
            return cur.lastrowid

    def list(self, run_id=None):
        q, args = "SELECT * FROM events", ()
        if run_id:
            q, args = q + " WHERE run_id=?", (run_id,)
        with self._conn() as c:
            return [dict(r) for r in c.execute(q + " ORDER BY id DESC", args)]

    def export_csv(self, path, run_id=None):
        rows = self.list(run_id)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        return path

    def clear(self):
        with self._conn() as c:
            c.execute("DELETE FROM events")


def build_html_report(rows, title="Báo cáo sự kiện", notes=()):
    """Báo cáo HTML một file (ảnh nhúng base64) để tải về."""
    parts = [f"<html><head><meta charset='utf-8'><title>{html.escape(title)}</title>"
             "<style>body{font-family:sans-serif;max-width:900px;margin:2rem auto}"
             "td,th{border:1px solid #ccc;padding:4px 8px}table{border-collapse:collapse}"
             "img{max-width:360px}</style></head><body>",
             f"<h1>{html.escape(title)}</h1>"]
    parts += [f"<p>{html.escape(n)}</p>" for n in notes]
    parts.append("<table><tr><th>#</th><th>Giây</th><th>Sự kiện</th><th>ID</th><th>Dwell (s)</th><th>Ảnh</th></tr>")
    for i, r in enumerate(rows, 1):
        img = ""
        if r.get("snapshot") and Path(r["snapshot"]).exists():
            b64 = base64.b64encode(Path(r["snapshot"]).read_bytes()).decode()
            img = f"<img src='data:image/jpeg;base64,{b64}'>"
        parts.append(f"<tr><td>{i}</td><td>{r['video_time']}</td><td>{html.escape(r['event_type'])}</td>"
                     f"<td>{r['track_id']}</td><td>{r['dwell']}</td><td>{img}</td></tr>")
    parts.append("</table><p><i>Hệ thống chỉ hỗ trợ cảnh báo, không thay thế nhân sự an ninh.</i></p></body></html>")
    return "".join(parts)
