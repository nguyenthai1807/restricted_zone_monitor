"""Giao diện demo Streamlit: chọn video -> kéo thả vùng cấm trên khung hình -> phân tích -> xem cảnh báo."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.processor import DEFAULT_CLASSES, frame_at, probe, process_video
from src.rules import replay, to_pixel_polygon
from src.storage import EventStore, build_html_report
from src.ui import DEFAULT_ZONE, frame_to_data_url, zone_editor

st.set_page_config(page_title="Giám sát khu vực hạn chế", layout="wide")

OUT, ZONES = Path("outputs"), Path("data/zones.json")
(OUT / "uploads").mkdir(parents=True, exist_ok=True)
VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv"}
VN = {"person": "Người", "bicycle": "Xe đạp", "car": "Ô tô", "motorcycle": "Xe máy", "bus": "Xe buýt", "truck": "Xe tải"}
SENS = {"Thấp (ít báo nhầm)": 0.50, "Vừa": 0.35, "Cao (bắt được nhiều hơn)": 0.25}


# ---------------- tiện ích ----------------
def fmt_time(s):
    return f"{int(s // 60):02d}:{s % 60:04.1f}"


def event_label(event_type):
    cls = event_type.replace("_in_restricted_zone", "")
    return "Tụ tập trong vùng cấm" if cls == "crowd" else f"{VN.get(cls, cls)} trong vùng cấm"


def load_zones():
    try:
        return json.loads(ZONES.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_zone(name, points):
    zones = load_zones()
    zones[name] = points
    ZONES.parent.mkdir(parents=True, exist_ok=True)
    ZONES.write_text(json.dumps(zones, indent=2, ensure_ascii=False), encoding="utf-8")


@st.cache_data(show_spinner=False)
def preview(path, mtime, frac):
    frame = frame_at(path, frac)
    return (frame_to_data_url(frame) if frame is not None else None), probe(path)


def sidebar():
    st.sidebar.header("Cài đặt")
    classes = st.sidebar.multiselect("Cảnh báo khi có", list(DEFAULT_CLASSES), ["person"], format_func=VN.get)
    dwell = st.sidebar.slider("Chỉ báo nếu ở trong vùng quá (giây)", 0.0, 10.0, 2.0, 0.5,
                              help="Tránh báo nhầm khi ai đó chỉ lướt qua mép vùng. 0 = báo ngay lập tức.")
    sens = st.sidebar.radio("Độ nhạy phát hiện", list(SENS), index=1,
                            help="Cao hơn thì bắt được nhiều đối tượng hơn nhưng dễ báo nhầm hơn.")
    with st.sidebar.expander("Tuỳ chọn nâng cao"):
        model = st.selectbox("Mô hình YOLO", ["yolov8n.pt", "yolov8s.pt", "yolo11n.pt"],
                             help="n = nhanh nhất, s = chính xác hơn nhưng chậm hơn")
        stride = st.select_slider("Tăng tốc: xử lý 1 trong N khung hình", [1, 2, 3, 5], 1)
        imgsz = st.select_slider("Kích thước ảnh vào mô hình", [320, 480, 640, 960], 640)
        anchor = st.radio("Điểm kiểm tra trong vùng", ["center", "bottom"], horizontal=True,
                          format_func=lambda x: "Tâm khung" if x == "center" else "Chân (đáy khung)")
        crowd = st.number_input("Báo tụ tập khi từ N người (0 = tắt)", 0, 50, 0)
    return dict(classes=classes, dwell=dwell, conf=SENS[sens], model=model, stride=stride,
                imgsz=imgsz, anchor=anchor, crowd=int(crowd))


# ---------------- tab giám sát ----------------
def pick_video():
    samples = sorted(p for d in ("normal", "event", "test") for p in Path("data", d).glob("*.*")
                     if p.suffix.lower() in VIDEO_EXT)
    source = st.radio("Nguồn video", ["Chọn từ thư mục data", "Tải video lên"], horizontal=True,
                      index=0 if samples else 1, label_visibility="collapsed")
    if source == "Tải video lên":
        up = st.file_uploader("Tải video lên", type=[e.strip(".") for e in VIDEO_EXT],
                              label_visibility="collapsed")
        if up is None:
            st.caption("Hãy tải lên một video (mp4, avi, mov, mkv).")
            return None
        path = OUT / "uploads" / up.name
        if not path.exists() or path.stat().st_size != up.size:
            path.write_bytes(up.getbuffer())
        return path
    if not samples:
        st.caption("Thư mục data/ chưa có video. Hãy chép video vào data/normal, data/event hoặc data/test, hoặc chọn 'Tải video lên'.")
        return None
    return st.selectbox("Video", samples, label_visibility="collapsed",
                        format_func=lambda p: f"{p.parent.name} / {p.name}")


def monitor_tab(cfg, store):
    """Bố cục 2 cột, không cần cuộn: trái = khung kéo thả / kết quả, phải = mọi nút điều khiển.
    Cột phải được vẽ trước (về mã) vì cột trái cần video, khung hình và kết quả mà cột phải tạo ra."""
    left, right = st.columns([3, 2], gap="large")
    zones = st.session_state.setdefault("zones", {})

    with right:
        st.markdown("**① Video**")
        video_path = pick_video()
        if video_path is None:
            with left:
                st.info("Chọn hoặc tải một video ở bên phải để bắt đầu.")
            return
        vkey = video_path.name

        st.markdown("**② Vùng cấm**")
        frac = st.slider("Khung hình để đặt vùng", 0, 100, 30, format="%d%%",
                         help="Kéo để xem người, xe đi qua đâu rồi đặt vùng. Vùng đã đặt không bị mất khi đổi khung hình.")
        data_url, info = preview(str(video_path), video_path.stat().st_mtime, frac / 100)
        if data_url is None:
            st.error("Không đọc được video này.")
            return
        saved = load_zones().get(vkey)
        points = zones.get(vkey) or saved or DEFAULT_ZONE
        b1, b2 = st.columns(2)
        if b1.button("Lưu vùng"):
            save_zone(vkey, zones.get(vkey) or points)
            st.toast("Đã lưu vào data/zones.json (evaluate.py sẽ dùng lại)")
        b2.caption(f"{info['width']}x{info['height']} · {info['duration']:.0f}s"
                   + (" · đã nạp vùng đã lưu" if saved and not zones.get(vkey) else ""))

        st.markdown("**③ Phân tích**")
        who = ", ".join(VN.get(c, c) for c in cfg["classes"]) or "(chưa chọn đối tượng)"
        st.caption(f"Báo khi: {who} ở trong vùng quá {cfg['dwell']:g} giây")
        if st.button("Chạy phân tích", type="primary", disabled=not cfg["classes"]):
            bar = st.progress(0.0, text="Đang xử lý...")
            poly_px = to_pixel_polygon(zones.get(vkey) or points, info["width"], info["height"])
            res = process_video(
                video_path, poly_px, out_path=str(OUT / f"{video_path.stem}_annotated.mp4"), store=store,
                model_path=cfg["model"], conf=cfg["conf"], imgsz=cfg["imgsz"], dwell=cfg["dwell"],
                alert_classes=cfg["classes"], crowd_min=cfg["crowd"], anchor=cfg["anchor"],
                vid_stride=cfg["stride"],
                progress=lambda f, n: bar.progress(f, text=f"Đang xử lý... khung {n}"))
            bar.empty()
            res.update(poly_px=poly_px, video_key=vkey, cfg=dict(cfg))
            st.session_state["result"] = res
            st.session_state["view"] = "Kết quả"   # tự chuyển sang xem kết quả

        res = st.session_state.get("result")
        has_result = bool(res and res.get("video_key") == vkey)
        if has_result:
            result_summary(res, store)

    with left:
        if has_result:
            if st.session_state.get("view") not in ("Vùng cấm", "Kết quả"):
                st.session_state["view"] = "Kết quả"
            view = st.radio("Xem", ["Vùng cấm", "Kết quả"], horizontal=True, key="view",
                            label_visibility="collapsed")
        else:
            st.session_state["view"] = "Vùng cấm"
            view = "Vùng cấm"
        if view == "Kết quả":
            result_view(res, store)
        else:
            val = zone_editor(data_url, points, token=vkey, key=f"zone_{vkey}")
            if val:
                zones[vkey] = val


def result_summary(res, store):
    """Cột phải: kết luận ngắn, nút tải, số liệu phụ."""
    ev = res["events"]
    if ev:
        st.error(f"Phát hiện {len(ev)} cảnh báo xâm nhập. Cảnh báo đầu tiên lúc {fmt_time(ev[0].ts)}.")
    else:
        st.success(f"Không có cảnh báo: không đối tượng nào ở trong vùng cấm quá {res['cfg']['dwell']:g} giây.")
    rows = list(reversed(store.list(res["run_id"])))
    if rows:
        csv_path = store.export_csv(OUT / "events_export.csv", res["run_id"])
        d1, d2 = st.columns(2)
        d1.download_button("Tải CSV", Path(csv_path).read_bytes(), "su_kien.csv", "text/csv")
        d2.download_button("Tải báo cáo", build_html_report(rows).encode("utf-8"),
                           "bao_cao_su_kien.html", "text/html")
    with st.expander("So sánh với báo ngay (N = 0)"):
        kw = dict(alert_classes=res["cfg"]["classes"], anchor=res["cfg"]["anchor"], crowd_min=res["cfg"]["crowd"])
        table = []
        for n in sorted({0.0, 1.0, res["cfg"]["dwell"], 3.0, 5.0}):
            e, stt = replay(res["log"], res["poly_px"], dwell_seconds=n, **kw)
            table.append({"Chờ (giây)": n, "Số cảnh báo": len(e),
                          "Khung có đối tượng trong vùng": stt["frames_with_object_in_zone"]})
        st.dataframe(pd.DataFrame(table))
        st.caption("Cột cuối là số lần sẽ báo nếu cảnh báo từng khung hình, không chờ liên tục.")
    with st.expander("Thông số kỹ thuật"):
        st.metric("FPS (chỉ suy luận)", f"{res['fps_infer']:.1f}")
        st.metric("FPS (toàn pipeline)", f"{res['fps_e2e']:.1f}")
        st.metric("ms mỗi khung", f"{res['infer_ms']:.0f}")


def result_view(res, store):
    """Cột trái: video đã chú thích + ảnh từng cảnh báo."""
    if res["out_path"] and Path(res["out_path"]).exists():
        st.video(res["out_path"])
        st.caption("Khung xanh: bình thường · cam: đang trong vùng cấm · đỏ: đã cảnh báo")
    rows = list(reversed(store.list(res["run_id"])))
    if rows:
        cols = st.columns(3)
        for i, r in enumerate(rows):
            if r["snapshot"] and Path(r["snapshot"]).exists():
                cols[i % 3].image(r["snapshot"], caption=f"{fmt_time(r['video_time'])} · {event_label(r['event_type'])} · ID {r['track_id']}")


# ---------------- tab lịch sử ----------------
def history_tab(store):
    rows = store.list()
    if not rows:
        st.info("Chưa có cảnh báo nào.")
    else:
        df = pd.DataFrame(rows).drop(columns=["snapshot", "run_id"])
        df["event_type"] = df["event_type"].map(event_label)
        st.dataframe(df)
        st.download_button("Tải toàn bộ lịch sử (HTML)", build_html_report(rows, "Lịch sử cảnh báo").encode("utf-8"),
                           "lich_su_canh_bao.html", "text/html")
    if st.button("Xoá toàn bộ lịch sử"):
        store.clear()
        st.rerun()


# ---------------- main ----------------
store = EventStore()
st.markdown("### Giám sát khu vực hạn chế")
settings = sidebar()
st.sidebar.caption("Hệ thống chỉ hỗ trợ cảnh báo, không thay thế nhân sự an ninh.")
tab1, tab2 = st.tabs(["Giám sát", "Lịch sử cảnh báo"])
with tab1:
    monitor_tab(settings, store)
with tab2:
    history_tab(store)
