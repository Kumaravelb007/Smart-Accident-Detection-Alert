# Smart Accident Detection and Traffic Analysis

A production-style computer vision platform for real-time accident detection, severity estimation, and traffic analytics from CCTV video.

## What Changed

This version upgrades the project to:

- CNN-first accident detection (replacing YOLO in the accident decision path)
- Multi-signal accident strategy with CNN + trajectory collision analysis + optical-flow impact validation
- Pretrained vehicle object detection with MobileNet-SSD DNN (with contour fallback)
- OpenCV traffic analytics (vehicle density, speed trend, congestion, anomaly score, motion spike ratio)
- Severity classification (`Minor`, `Moderate`, `Critical`)
- React frontend for login, signup, dashboard, history, and AI chat
- Insight-rich history dashboard with KPI tiles, trend charts, heatmaps, and risk visuals
- FastAPI backend serving React build plus API routes

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI + Uvicorn
- Computer Vision: OpenCV + CNN pipeline
- Deep Learning: TensorFlow/Keras (optional custom model), MobileNetV2 fallback
- AI Reporting: Groq API
- Alerting: SendGrid
- Storage: SQLite + JSON user store

## Project Structure

```text
smart accident detection/
  docs/
    ARCHITECTURE.md
  backend/
    main.py
    config.py
    .env.example
    requirements.txt
    models/
      detector.py
      pretrained/
        accident_cnn.keras   # optional custom model path
    routes/
      auth.py
      detection.py
      chat.py
    utils/
      video_processor.py
      email_service.py
      ai_report.py
      database.py
      auth.py
  frontend/
    package.json
    vite.config.js
    .env.example
    index.html
    src/
      App.jsx
      main.jsx
      api.js
      styles.css
      constants/
        detection.js
      lib/
        session.js
        formatters.js
      pages/
        LoginPage.jsx
        SignupPage.jsx
        DashboardPage.jsx
      components/
        ToastProvider.jsx
        LoadingOverlay.jsx
        ChatWidget.jsx
        dashboard/
          DashboardHeader.jsx
          FeatureHighlights.jsx
          DashboardTabs.jsx
          UploadPanel.jsx
          AnalysisResultPanel.jsx
          HistorySection.jsx
          HistoryRecords.jsx
        history/
          HistoryInsights.jsx
```

## Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Server: `http://127.0.0.1:8000`

## Frontend Setup (React)

### Development mode

```bash
# terminal 1
cd backend
python main.py

# terminal 2
cd frontend
npm install
npm run dev
```

Important:
- Vite is configured with a proxy, so frontend requests to `/api/*`, `/frames/*`, and `/uploads/*` are forwarded to `http://127.0.0.1:8000`.
- If your backend runs on another host/port, set `VITE_API_BASE_URL` in frontend env (example: `http://127.0.0.1:9000`).

### Build for FastAPI serving

```bash
cd frontend
npm install
npm run build
```

After build, FastAPI automatically serves `frontend/dist`.

## Optional Custom CNN Model

Set a trained Keras model at:

- `backend/models/pretrained/accident_cnn.keras`

Or configure a custom path using env var:

- `CNN_MODEL_PATH`

If no custom model is available, the system uses predefined MobileNetV2 feature-based CNN analysis.
If TensorFlow is unavailable, it falls back to a predefined SqueezeNet ONNX CNN model (auto-downloaded on first run), with optical-flow support.

## API Endpoints

- `POST /api/auth/signup` - Register
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/detect` - Upload video and run accident + traffic analysis
- `GET /api/history` - Last 120 analyses for logged-in user
- `GET /api/health` - Service status
- `POST /api/chat/` - AI assistant chat

## Detection Response Highlights

`/api/detect` now returns:

- `accident_detected`
- `confidence`, `confidence_percent`
- `severity`
- `traffic_analysis` with:
  - `average_vehicle_count`
  - `peak_vehicle_count`
  - `average_speed_kmh`
  - `peak_speed_kmh`
  - `traffic_density`
  - `congestion_detected`
  - `anomaly_score`
- `detection_strategy`
- `frame_url`, `frame_index`
- `ai_report`, `email_alert`

## Notes

- TensorFlow installation can be Python-version dependent. The backend is coded to degrade gracefully if TensorFlow is unavailable.
- You can still run detection with optical-flow and traffic analytics even without a custom CNN model file.
- Legacy static frontend files and YOLO artifacts were removed in favor of the React + CNN production path.
