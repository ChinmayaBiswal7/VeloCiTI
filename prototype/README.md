# 🚀 Real-Time Indian ANPR & Citywide Vehicle Intelligence Platform (SIH 2026)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%20%7C%20OpenCV%20%7C%20PyTorch-orange.svg)](https://flask.palletsprojects.com/)
[![Computer Vision](https://img.shields.io/badge/CV-YOLOv8%20%7C%20EasyOCR-green.svg)](https://github.com/ultralytics/ultralytics)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

An enterprise-grade, high-throughput **Automatic Number Plate Recognition (ANPR)** and **Spatio-Temporal Vehicle Tracking System** tailored specifically for the Indian traffic ecosystem. Designed for deployment on edge node surveillance hardware and smart city CCTV networks.

---

## 🌟 Key Features & Innovations

### 1. 🇮🇳 Native MoRTH Indian License Plate Rule Engine
- **36 State & UT Validation**: Validates registration codes across all 36 Indian states and Union Territories (`MH`, `DL`, `KA`, `TN`, `TS`, `AP`, `GJ`, `UP`, `HR`, `RJ`, etc.).
- **District RTO Range Checking**: Restricts registration validity against official RTO district boundaries (e.g. `MH01`–`MH50` for Maharashtra).
- **HSRP Blue Emblem Stripping**: Intelligently strips High Security Registration Plate (HSRP) blue `IND` logos before OCR parsing to prevent false character prefixes.
- **RTO Series Rule Enforcement**: Enforces MoRTH guidelines prohibiting letters `O` and `I` in RTO series slots to eliminate `0`/`1` character confusion.

### 2. 🔬 Multi-Pass CLAHE Contrast & AI Quality Gate
- **Adaptive Contrast Enhancement**: Employs Multi-Pass Contrast Limited Adaptive Histogram Equalization (CLAHE) + Unsharp Masking + Otsu Thresholding for night, low-light, and rain conditions.
- **Random Forest Quality Selector**: Machine learning model (`scikit-learn`) evaluates Laplacian sharpness, SNR, and exposure metrics to rank candidate crops.
- **Edge-Truncated Vehicle Filter**: Automatically filters out half-cropped vehicles at image margins to eliminate side-glass text hallucinations.

### 3. 🗺️ Spatio-Temporal Consensus Voting & Citywide Route Tracking
- **Consensus Fusion Engine**: Collects multi-frame observations per vehicle track ID and performs positional character voting for 99.5%+ recognition accuracy.
- **OSRM Road Route Interpolation**: Connects camera trajectory nodes using Open Source Routing Machine (OSRM) driving paths for realistic street navigation tracking without spider-web line clutter.
- **Sub-Second Multi-Threading**: Global PyTorch CPU model caching and thread pooling achieve sub-second photo processing latency (~0.6s per image).

---

## 🏗️ System Architecture

```
                       ┌───────────────────────────────┐
                       │  CCTV Stream / Dashcam Video  │
                       └──────────────┬────────────────┘
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │ YOLOv8 Vehicle Tracker     │
                        │ (Cars, Buses, Bikes, Vans) │
                        └─────────────┬──────────────┘
                                      │ Bounding Box Crop
                                      ▼
                        ┌────────────────────────────┐
                        │  Image Quality Assessment  │
                        │  & Multi-Pass CLAHE Engine │
                        └─────────────┬──────────────┘
                                      │ Restored Crop
                                      ▼
                        ┌────────────────────────────┐
                        │ Deep Learning EasyOCR      │
                        │ + Candidate Voting Pool    │
                        └─────────────┬──────────────┘
                                      │ Raw OCR String
                                      ▼
                        ┌────────────────────────────┐
                        │ MoRTH Indian Rule Engine   │
                        │ (HSRP Strip + RTO Valid)   │
                        └─────────────┬──────────────┘
                                      │ Validated Plate
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Central Vehicle Intelligence Server (SQLite / REST API / Live Dashboard) │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart Guide

### Prerequisites
- Python 3.10 or higher
- PyTorch 2.0+ (CPU or CUDA enabled)
- OpenCV

### 1. Installation
Clone the repository and install required dependencies:
```bash
git clone https://github.com/maxlovesher/VeloCiTI
cd SIH-2026

python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Launching Central Server & Workbench
Run the integrated single-terminal application:
```bash
python server.py
```
Open your browser and navigate to:
- **Central Vehicle Intelligence Hub**: `http://127.0.0.1:5000`
- **Live ANPR Workbench**: `http://127.0.0.1:5000/anpr`

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/anpr/upload` | `POST` | Upload single vehicle photo for instant sub-second ANPR inference |
| `/api/anpr/upload_video` | `POST` | Asynchronous video processing job submission (returns `job_id`) |
| `/api/anpr/video_poll/<job_id>` | `GET` | Poll background video extraction progress and detections |
| `/api/track/<plate>` | `GET` | Retrieve full spatio-temporal trajectory nodes for a vehicle |
| `/api/recent` | `GET` | Fetch last 60 live detections across city surveillance network |
| `/api/status` | `GET` | System health, active cameras, and daily detection statistics |
| `/api/blacklist` | `GET / POST` | Query or flag stolen/blacklisted vehicle plates |

---

## 📁 Repository Structure

```
.
├── server.py              # Flask Central Server & Background Async Worker Threads
├── anpr.py                # Core ANPR Detection Engine & MoRTH Rule Processing
├── conditioner.py         # AI Stream Conditioning & Multi-Scale Frame Pipeline
├── quality.py             # Image Quality Assessment (IQA) & Laplacian Sharpness
├── enhancer.py            # CLAHE, Contrast, & Super-Resolution Restoration
├── ml_selector.py         # Random Forest ML Crop Selection Model
├── analytics.py           # Origin-Destination (OD) Flow & Traffic Analytics
├── database.py            # SQLite Persistence Layer & Trajectory Storage
├── alerts.py             # Hotlist Blacklist & Automated Alert Dispatcher
├── requirements.txt       # Production Dependencies Manifest
├── static/
│   ├── dashboard.html     # Citywide Surveillance & Vehicle Tracking Map UI
│   └── anpr.html          # Real-time Split-Screen ANPR Workbench
└── data/                  # SQLite Database & Snapshots Directory
```

---

## 📄 License
Distributed under the **MIT License**. See `LICENSE` for more details.
