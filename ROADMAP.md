# ROADMAP — SchoolGuard AI
## Giám sát an ninh khuôn viên trường học bằng Computer Vision

**Mốc nộp/trình bày:** 28/10/2026  
**Chiến lược:** hoàn thiện một MVP ổn định trước, nghiên cứu nhận diện sự cố sau. Đây là kế hoạch; mục nào chưa được triển khai và kiểm thử thì không được coi là chức năng đã hoàn thành.

## 1. Phạm vi đã chốt

### Mục tiêu MVP (bắt buộc)
Hỗ trợ nhân viên an ninh rà soát **video mẫu tải lên** để phát hiện người đi vào vùng hạn chế trong khung giờ không được phép, tạo cảnh báo có bằng chứng và lưu lịch sử.

Kịch bản mẫu:
- Cổng phụ hoặc hành lang chỉ dành cho nhân viên.
- Sân thượng/khu vực kỹ thuật bị hạn chế.
- Khuôn viên hoặc bãi xe sau giờ hoạt động.

Không kết nối camera trực tiếp trong MVP; không nhận diện danh tính; không tự động kết luận một người có ý định xấu.

### Giai đoạn 2 (chỉ làm khi MVP đạt mốc)
Nghiên cứu **một** loại sự cố, ưu tiên thử nghiệm té ngã *hoặc* xô xát, bằng mô hình nhận diện hành động/chuỗi khung hình và tập video có nhãn. Kết quả chỉ là “sự cố nghi ngờ — cần xác minh”. Nếu chưa có dữ liệu/mô hình và kết quả đánh giá phù hợp, báo cáo phần này là nghiên cứu khả thi/hướng phát triển, không đưa vào danh sách tính năng đã hoàn thiện.

### Ngoài phạm vi trước 28/10
- Hệ thống đa camera hoặc giám sát RTSP 24/7.
- Nhận diện khuôn mặt/định danh học sinh.
- Gửi SMS/email/Telegram hoặc tích hợp hệ thống quản lý trường.
- Nhiều hồ sơ môi trường (bệnh viện, kho hàng, v.v.).
- Cam kết phát hiện đánh nhau/té ngã chính xác khi chưa đánh giá.

## 2. Thành phần hiện có phải giữ

- OpenCV đọc video.
- YOLO (Ultralytics) phát hiện người/đối tượng mà mô hình hiện tại hỗ trợ.
- ByteTrack theo dõi ID đối tượng.
- Polygon zones và trình chỉnh sửa vùng.
- Luật vùng cấm/thời gian lưu lại N giây hiện có.
- Giao diện Streamlit tải/chọn video và hiển thị kết quả.
- SQLite, ảnh sự kiện, lịch sử, xuất CSV/HTML.
- `evaluate.py`, `eval_detection.py` và `tests/test_pipeline.py`.

Không viết lại toàn bộ pipeline. Giữ khả năng đọc cấu hình vùng cũ (`data/zones.json`) hoặc cung cấp chuyển đổi có kiểm thử nếu định dạng thay đổi.

## 3. Yêu cầu MVP — P0

1. **Vùng hạn chế theo lịch:** tên vùng, polygon, ngày trong tuần, giờ cấm/cho phép và thời gian chờ trước cảnh báo.
2. **Lịch qua nửa đêm:** ví dụ 22:00–05:00 phải hoạt động đúng ở cả hai phía của nửa đêm.
3. **Cảnh báo xâm nhập:** ghi loại sự kiện, video, thời điểm, vùng, ảnh bằng chứng và thông tin đối tượng nếu có.
4. **Chống cảnh báo trùng:** cooldown/khóa sự kiện theo track và vùng; tránh một người đứng trong vùng tạo cảnh báo ở mọi khung hình.
5. **Bảng sự kiện:** xem ảnh, lọc theo ngày/vùng/loại, đánh dấu “Mới”, “Đang xác minh”, “Đã xử lý” hoặc “Báo nhầm”.
6. **Lưu trữ và báo cáo:** SQLite vẫn hoạt động sau khi khởi động lại; xuất CSV/HTML.
7. **Trải nghiệm demo:** trạng thái tải video, phân tích, hoàn thành và lỗi rõ ràng; demo có thể chạy hoàn toàn từ video tải lên.
8. **Đánh giá:** dùng video có nhãn thật; tách video dùng chỉnh cấu hình và video kiểm thử cuối.

## 4. Kế hoạch theo ngày và deadline

| Ngày | Công việc | Đầu ra/tiêu chí chốt |
|---|---|---|
| 13–14/10 | Chạy baseline, chốt cấu trúc dữ liệu sự kiện/lịch, chuẩn bị video và test case, tạo GitHub Issues | Cả nhóm chạy được bản hiện tại; thống nhất hợp đồng dữ liệu và phạm vi |
| 15–16/10 | Viết/test hàm lịch và luật vùng; làm giao diện vùng/lịch; chuẩn bị nhãn video | Có test giờ được phép, giờ cấm và lịch qua nửa đêm |
| 17–18/10 | Tích hợp luật lịch vào pipeline và cảnh báo; dựng UI giám sát | Chạy được một video end-to-end, tạo sự kiện có timestamp |
| 19–21/10 | Hoàn thiện SQLite, ảnh bằng chứng, trạng thái xác minh, lọc và xuất CSV/HTML | **MVP tích hợp ổn định chậm nhất 21/10** |
| 22–24/10 | Kiểm thử độc lập, sửa lỗi; chỉ sau khi MVP đạt mới thử một mô hình sự cố | Báo cáo test và số liệu; mô hình sự cố là tùy chọn |
| 25/10 | Đóng băng tính năng | Không thêm tính năng lớn; chỉ sửa lỗi |
| 25–26/10 | Viết báo cáo, slide, hướng dẫn cài đặt, ghi giới hạn | Báo cáo có kiến trúc, phân công, dữ liệu, kết quả và hạn chế |
| 27/10 | Tổng duyệt trên máy demo, chạy video dự phòng | Chạy trọn kịch bản ít nhất 2 lần, không thao tác sửa code tại chỗ |
| 28/10 | Trình bày | Demo MVP, số liệu đánh giá và hướng phát triển |

## 5. Phân công 7 thành viên

### Thành viên 1 — Frontend: màn hình video
- Hoàn thiện chọn/tải video, nút chạy/dừng và trạng thái xử lý.
- Hiển thị video chú thích, bounding box, ID và polygon.
- **Deadline:** bản đầu 18/10; ổn định 21/10.
- **Nghiệm thu:** chạy được video mẫu hợp lệ; báo lỗi dễ hiểu với file không hợp lệ.

### Thành viên 2 — Frontend: cấu hình vùng và lịch
- Giao diện chọn vùng, tên vùng và cấu hình ngày/giờ cấm.
- Làm rõ múi giờ dùng cho demo; không mở rộng ngày nghỉ/ngoại lệ nếu chưa cần.
- **Deadline:** bản đầu 18/10; kiểm thử tích hợp 21/10.
- **Nghiệm thu:** cấu hình được ít nhất 2 vùng với lịch khác nhau; dữ liệu hợp lệ được lưu và nạp lại.

### Thành viên 3 — Frontend: cảnh báo và lịch sử
- Bảng sự kiện, ảnh bằng chứng, bộ lọc và trạng thái xác minh.
- Nút xuất CSV/HTML hoặc nối với chức năng xuất hiện có.
- **Deadline:** bản đầu 19/10; tích hợp 21/10.
- **Nghiệm thu:** xem được chi tiết một sự kiện, lọc lịch sử và thay đổi trạng thái.

### Thành viên 4 — Backend: pipeline video
- Giữ OpenCV + YOLO + ByteTrack; đảm bảo video tải lên được xử lý và vùng hiển thị đúng.
- Kiểm tra lỗi codec/video và luồng dừng/chạy.
- **Deadline:** kiểm tra baseline 14/10; tích hợp 18/10; ổn định 21/10.
- **Nghiệm thu:** không làm hỏng pipeline cũ; ID và timestamp được truyền đúng cho luật cảnh báo.

### Thành viên 5 — Backend: luật lịch và lưu trữ
- Viết hàm kiểm tra lịch cấm độc lập với UI; xử lý lịch qua nửa đêm.
- Tích hợp cooldown/chống trùng, SQLite, ảnh và báo cáo.
- **Deadline:** logic lịch 16/10; tích hợp 20/10; hoàn thiện 21/10.
- **Nghiệm thu:** test giờ cấm/cho phép và qua nửa đêm đạt; sự kiện lưu đúng và tồn tại sau khi khởi động lại.

### Thành viên 6 — Tester: kiểm thử chức năng/hồi quy
- Viết checklist, kiểm thử file lỗi, polygon/lịch không hợp lệ, cooldown, SQLite và CSV/HTML.
- Chạy lại `tests/test_pipeline.py` sau các lần tích hợp.
- **Deadline:** test case 15/10; vòng test MVP 21–22/10; kiểm thử cuối 24/10.
- **Nghiệm thu:** có báo cáo từng test đạt/không đạt, bước tái hiện và mức độ lỗi.

### Thành viên 7 — Tester: dữ liệu và đánh giá
- Chuẩn bị video bình thường/xâm nhập và ground truth theo khoảng thời gian.
- Tách video chỉnh cấu hình khỏi tập test cuối; đo precision, recall, cảnh báo sai/giờ và FPS.
- **Deadline:** bộ video nháp 16/10; ground truth 20/10; kết quả 24/10.
- **Nghiệm thu:** có bảng số liệu, mô tả cách tính và nêu rõ giới hạn của video mẫu; không sửa ngưỡng dựa trên tập test cuối.

**Phối hợp:** một thành viên được nhóm chỉ định làm người tích hợp/merge; đây là vai trò điều phối, không phải thành viên thứ tám. Frontend/backend thống nhất tên trường và kiểu dữ liệu sự kiện trước 15/10. Mỗi PR phải mô tả thay đổi và cách test; tránh nhiều người cùng sửa `app.py` mà không báo nhau.

## 6. Tiêu chí nghiệm thu toàn dự án

### Chức năng bắt buộc
- [ ] Demo được ít nhất 2 kịch bản: người xâm nhập trong giờ cấm → có cảnh báo; người đi vào trong giờ cho phép → không có cảnh báo xâm nhập theo lịch.
- [ ] Có ít nhất 2 vùng cấu hình khác nhau.
- [ ] Lịch qua nửa đêm được kiểm thử.
- [ ] Cảnh báo có thời gian, vùng và ảnh bằng chứng.
- [ ] Chống lặp cảnh báo cho cùng một lần xâm nhập.
- [ ] SQLite lưu được lịch sử sau khi khởi động lại.
- [ ] Lọc sự kiện và xuất CSV/HTML hoạt động.
- [ ] Các bài test hồi quy hiện có vẫn đạt.
- [ ] Demo từ video tải lên, không phụ thuộc camera trực tiếp.

### Đánh giá định lượng
Mục tiêu khởi đầu (không phải kết quả đã đạt): precision cảnh báo xâm nhập ≥ 90%, recall ≥ 85%, độ trễ ≤ 2 giây sau khi hệ thống đủ điều kiện phát cảnh báo trong môi trường demo đã xác định. Nếu không đạt, báo cáo số liệu thật và phân tích nguyên nhân; không thay đổi nhãn để làm đẹp kết quả.

### An toàn, quyền riêng tư và tính trung thực
- [ ] Dùng video tự tạo hoặc có quyền sử dụng; tránh dữ liệu học sinh có thể nhận dạng nếu không có cho phép.
- [ ] Không nhận diện khuôn mặt hoặc khẳng định danh tính.
- [ ] Cảnh báo là hỗ trợ xác minh của con người, không phải kết luận vi phạm.
- [ ] Té ngã/xô xát chỉ được ghi là tính năng thử nghiệm nếu có mô hình và đánh giá riêng; nếu chưa, để ở mục hướng phát triển.

## 7. Kịch bản demo chuẩn

1. Mở ứng dụng và tải video mẫu.
2. Chọn vùng hạn chế và cấu hình giờ cấm.
3. Chạy phân tích, quan sát box/ID/vùng.
4. Chỉ ra thời điểm xâm nhập và cảnh báo kèm ảnh bằng chứng.
5. Mở lịch sử, xác minh sự kiện, xuất CSV/HTML.
6. Chạy video đối chứng trong giờ cho phép để chứng minh hệ thống không cảnh báo sai theo lịch.
7. Kết thúc bằng số liệu test và các giới hạn đã biết.

## 8. Giới hạn phải nêu trong báo cáo

Video mẫu không đại diện đầy đủ cho camera trường học thực tế. Ánh sáng, góc camera, che khuất và đổi ID tracking có thể ảnh hưởng kết quả. Polygon là vùng 2D trên ảnh. Hệ thống chưa được chứng nhận để triển khai an ninh thực tế và mọi cảnh báo cần người có trách nhiệm xác minh.
