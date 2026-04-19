# Plickers Python 📸

Hệ thống nhận diện ứng dụng ảnh thẻ Plickers nguồn mở ứng với OpenCV dành cho Python.
Dự án được kết cấu lại theo kiến trúc module chuyên nghiệp để dễ dàng bảo trì và bổ sung tính năng.

---

## 🎯 Giới thiệu
Ứng dụng sử dụng Computer Vision (OpenCV) kết hợp các thuật toán xác định Contours và áp dụng Thresholding linh hoạt (Otsu Threshold & Offset cắt Crop) nhằm nhận dạng thẻ Plickers trực tiếp qua đường truyền Camera (Live Webcam) hoặc từ tập ảnh thử nghiệm. 
Toàn bộ mã sẽ theo dõi toạ độ điểm ảnh, phát hiện hình vuông mẫu của Plickers, cắt lấy lưới `5x5` rồi đối chiếu với Database đã cho trước để chỉ ra: **Mã Học sinh** và **Đáp án chọn A/B/C/D**.

### Tỷ lệ nhận diện mẫu (Accuracy)
Hiện tại hệ thống đạt độ chính xác đáng tin cậy trên các môi trường ánh sáng phức tạp, quét mẫu tự động báo khoảng **86%~ nhận diện thành công** từ kho ảnh sample (Pass 35/41 thẻ khó qua phép Canny Edge).

## 📁 Cấu trúc thư mục

Dự án được phân cấp rõ ràng theo mô hình Layer Data và Source module:

```text
plickers-python/
│
├── data/                      # 📁 Tầng dữ liệu & tài nguyên tĩnh
│   ├── database/              # Chứa hệ cơ sở dữ liệu mẫu dạng Binary (card.data, card.list)
│   ├── samples/               # Bộ ảnh mẫu dùng để Unit Test khả năng quét
│   └── output/                # File logs đầu ra (vd: ket_qua.csv từ máy quét Camera)
│
├── src/                       # 📁 Tầng giao diện logic chính
│   ├── __init__.py
│   ├── core/                  # Bộ xử lý chung (Core Module)
│   │   ├── detector.py        # Object `PlickersDetector` - Trái tim OpenCV nhận diện khung
│   │   └── utils.py           # Helper xử lý Toán (Tìm Mode)
│   │
│   ├── scripts/               # Các Pipeline tác vụ độc lập
│   │   ├── generate_db.py     # Quét ảnh ở \data\samples để lập file Binary gốc
│   │   └── evaluate.py        # Đánh giá Unit Test tính chính xác của thuật toán quét
│   │
│   └── app.py                 # (MAIN) Chạy Camera Scanner giám sát trực tiếp!
│
├── requirements.txt           # Quản lý dependencies (Pip)
└── README.md                  # Hướng dẫn chi tiết dự án
```

## 🛠️ Cài đặt & Hướng dẫn sử dụng

### B1: Cài đặt thư viện
Yêu cầu bạn phải cài đặt `Python 3.x` trên thiết bị, sau đó chạy lệnh cài qua pip:

```bash
pip install -r requirements.txt
```

### B2: Sử dụng bộ Test để theo dõi độ nhạy
Chạy thử nghiệm thuật toán lên tập mẫu nội bộ (Kiểm tra lại độ chính xác hiện tại qua Console terminal, xuất thành báo cáo BINGO / TẠT FAIL). Mẫu in kết quả hoàn thiện và không vỡ bảng mã tiếng Việt.

```bash
python src/scripts/evaluate.py
```

### B3: Chạy phần mềm Webcam (Scanner Chính)
Bật ứng dụng giám sát thẻ. Phần mềm sẽ kết nối tới Window Direct Show `CAP_DSHOW` bắt khung hình và vẽ ô chữ nhật Xanh Lá bao lại mã thẻ + Tag Tên/Đáp án tìm thấy ngay trên màn hình.

```bash
python src/app.py
```
> **Đầu ra**: Kết quả quét trực tiếp sau khi được bắt giữ sẽ chèn thêm thông tin Thời gian (Timestamp) và cất vào file log Excel tại `data/output/ket_qua.csv`.

### (Tùy chọn) B4: Sinh dữ liệu mẫu lại Database
Trong trường hợp bạn nhập các ảnh chuẩn xác mới và muốn lập các điểm tham chiếu ảnh ma trận (5x5) Binary, hãy chạy Pipeline tạo lại DB bằng lệnh:
```bash
python src/scripts/generate_db.py
```

## 👨‍💻 Khả năng nâng cấp
Nhờ việc dọn dẹp biến thừa và đóng gói class cấu hình linh động:
- Lõi `detector.py` có thể được Import và đưa vào các nền tảng Framework lớn như **FastAPI/Flask** hoặc **Django** để tạo REST API cho app di động.
- Sẵn sàng tích hợp Module xử lý `OpenCV` khác không gây tác động lên logic luồng Camera.
