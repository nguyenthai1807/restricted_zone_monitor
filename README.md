# SchoolGuard AI — Giám sát an ninh khuôn viên trường học

Dự án thị giác máy tính hỗ trợ rà soát **video mẫu tải lên** để phát hiện người đi vào vùng hạn chế trong thời gian không được phép. Mục tiêu của bản MVP là tạo cảnh báo có bằng chứng và lưu lịch sử sự kiện; không thay thế nhân sự an ninh.

> **Phạm vi:** ưu tiên khuôn viên trường học. Lộ trình, phân công 7 thành viên, deadline và tiêu chí nghiệm thu xem tại [ROADMAP.md](ROADMAP.md). Những tính năng chưa được triển khai và kiểm thử không được xem là đã hoàn thiện.

## Pipeline hiện có

**OpenCV** đọc video → **YOLO (Ultralytics)** phát hiện người/đối tượng mô hình hỗ trợ → **ByteTrack** gán ID → **polygon zones + luật vùng/thời gian lưu lại** → **SQLite + ảnh sự kiện** → giao diện **Streamlit**, lịch sử và xuất CSV/HTML.

Kế hoạch mở rộng theo thứ tự:
1. Xâm nhập vùng hạn chế theo lịch — chức năng chính cần hoàn thiện.
2. Cảnh báo, xác minh, lịch sử và đánh giá bằng video có nhãn.
3. Nghiên cứu một loại sự cố (té ngã hoặc xô xát) chỉ khi MVP ổn định và có mô hình/dữ liệu phù hợp.

YOLO phát hiện người không tự động có nghĩa là hệ thống nhận diện được té ngã hay xô xát. Những hành vi đó cần mô hình và đánh giá riêng; nếu chưa đủ bằng chứng, chỉ ghi là hướng phát triển.

## 1. Cài đặt và chạy

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

Lần đầu chạy, Ultralytics có thể tự tải trọng số `yolov8n.pt`. Kiểm tra logic không cần YOLO bằng `python tests/test_pipeline.py` (hoặc `pytest`).

## 2. Demo video

Dùng video tự tạo hoặc video có quyền sử dụng. Không đưa video học sinh có thể nhận dạng hoặc thông tin nhạy cảm lên kho công khai nếu chưa có quyền phù hợp.

1. Chọn/tải video trong giao diện.
2. Đặt polygon vùng hạn chế và lưu cấu hình.
3. Cấu hình thời gian cấm khi tính năng lịch được tích hợp.
4. Chạy phân tích, xem cảnh báo và ảnh bằng chứng.
5. Kiểm tra lịch sử, rồi xuất CSV/HTML.

Cấu trúc dữ liệu đánh giá khuyến nghị:
- `data/normal/`: video không có xâm nhập.
- `data/event/`: video có xâm nhập.
- `data/test/`: video kiểm thử cuối, không dùng để chỉnh ngưỡng.
- `data/ground_truth.csv`: khoảng thời gian sự kiện thật, theo định dạng được mô tả trong `ROADMAP.md` và `evaluate.py`.

## 3. Đánh giá

Các script hiện có gồm `evaluate.py`, `eval_detection.py` và `tests/test_pipeline.py`. Báo cáo nên nêu precision, recall, cảnh báo sai mỗi giờ, FPS, độ trễ và điều kiện chạy. Không coi các mục tiêu trong roadmap là kết quả đã đo được.

## 4. Thành phần chính

```
app.py                  giao diện Streamlit
components/zone_editor  chỉnh sửa polygon vùng hạn chế
src/ui.py               cầu nối Streamlit và zone editor
src/processor.py        video, YOLO + ByteTrack, vẽ chú thích
src/rules.py            luật vùng, dwell time và cảnh báo
src/storage.py          SQLite, ảnh sự kiện, CSV/HTML
evaluate.py             đánh giá sự kiện/FPS
eval_detection.py       đánh giá phát hiện đối tượng
tests/test_pipeline.py  kiểm thử pipeline
ROADMAP.md              phạm vi, deadline, phân công và nghiệm thu
```

## 5. Giới hạn và quyền riêng tư

- Video mẫu không đại diện hoàn toàn cho camera thật; ánh sáng, góc quay, che khuất và tracking có thể ảnh hưởng kết quả.
- Polygon là vùng 2D trên ảnh, không phải hiểu biết đầy đủ về không gian.
- MVP không nhận diện danh tính và không giám sát camera trực tiếp 24/7.
- Chỉ dùng video có quyền sử dụng; giảm thiểu dữ liệu nhận dạng và thời gian lưu.
- Hệ thống chỉ hỗ trợ người trực; mọi cảnh báo cần được con người xác minh.
