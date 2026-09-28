# OVERSIGHT 🛡️
**Operational Vision & Evidence-based Real-time Smart Inspection & Governance Tracking**

OVERSIGHT is a comprehensive, AI-powered governance and inspection platform built for the Ministry of Social Justice & Empowerment. It transforms manual, trust-based NGO monitoring into a structured, data-driven, and fraud-resistant ecosystem.

![Dashboard Preview](https://via.placeholder.com/1000x500.png?text=OVERSIGHT+Dashboard+Preview)

## 🚀 Key Features

* **End-to-End Governance Pipeline**: Structured tracking of NGO proposals, official approvals, and automated fund tranche releases based on verifiable evidence.
* **Fake CCTV AI Pipeline**: A local Computer Vision worker running **YOLOv8** that detects humans in a physical space, counts them, and broadcasts the live occupancy to the dashboard via WebSockets.
* **Real-time Monitoring Dashboard**: Built with Next.js, featuring dynamic risk scoring, live alerts, and a fluid Day/Night mode.
* **Automated Cross-Verification**: The system automatically cross-references `Expected_Occupancy` (from geofenced mobile app check-ins) against `Actual_Occupancy` (from the YOLOv8 CCTV feed) to instantly flag anomalies.
* **WebRTC Surprise Video Calls**: Officials can initiate one-click, surprise live video verification calls to NGO admins.
* **Robust FastAPI Backend**: High-performance Python backend managing Postgres databases, WebSocket connections, and complex business logic.

## 🏗️ Architecture (Monorepo)

OVERSIGHT is structured as a modern Monorepo:
* **`/apps/dashboard`**: The Frontend. Built with Next.js 14, React, and native CSS for high-performance UI/UX. (Deployable to Vercel).
* **`/apps/api`**: The Backend. Built with FastAPI (Python), SQLAlchemy, and PostgreSQL. Handles WebSockets and REST APIs. (Deployable to Render).
* **`/apps/cctv_worker`**: The AI Worker. A standalone Python script utilizing `ultralytics` (YOLOv8) and OpenCV to process local video feeds and transmit data to the API.

## ⚙️ Getting Started

### 1. Backend (FastAPI)
```bash
cd apps/api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend (Next.js)
```bash
cd apps/dashboard
npm install
npm run dev
```
Access the dashboard at `http://localhost:3000`.

### 3. CCTV AI Worker
```bash
cd apps/cctv_worker
pip install -r requirements.txt
python camera_simulator.py YOUR_INSTITUTION_ID
```
*(Ensure you have a `sample.mp4` video in the folder or change the script to use your webcam).*

## 🔮 Future Roadmap
* **Machine Learning Fraud Engine**: Upgrading the rule-based anomaly detector to an **Isolation Forest** unsupervised ML model.
* **Generative AI Chatbot (RAG)**: An inspector assistant capable of answering complex policy questions via parsed government PDFs.
* **Location-Verified PWA**: Upgrading the field app to enforce HTML5 GPS tracking during checklist submissions.
* **Real SMS Auth**: Replacing the demo OTP system with Twilio/MSG91 integration.

---
*Built for the Smart India Hackathon 2026*
