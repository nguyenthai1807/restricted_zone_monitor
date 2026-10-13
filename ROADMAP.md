# Lộ trình mở rộng: Hệ thống giám sát an ninh thông minh

## 1. Mục tiêu mới
Mở rộng dự án từ phát hiện đối tượng trong vùng cấm thành hệ thống hỗ trợ giám sát an ninh theo ngữ cảnh:
- Phát hiện người/xe đi vào khu vực bị hạn chế.
- Cấu hình vùng, lịch được phép/cấm, độ trễ và mức độ cảnh báo.
- Nghiên cứu phát hiện hành vi nguy hiểm như nghi ngờ ẩu đả hoặc té ngã/tai nạn.
- Lưu sự kiện, ảnh minh chứng, thời gian, loại cảnh báo và trạng thái xử lý.

**Lưu ý quan trọng:** YOLO hiện tại nhận diện đối tượng như người/xe, không tự nhận biết đáng tin cậy hành vi đánh nhau hay tai nạn. Các tính năng hành vi cần mô hình phù hợp và dữ liệu kiểm thử riêng. Hệ thống chỉ hỗ trợ người trực giám sát; cảnh báo cần được con người xác minh.

## 2. Chức năng hiện có cần giữ
- Giao diện Streamlit chọn/tải video.
- Vẽ polygon vùng hạn chế và lưu cấu hình.
- YOLO phát hiện đối tượng, ByteTrack theo dõi ID.
- Quy tắc ở trong vùng quá N giây và cảnh báo tụ tập cơ bản.
- SQLite, ảnh sự kiện, lịch sử, xuất CSV/HTML.
- Công cụ đánh giá sự kiện/FPS và kiểm thử pipeline.

Không xóa các chức năng này. Bổ sung theo từng bước và giữ tương thích với cấu hình vùng cấm cũ nếu có thể.

## 3. Kịch bản và mức ưu tiên

### P0 — Cần hoàn thiện trước
1. **Xâm nhập theo lịch:** mỗi khu vực có tên, polygon, đối tượng áp dụng, ngày trong tuần và giờ cấm. Ví dụ sân thượng cấm toàn thời gian; sân trường cấm từ 22:00 đến 05:00. Cho phép cấu hình báo ngay hoặc chờ vài giây để giảm báo nhầm. Phải xử lý đúng lịch qua nửa đêm.
2. **Nhiều hồ sơ môi trường:** Trường học, Kho hàng, Sân thượng; mỗi hồ sơ có vùng, lịch, ngưỡng tin cậy, thời gian chờ và mức độ cảnh báo riêng.
3. **Bảng cảnh báo:** loại sự kiện, camera/video, thời gian, khu vực, độ tin cậy, ảnh minh chứng và mức độ.
4. **Xử lý sự kiện:** Mới / Đang xác minh / Đã xử lý / Báo nhầm; có ghi chú người xác minh.
5. **Lọc và báo cáo:** lọc theo ngày, khu vực, loại, mức độ; xuất CSV/HTML; tránh tạo cảnh báo lặp bằng cơ chế cooldown.
6. **Thông báo:** bản đầu tiên cảnh báo ngay trên giao diện và lưu lịch sử. Email/Telegram là phần mở rộng; bí mật API phải đặt trong biến môi trường, không commit lên GitHub.

### P1 — Nghiên cứu hành vi
7. **Nghi ngờ ẩu đả/xung đột:** cần mô hình nhận diện hành động/video hoặc baseline phù hợp và dữ liệu gán nhãn. Phân biệt với thể thao, đùa giỡn, bắt tay, chen lấn. Chỉ hiển thị “nghi ngờ xung đột” kèm độ tin cậy để người trực xác minh.
8. **Nghi ngờ té ngã/tai nạn:** cần pose estimation hoặc action recognition theo chuỗi khung hình. Không được kết luận tai nạn chỉ vì người ngồi/nằm hoặc một khung hình bất thường.
9. Nếu chưa có mô hình và đánh giá phù hợp, trình bày hai tính năng trên là hướng phát triển, không tuyên bố đã hoàn thiện.

### P2 — Ý tưởng mở rộng
10. Tụ tập đông người ở nơi/giờ không phù hợp.
11. Xe đi vào khu vực chỉ dành cho người đi bộ.
12. Người lưu lại bất thường ngoài giờ cho phép.
13. Lối thoát hiểm bị che chắn — cần luật/mô hình và góc camera phù hợp.
14. Vật thể bị bỏ quên — cần định nghĩa khu vực và cách giảm báo nhầm.
15. Nhiều camera hoặc camera IP/RTSP trực tiếp. Phiên bản hiện tại chủ yếu xử lý video đã chọn/tải lên, chưa phải hệ thống giám sát trực tiếp 24/7.

## 4. Danh sách công việc kỹ thuật

### Cấu hình và luật
- [ ] Thiết kế data/security_profiles.json (hoặc cấu hình tương đương) lưu hồ sơ, vùng và lịch.
- [ ] Viết hàm kiểm tra lịch cấm độc lập với giao diện.
- [ ] Xử lý đúng lịch qua nửa đêm, ngày trong tuần, múi giờ và ngày ngoại lệ.
- [ ] Giữ tương thích data/zones.json hoặc có bước chuyển đổi cấu hình cũ.
- [ ] Kiểm tra polygon/giờ không hợp lệ.
- [ ] Tách loại sự kiện, mức độ, độ trễ và cooldown.
- [ ] Phân biệt rõ “phát hiện người”, “xâm nhập vùng cấm” và “nghi ngờ hành vi nguy hiểm”.
- [ ] Đảm bảo vùng nguy cơ cao có thể báo ngay, không bị áp thời gian chờ mặc định.

### Giao diện và lưu trữ
- [ ] Trang quản lý khu vực, hồ sơ môi trường và lịch cấm.
- [ ] Bảng sự kiện với bộ lọc, ảnh minh chứng và trạng thái xác minh.
- [ ] Hiển thị rõ nguồn của cảnh báo: luật vùng hay mô hình hành vi.
- [ ] Lưu loại sự kiện, mức độ, độ tin cậy, thời gian, ảnh và trạng thái xử lý.
- [ ] Hiển thị lỗi dễ hiểu khi video, mô hình hoặc cấu hình không dùng được.

### Dữ liệu và đánh giá
- [ ] Chuẩn bị video bình thường, xâm nhập ban ngày/ban đêm, đi sát mép vùng, tụ tập và tình huống dễ nhầm.
- [ ] Gán nhãn khoảng thời gian có sự kiện làm ground truth.
- [ ] Tách tập chỉnh ngưỡng và tập kiểm thử cuối.
- [ ] Báo cáo precision, recall, F1, cảnh báo sai mỗi giờ, độ trễ cảnh báo và FPS.
- [ ] Với mô hình ẩu đả/té ngã, cần bộ dữ liệu và chỉ số riêng.
- [ ] Không dùng video chưa có quyền sử dụng; hạn chế dữ liệu nhận diện cá nhân và thời hạn lưu.

### Kiểm thử tối thiểu
- [ ] Vào vùng cấm trong giờ cấm → cảnh báo đúng độ trễ.
- [ ] Vào vùng trong giờ được phép → không có cảnh báo xâm nhập.
- [ ] Lịch 22:00–05:00 hoạt động đúng trước và sau nửa đêm.
- [ ] Đi sát mép vùng không gây quá nhiều báo nhầm.
- [ ] Mất tracking rồi xuất hiện lại không tạo hàng loạt cảnh báo.
- [ ] Sự kiện lưu đúng vào SQLite và xuất CSV/HTML.
- [ ] Cấu hình cũ vẫn đọc được hoặc chuyển đổi an toàn.
- [ ] Cảnh báo hành vi không chắc chắn được hiển thị là “nghi ngờ”, không phải kết luận.

## 5. Thứ tự triển khai
1. Chốt cấu trúc hồ sơ/khu vực/lịch và viết test lịch.
2. Thêm luật xâm nhập theo lịch, giữ pipeline YOLO + ByteTrack.
3. Nâng cấp bảng cảnh báo và trạng thái xác minh.
4. Chuẩn bị video test, đo precision/recall, báo nhầm mỗi giờ và độ trễ.
5. Khi P0 ổn định, thử nghiệm mô hình xung đột/té ngã.
6. Sau cùng mới xét camera trực tiếp, thông báo ngoài ứng dụng và nhiều camera.

## 6. Phân chia nhóm 7 người
1. **Frontend 1:** giao diện giám sát, chọn video, tiến trình xử lý.
2. **Frontend 2:** cấu hình khu vực, hồ sơ môi trường, lịch cấm.
3. **Frontend 3:** bảng sự kiện, bộ lọc, xác minh, báo cáo.
4. **Backend 1:** pipeline video, YOLO/ByteTrack, ảnh sự kiện, độ trễ.
5. **Backend 2:** luật lịch, mức cảnh báo, cooldown, cấu hình và SQLite.
6. **Tester 1:** kiểm thử chức năng, lịch qua nửa đêm, tương thích cấu hình, xuất báo cáo.
7. **Tester 2:** ground truth, precision/recall/F1, báo nhầm mỗi giờ, FPS và nghiên cứu dữ liệu hành vi.

Chốt hợp đồng giao tiếp giữa frontend/backend trước khi chia nhánh; tránh để nhiều người cùng sửa app.py mà không thống nhất.

## 7. Tiêu chí hoàn thành bản báo cáo
- [ ] Demo ít nhất 2 kịch bản: xâm nhập theo lịch và không cảnh báo khi được phép.
- [ ] Cấu hình được ít nhất 2 môi trường.
- [ ] Cảnh báo có ảnh, thời gian, loại sự kiện và lưu lịch sử.
- [ ] Có kết quả kiểm thử định lượng, ví dụ báo nhầm và giới hạn.
- [ ] Nêu rõ ẩu đả/té ngã là hướng nghiên cứu nếu chưa có mô hình và đánh giá đủ tin cậy.
- [ ] README hướng dẫn cài đặt, demo, chuẩn bị dữ liệu và giới hạn.
