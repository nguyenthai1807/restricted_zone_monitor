"""Giao diện demo Streamlit: tải video, chỉnh vùng cấm, chạy phân tích, xem cảnh báo, tải báo cáo."""
from pathlib import Path

import cv2
import pandas as pd
import streamlit as st

from src.processor import DEFAULT_CLASSES, draw_zone, first_frame, probe, process_video
from src.rules import replay, to_pixel_polygon
from src.storage import EventStore, build_html_report

st.set_page_config(page_title="Giám sát khu vực hạn chế", layout="wide")
OUT = Path("outputs")
(OUT / "uploads").mkdir(parents=True, exist_ok=True)
store = EventStore()

st.title("Giám sát khu vực hạn chế bằng Computer Vision")
st.caption("YOLO + ByteTrack + luật vùng cấm. Hệ thống hỗ trợ cảnh báo, không thay thế nhân sự an ninh.")

# ---------------- Sidebar: tham số ----------------
with st.sidebar:
    st.header("Tham số")
    model_path = st.selectbox("Mô hình YOLO", ["yolov8n.pt", "yolov8s.pt", "yolo11n.pt"],
                              help="n = nhanh nhất, s = chính xác hơn nhưng chậm hơn")
    conf = st.slider("Ngưỡng confidence", 0.10, 0.90, 0.35, 0.05)
    dwell = st.slider("Chỉ cảnh báo nếu ở trong vùng liên tục (giây)", 0.0, 10.0, 2.0, 0.5,
                      help="0 = cảnh báo ngay khi chạm vùng (dễ báo giả)")
    alert_classes = st.multiselect("Đối tượng bị cấm trong vùng", list(DEFAULT_CLASSES), ["person"])
    crowd_min = st.number_input("Cảnh báo tụ tập khi >= N người (0 = tắt)", 0, 50, 0)
    anchor = st.radio("Điểm kiểm tra trong vùng", ["center", "bottom"], horizontal=True,
                      format_func=lambda x: "Tâm bbox" if x == "center" else "Chân (đáy bbox)")
    stride = st.select_slider("Bỏ qua khung hình (tăng tốc)", [1, 2, 3, 5], 1,
                              format_func=lambda x: f"xử lý 1/{x} khung")
    imgsz = st.select_slider("Kích thước ảnh vào mô hình", [320, 480, 640, 960], 640)

tab_run, tab_events = st.tabs(["1. Video & vùng cấm", "2. Lịch sử cảnh báo"])

# ---------------- Tab 1 ----------------
with tab_run:
    c1, c2 = st.columns([3, 2])
    with c1:
        up = st.file_uploader("Tải video lên", type=["mp4", "avi", "mov", "mkv"])
        samples = sorted(p for d in ("normal", "event", "test") for p in Path("data", d).glob("*.*")
                         if p.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"})
        pick = st.selectbox("...hoặc chọn video trong thư mục data/", ["(không chọn)"] + [str(p) for p in samples])
        video_path = None
        if up is not None:
            video_path = OUT / "uploads" / up.name
            video_path.write_bytes(up.getbuffer())
        elif pick != "(không chọn)":
            video_path = Path(pick)

    if video_path is None:
        st.info("Hãy tải một video (hoặc đặt video vào data/normal, data/event, data/test).")
        st.stop()

    info = probe(video_path)
    frame0 = first_frame(video_path)
    if frame0 is None:
        st.error("Không đọc được video này.")
        st.stop()

    with c2:
        st.markdown("**Vùng cấm** (toạ độ % theo chiều rộng/cao khung hình, thêm/xoá dòng để đổi hình dạng)")
        default_pts = pd.DataFrame({"x_%": [25.0, 75.0, 75.0, 25.0], "y_%": [40.0, 40.0, 90.0, 90.0]})
        pts = st.data_editor(default_pts, num_rows="dynamic", key="zone_pts", use_container_width=True)
        pts = pts.dropna()
        st.caption(f"Video: {info['width']}x{info['height']}, {info['fps']:.1f} FPS, {info['duration']:.1f}s")

    valid = len(pts) >= 3
    poly_norm = [(min(max(x, 0), 100) / 100, min(max(y, 0), 100) / 100) for x, y in pts[["x_%", "y_%"]].values] if valid else []
    poly_px = to_pixel_polygon(poly_norm, info["width"], info["height"]) if valid else None
    with c1:
        if valid:
            st.image(cv2.cvtColor(draw_zone(frame0, poly_px), cv2.COLOR_BGR2RGB),
                     caption="Xem trước vùng cấm trên khung hình đầu tiên", use_container_width=True)
        else:
            st.warning("Vùng cấm cần ít nhất 3 điểm.")

    if st.button("Chạy phân tích", type="primary", disabled=not valid or not alert_classes):
        bar = st.progress(0.0, text="Đang xử lý...")
        out_video = OUT / f"{Path(video_path).stem}_annotated.mp4"
        res = process_video(
            video_path, poly_px, out_path=str(out_video), store=store, model_path=model_path,
            conf=conf, imgsz=imgsz, dwell=dwell, alert_classes=alert_classes,
            crowd_min=crowd_min, anchor=anchor, vid_stride=stride,
            progress=lambda f, n: bar.progress(f, text=f"Đang xử lý... khung {n}"))
        bar.empty()
        res["poly_px"] = poly_px
        res["video_name"] = Path(video_path).name
        res["cfg"] = dict(alert_classes=alert_classes, anchor=anchor, crowd_min=crowd_min, dwell=dwell)
        st.session_state["result"] = res

    res = st.session_state.get("result")
    if res:
        st.subheader("Kết quả")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Số cảnh báo", len(res["events"]))
        m2.metric("FPS (chỉ suy luận)", f"{res['fps_infer']:.1f}")
        m3.metric("FPS (toàn pipeline)", f"{res['fps_e2e']:.1f}")
        m4.metric("ms / khung", f"{res['infer_ms']:.0f}")
        if res["out_path"] and Path(res["out_path"]).exists():
            st.video(res["out_path"])
        if res["events"]:
            st.dataframe(pd.DataFrame([dict(giay=round(e.ts, 2), su_kien=e.event_type, id=e.track_id,
                                            dwell_s=round(e.dwell, 2), conf=round(e.conf, 2))
                                       for e in res["events"]]), use_container_width=True)
        else:
            st.success("Không có cảnh báo nào trong video này.")

        st.subheader("So sánh trước/sau cơ chế 'cảnh báo sau N giây'")
        kw = dict(alert_classes=res["cfg"]["alert_classes"], anchor=res["cfg"]["anchor"],
                  crowd_min=res["cfg"]["crowd_min"])
        rows = []
        for n in sorted({0.0, 1.0, res["cfg"]["dwell"], 3.0, 5.0}):
            ev, stt = replay(res["log"], res["poly_px"], dwell_seconds=n, **kw)
            rows.append({"N (giây)": n, "Số cảnh báo": len(ev),
                         "Số khung có đối tượng trong vùng (báo từng khung)": stt["frames_with_object_in_zone"]})
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.caption("N = 0 là cảnh báo ngay khi chạm vùng; số khung ở cột cuối là số lần sẽ báo nếu cảnh báo ở từng khung hình.")

# ---------------- Tab 2 ----------------
with tab_events:
    res = st.session_state.get("result")
    scope = st.radio("Phạm vi", ["Lần chạy gần nhất", "Toàn bộ lịch sử"], horizontal=True)
    rows = store.list(res["run_id"] if res and scope == "Lần chạy gần nhất" else None)
    if not rows:
        st.info("Chưa có cảnh báo nào.")
    else:
        st.dataframe(pd.DataFrame(rows).drop(columns=["snapshot"]), use_container_width=True)
        cols = st.columns(3)
        for i, r in enumerate(rows[:12]):
            if r["snapshot"] and Path(r["snapshot"]).exists():
                cols[i % 3].image(r["snapshot"], caption=f"t={r['video_time']}s · {r['event_type']} · ID {r['track_id']}")
        csv_path = store.export_csv(OUT / "events_export.csv", res["run_id"] if res and scope == "Lần chạy gần nhất" else None)
        d1, d2 = st.columns(2)
        d1.download_button("Tải CSV", Path(csv_path).read_bytes(), "events.csv", "text/csv")
        d2.download_button("Tải báo cáo HTML", build_html_report(rows).encode("utf-8"), "bao_cao_su_kien.html", "text/html")
    if st.button("Xoá toàn bộ lịch sử"):
        store.clear()
        st.rerun()
