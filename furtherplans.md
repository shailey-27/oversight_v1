# OVERSIGHT - Resume Project Roadmap & Implementation Plan

This document outlines the strategic roadmap to transition the OVERSIGHT application from a hackathon prototype into a robust, production-grade automated governance platform.

## 1. End-to-End Governance & Verification Architecture (The Core Workflow)
To ensure the CCTV AI and other verification tools function meaningfully, OVERSIGHT will implement a structured, multi-stage approval and fund-release pipeline:

**Phase A: Registration & Scheme Proposal**
- An NGO registers and submits details of the Yojana (Scheme) they are implementing.
- They must submit hard data: Maximum Capacity, Expected Daily Beneficiaries, Location (GPS), and Budget layout.

**Phase B: Official Approval & Initial Fund Release**
- A DoSJE Official reviews the proposal on the dashboard.
- Upon approval, the *first tranche* of the fund is released to the NGO. 

**Phase C: Daily Automated Cross-Verification (The "Watchdog")**
- **Mobile App Check-ins:** Beneficiaries and staff mark attendance via a geo-fenced mobile app. This provides `Expected_Occupancy`.
- **CCTV AI Pipeline:** The YOLOv8 computer vision model counts actual humans in the frame and sends this to the backend. This provides `Actual_Occupancy`.
- **Anomaly Detection:** The system continuously compares `Expected_Occupancy` vs `Actual_Occupancy`. If 50 students are checked in via the app but CCTV only detects 10, an anomaly flag is raised.

**Phase D: Invoice Fraud Checking & Subsequent Releases**
- When the NGO submits invoices for the next fund tranche, the system runs ML anomaly detection on the invoices (e.g., checking if the food invoice matches the actual daily average occupancy over the last month).
- Only if the Anomaly Score is low does the next tranche get released. High scores trigger a surprise Video Call inspection.

---

## 2. Fake CCTV AI Pipeline (Computer Vision Implementation)
Since physical CCTV cameras are not available, simulate them using real AI.
- **Implementation**: Create a standalone Python worker using **YOLOv8** (an AI object detection model) and OpenCV.
- **Workflow**: Feed it a downloaded YouTube video of a crowded room. The script uses AI to count the number of people in the frame in real-time. It then fires API requests to the FastAPI backend, inserting counts into the `OccupancyLog` database table.
- **Resume Impact**: Demonstrates the ability to bridge Computer Vision (CV) with a web backend and handle real-time data streams for verification.

## 3. Upgrade Anomaly Engine to Real Machine Learning
Replace the current rule-based scoring engine with actual Machine Learning.
- **Implementation**: Integrate `scikit-learn` into the backend.
- **Workflow**: Train an **Isolation Forest** model (an unsupervised ML algorithm often used in finance for fraud detection) to find anomalies in the NGO data (e.g., attendance vs CCTV gaps, invoice amounts, etc.).
- **Resume Impact**: Showcases capability in building an "Unsupervised Machine Learning pipeline for automated fraud and anomaly detection."

## 4. Implement Genuine WebRTC Video Calls
Transform the stubbed "Video Call" feature into a fully functional communication tool.
- **Implementation**: Use **Socket.io** or a free **Twilio** trial.
- **Workflow**: Make video calls function seamlessly between the desktop dashboard and an inspector's mobile browser using WebRTC for real-time bidirectional media streaming.
- **Resume Impact**: Proves ability to handle real-time peer-to-peer video streaming and socket-based architecture.

## 5. Generative AI Chatbot for Policy (RAG)
Add a smart assistant for inspectors.
- **Implementation**: Integrate OpenAI or Gemini API into the dashboard.
- **Workflow**: Create an "Inspector AI Assistant" utilizing **Retrieval-Augmented Generation (RAG)**. Inspectors can ask questions like, "What is the penalty for missing a fire extinguisher?" and the AI will answer accurately based on parsed government policy PDFs.
- **Resume Impact**: Demonstrates proficiency with modern LLMs, Prompt Engineering, and RAG architectures.

## 6. Location-Verified Mobile App / PWA
Enhance the inspector's field capabilities.
- **Implementation**: Upgrade the Next.js frontend to be a mobile-friendly Progressive Web App (PWA) or create a simple React Native app.
- **Workflow**: Utilize HTML5 Geolocation to ensure inspectors are submitting checklists from the actual GPS coordinates of the institution.

## 7. Real SMS Authentication
Replace the demo OTP system.
- **Implementation**: Integrate an SMS gateway like **Twilio**, **MSG91**, or switch to **Firebase Auth**.
- **Workflow**: Send actual SMS messages to the user's phone for login verification.
