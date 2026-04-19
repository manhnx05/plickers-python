# Plickers Python 📸

Hệ thống nhận diện thẻ Plickers nguồn mở sử dụng OpenCV cho Python.  
Hỗ trợ hai chế độ: **Web App** (teacher dashboard + student display) và **Standalone Scanner** (camera trực tiếp).

---

## 🎯 Giới thiệu

Ứng dụng dùng Computer Vision (OpenCV) kết hợp thuật toán Contours + Otsu Thresholding để nhận dạng thẻ Plickers qua Webcam hoặc ảnh tĩnh.  
Hệ thống xác định **Mã Học sinh** và **Đáp án A/B/C/D** bằng cách cắt lưới `5×5` trên thẻ và đối chiếu với database nhị phân.

### Tỷ lệ nhận diện (Accuracy)
~**86%** trên bộ ảnh sample 34 thẻ qua bộ lọc Canny Edge đa tham số.

---

## 📁 Cấu trúc thư mục

```text
plickers-python/
│
├── run_web.py                 # ▶ Khởi chạy Web App (Flask)
├── run_scanner.py             # ▶ Khởi chạy Standalone Camera Scanner
├── requirements.txt
├── README.md
│
├── data/                      # Tầng dữ liệu & tài nguyên tĩnh
│   ├── database/              # Database nhị phân (card.data, card.list)
│   ├── samples/               # Ảnh mẫu dùng để test (###-X.jpg)
│   ├── class.json             # Danh sách học sinh (card_no → tên)
│   ├── questions.json         # Ngân hàng câu hỏi ABCD
│   └── output/                # Kết quả xuất ra (CSV sessions) — KHÔNG track git
│
└── src/                       # Tầng logic chính
    ├── app.py                 # Standalone Camera Scanner (entry: main())
    ├── core/
    │   ├── detector.py        # PlickersDetector — trái tim OpenCV
    │   └── utils.py           # Math helper (mode)
    ├── scripts/
    │   ├── evaluate.py        # Unit test độ chính xác trên tập mẫu
    │   ├── generate_db.py     # Tạo database từ ảnh samples
    │   ├── generate_pdf.py    # Xuất PDF thẻ in (ảnh mẫu)
    │   └── generate_plickers_pdf.py  # Xuất PDF thẻ in (từ database matrix)
    └── web/
        ├── app_web.py         # Flask server — Teacher + Display
        └── templates/
            ├── teacher.html   # Teacher dashboard (camera + điều khiển)
            └── display.html   # Student display (chiếu lên màn hình lớn)
```

---

## 🛠️ Cài đặt

```bash
pip install -r requirements.txt
```

---

## 🚀 Cách sử dụng

### 1. Web App (Khuyến nghị)

Chạy Flask server từ **thư mục gốc**:

```bash
python run_web.py
```

Mở trình duyệt:
- **Teacher Dashboard** → `http://localhost:5000/`  
- **Student Display** → `http://localhost:5000/display`  

**Luồng hoạt động:**
1. Chọn câu hỏi ở Teacher Dashboard
2. Nhấn **▶ BẮT ĐẦU QUÉT** — camera tự bật
3. Học sinh giơ thẻ, hệ thống quét và hiển thị realtime
4. Nhấn **👁 HIỆN ĐÁP ÁN** — chart kết quả hiện trên màn hình lớp
5. Kết quả tự xuất ra `data/output/session_YYYYMMDD_HHmmss.csv`

> **Lưu ý:** Camera khởi động lazy — chỉ bật khi client kết nối lần đầu.  
> Reload dữ liệu không cần restart: `POST /api/reload_data`

### 2. Standalone Camera Scanner

```bash
python run_scanner.py
```

Quét trực tiếp qua Webcam. Kết quả lưu vào `data/output/ket_qua.csv`.  
Nhấn **`q`** để thoát.

### 3. Kiểm tra độ chính xác

```bash
python src/scripts/evaluate.py
```

Chạy detector trên toàn bộ ảnh trong `data/samples/` và in kết quả BINGO / THẤT BẠI.

### 4. Tạo lại Database

```bash
python src/scripts/generate_db.py
```

Cần thiết khi thêm ảnh mẫu mới vào `data/samples/`.

### 5. In thẻ PDF

```bash
# PDF từ database matrix (đẹp hơn, khuyến nghị)
python src/scripts/generate_plickers_pdf.py

# PDF từ ảnh mẫu (xem trước ảnh thật)
python src/scripts/generate_pdf.py
```

---

## 🔌 API Endpoints (Web App)

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/` | Teacher dashboard |
| GET | `/display` | Student display |
| GET | `/video_feed` | MJPEG camera stream |
| GET | `/api/state` | Trạng thái hiện tại (JSON) |
| GET | `/api/events` | SSE realtime stream |
| GET | `/api/class` | Danh sách học sinh |
| GET | `/api/questions` | Ngân hàng câu hỏi |
| POST | `/api/start` | Bắt đầu phiên quét |
| POST | `/api/stop` | Tạm dừng quét |
| POST | `/api/reveal` | Hiện đáp án + lưu CSV |
| POST | `/api/reset` | Reset phiên mới |
| POST | `/api/reload_data` | Reload JSON không restart server |

---

## 👨‍💻 Nâng cấp & Mở rộng

- `PlickersDetector` trong `core/detector.py` có thể import và nhúng vào bất kỳ framework nào (FastAPI, Django…)
- Thêm câu hỏi: chỉnh sửa `data/questions.json`
- Thêm học sinh: chỉnh sửa `data/class.json`, gọi `POST /api/reload_data`
- Thêm thẻ mới: thêm ảnh vào `data/samples/`, chạy lại `generate_db.py`
