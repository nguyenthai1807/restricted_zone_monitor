# Giám sát khu vực hạn chế bằng Computer Vision

Pipeline: **OpenCV** đọc video → **YOLO (Ultralytics)** nhận diện người/xe → **ByteTrack** gán ID liên tục → **luật vùng cấm** (polygon + ở lại liên tục N giây) → lưu cảnh báo vào **SQLite** (+ ảnh) → giao diện **Streamlit**.

> Hệ thống chỉ hỗ trợ cảnh báo, không thay thế nhân sự an ninh.

## 1. Cài đặt và chạy

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Lần đầu chạy, Ultralytics tự tải trọng số `yolov8n.pt`. Có GPU NVIDIA thì cài PyTorch bản CUDA để nhanh hơn.

Kiểm tra logic không cần YOLO: `python tests/test_pipeline.py` (hoặc `pytest`).

## 2. Tình huống demo và chuẩn bị video

Tình huống: camera cổng trường / bãi xe / kho hàng; cảnh báo khi người đi vào vùng cấm quá N giây.

```bash
pip install yt-dlp
yt-dlp -f "mp4[height<=720]" -o "data/raw/%(id)s.%(ext)s" "<URL video giám sát công khai>"
# cắt đoạn 10s -> 40s
ffmpeg -ss 10 -i data/raw/abc.mp4 -t 30 -c copy data/normal/abc_normal.mp4
```
Kiểm tra giấy phép/điều khoản của video trước khi dùng. Chia thư mục:

| Thư mục | Nội dung |
|---|---|
| `data/normal/` | người di chuyển hợp lệ, không vào vùng cấm |
| `data/event/` | người bước vào vùng cấm, đỗ xe bất thường, tụ tập |
| `data/test/` | video **riêng để kiểm thử**, không dùng để chỉnh ngưỡng/vùng/N |

Chỉnh `conf`, vùng cấm và N chỉ trên `normal/` + `event/`; chốt cấu hình rồi mới chạy đánh giá trên `test/`.

## 3. Dùng giao diện

1. Tải video (hoặc chọn từ `data/`).
2. Sửa bảng toạ độ vùng cấm (x%, y%); xem trước ngay trên khung hình đầu.
3. Chọn đối tượng cần cảnh báo, N giây, ngưỡng confidence → **Chạy phân tích**.
4. Xem video đã chú thích (xanh = bình thường, cam = trong vùng, đỏ = đã cảnh báo), bảng so sánh N, tab **Lịch sử cảnh báo** để tải CSV / báo cáo HTML.

Điểm kiểm tra mặc định là **tâm bounding box** (đúng yêu cầu); có thể đổi sang **đáy bbox** (chân người) – thường đúng hơn với camera nghiêng.

## 4. Đánh giá

```bash
# a) Mức sự kiện + so sánh N + FPS
python evaluate.py --videos data/test --zones data/zones.json --gt data/ground_truth.csv --dwell 0 2 3
# b) Precision/Recall phát hiện người (cần ~100-200 khung tự gán nhãn dạng YOLO)
python eval_detection.py --data data/person.yaml --model yolov8n.pt
```
- `data/zones.json`: vùng cấm chuẩn hoá (0–1) cho từng video, khoá `default` dùng chung.
- `data/ground_truth.csv`: `video,start_s,end_s` – khoảng thời gian có sự kiện thật. Video bình thường không cần dòng nào.
- Cảnh báo được tính **đúng** nếu rơi vào khoảng sự kiện ± `--tolerance` giây (mặc định 2s).
- Kết quả: precision, recall, số cảnh báo sai mỗi giờ, FPS, ghi vào `outputs/eval_results.csv`. `N=0` là mốc "trước khi có cơ chế N giây".

## 5. Đưa lên web

Streamlit cần máy chủ Python nên không chạy được như trang HTML tĩnh. Cách đơn giản nhất:

- **Hugging Face Spaces** (khuyên dùng – RAM 16 GB miễn phí): New Space → SDK *Streamlit* → tải toàn bộ thư mục này lên (có sẵn `requirements.txt`, `packages.txt`).
- **Streamlit Community Cloud**: đẩy lên GitHub → share.streamlit.io → chọn `app.py`. Bộ nhớ ít hơn, nên dùng `yolov8n.pt` và video ngắn.

Trên server miễn phí chỉ có CPU, tốc độ thấp (vài FPS); tăng tốc bằng "xử lý 1/N khung" và `imgsz` nhỏ.

## 6. Cấu trúc

```
app.py                 giao diện Streamlit
evaluate.py            đánh giá mức sự kiện, so sánh N, FPS
eval_detection.py      precision/recall phát hiện người
src/processor.py       đọc video, YOLO + ByteTrack, vẽ chú thích, ghi video H.264
src/rules.py           vùng cấm, dwell time, cảnh báo tụ tập, phát lại luật
src/storage.py         SQLite, ảnh sự kiện, CSV, báo cáo HTML
tests/test_pipeline.py kiểm thử bằng YOLO giả lập
```

## 7. Giới hạn cần nêu trong báo cáo

- Video mạng khác góc camera, độ cao, ánh sáng và độ phân giải của camera thực tế → kết quả không đại diện triển khai thật.
- Bị che khuất, đông người, ban đêm/mưa làm giảm độ chính xác; ID tracking có thể đổi khi mất dấu lâu.
- Vùng cấm là polygon 2D trên ảnh; camera nghiêng làm "tâm bbox trong vùng" không luôn đồng nghĩa người đứng trong vùng.
- Chưa nhận diện danh tính; dùng camera thật cần tuân thủ quy định về quyền riêng tư và biển báo giám sát.
- Là công cụ hỗ trợ: mọi cảnh báo cần nhân sự an ninh xác nhận.
