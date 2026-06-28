# Plickers Python 🎯

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-App%20Factory-black.svg)
![React](https://img.shields.io/badge/React-Vite%20SPA-61DAFB.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green.svg)

An open-source, modernized alternative to Plickers built with **Python (Computer Vision)**, **Flask (Backend API)**, and **React (Frontend SPA)**. 

This system allows teachers to rapidly collect formative assessment data without requiring students to have devices. Teachers simply use their webcam to scan physical "paper clickers" (Plickers cards) that students hold up to indicate their answers (A, B, C, or D).

---

## ✨ Features

- **Real-Time Computer Vision Scanning**: Utilizes OpenCV algorithms (Contours, Otsu Thresholding, Canny Edge Detection) to instantly identify student cards and parse their chosen answers.
- **Modern Single Page Application (SPA)**: A beautiful, responsive user interface built with React, TypeScript, and Vite. Features a premium Dark Mode aesthetic.
- **Live Event Streaming**: Real-time synchronization between the camera scanning engine and the frontend UI using Server-Sent Events (SSE).
- **Dual Display Modes**: 
  - *Teacher Dashboard*: Controls the scanning session, previews the live camera feed, and manages questions.
  - *Student Display*: A projector-friendly view featuring live-updating bar charts (via Chart.js) that reveal class statistics without exposing individual student answers during the scan.
- **Decoupled Architecture**: Strictly separated Frontend and Backend architectures allowing independent scaling, testing, and modification.

---

## 🏗 System Architecture

This project strictly adheres to professional software architecture patterns, focusing on maintainability, modularity, and separation of concerns.

### Backend (Flask API)
The backend is powered by Python and Flask, implementing the **App Factory Pattern** and **Blueprints**.
- **Core / CV (`src/core`)**: Contains the `PlickersDetector`, utilizing OpenCV for geometric transformations and matrix mapping to decode the 5x5 card grids.
- **Services (`src/web/services`)**: Business logic is isolated here.
  - `camera_service.py`: Manages the background OpenCV camera thread and yields JPEG frames.
  - `state.py`: Handles concurrency and locks for the global scanning state.
  - `data_service.py`: Manages I/O operations for student rosters and question banks.
- **Routes (`src/web/routes`)**: API endpoints divided logically into `auth_routes`, `scanner_routes`, and `data_routes`.
- **Security**: Utilizes `Flask-Login` for session management and `Flask-Bcrypt` for password hashing.

### Frontend (React SPA)
The frontend is a standalone React application built via Vite.
- **API Client (`src/api/client.ts`)**: A centralized wrapper around `fetch` that standardizes request headers, handles JSON parsing, and manages error throwing across the application.
- **State Management**: Uses React hooks alongside `EventSource` to subscribe to the Flask backend's SSE stream, ensuring the UI remains perfectly synced with the camera's detection state.
- **Styling**: Relies on scalable, clean Vanilla CSS variables with zero bloated frameworks, ensuring maximum flexibility.

---

## 📂 Directory Structure

```text
plickers-python/
│
├── run_web.py                 # Entry point for the Flask Backend API Server
├── run_scanner.py             # Entry point for the Standalone Camera Scanner (CLI mode)
├── requirements.txt           # Python backend dependencies
├── pyproject.toml             # Project metadata and linting configuration
│
├── frontend/                  # React Single Page Application
│   ├── src/
│   │   ├── api/               # Centralized API client (client.ts)
│   │   ├── pages/             # Route components (Dashboard, Student Display, Auth)
│   │   ├── App.tsx            # Main router and authentication state provider
│   │   └── index.css          # Global design system and CSS variables
│   └── vite.config.ts         # Vite build config with proxy to Flask (:5000)
│
├── data/                      # Local Data Storage
│   ├── class.json             # Roster defining card numbers to student names
│   ├── questions.json         # Bank of multiple-choice questions
│   ├── database/              # Matrix configuration defining the signatures of cards
│   ├── samples/               # Sample images used for offline testing
│   └── output/                # Auto-generated CSV files of scan sessions
│
└── src/                       # Python Source Code
    ├── core/                  # OpenCV Detector, Models, and Database setup
    ├── scripts/               # Utilities (PDF Generation, DB initialization)
    └── web/                   # Flask Application Directory
        ├── app.py             # App Factory (create_app)
        ├── extensions.py      # Flask plugins initialization
        ├── routes/            # Flask Blueprints (API Controllers)
        └── services/          # Business logic and State management
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.8+**
- **Node.js 18+**

### 1. Backend Setup (Python)

It is highly recommended to use a virtual environment.

```bash
# Create the virtual environment
python -m venv .venv

# Activate it (Windows)
.venv\Scripts\activate

# Activate it (macOS/Linux)
source .venv/bin/activate

# Install all backend dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup (React)

Open a new terminal window:

```bash
cd frontend
npm install
```

---

## 💻 Usage

To run the full application, you must start both the backend API and the frontend development server simultaneously.

**Terminal 1: Start the API Server**
```bash
# From the project root, ensure .venv is activated
python run_web.py
```
*The Flask server will boot up on `http://localhost:5000`.*

**Terminal 2: Start the Frontend UI**
```bash
# From the frontend/ directory
npm run dev
```
*The React application will boot up on `http://localhost:5173`.*

### Operating the System
1. Open your browser and navigate to `http://localhost:5173`.
2. Register a new teacher account and log in.
3. You will land on the **Teacher Dashboard**. Select a question from the dropdown.
4. Click **▶ START** to activate your webcam.
5. Have students hold up their printed Plickers cards. The system will detect them instantly.
6. Click **👁 REVEAL** to stop scanning, lock in the answers, and grade the results.
7. Open a secondary tab/window to `http://localhost:5173/display` and drag it to your projector to show live charts to the students.
8. Results are automatically saved to `data/output/session_YYYYMMDD_HHmmss.csv`.

---

## 🛠 Advanced Scripts

The repository includes several helpful CLI scripts located in `src/scripts/`:

- **Generate PDF Cards**: Create printable PDF sheets of the Plickers cards.
  ```bash
  python src/scripts/generate_plickers_pdf.py
  ```
- **Accuracy Testing**: Run the detector against static images in `data/samples/` to evaluate algorithmic accuracy.
  ```bash
  python tests/test_plickers.py
  ```
- **Standalone Scanner**: Run the scanner entirely through an OpenCV desktop window without the web application.
  ```bash
  python run_scanner.py
  ```

---

## 📄 License

This project is open-source and available under the MIT License. Feel free to fork, modify, and use it in your classrooms!
