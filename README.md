# Apex Retail Store Intelligence API

Apex Retail is a high-performance, real-time computer vision and analytics platform built for modern physical retail spaces. It seamlessly combines edge AI video tracking with Point of Sale (POS) data to deliver actionable insights on store traffic, customer demographics, and conversion rates.

## Features
- **Real-Time Object Tracking:** Leverages YOLOv8n and ByteTrack to track visitors across customized spatial polygons.
- **Event-Driven Ingestion:** Uses Redis Streams and FastAPI background workers for unblocked, high-throughput database inserts.
- **Fuzzy Correlation Engine:** A PostgreSQL-backed temporal join that maps visual demographic data to POS revenue within a 3-minute window of uncertainty.
- **Business Intelligence API:** Fully asynchronous REST API serving real-time conversion rates and average order values grouped by demographics.

---

## 🚀 Quick Start Guide

Follow these steps to deploy and evaluate the system locally.

### 1. Pre-requisites
- **Python 3.11+** installed on your system.
- **Docker Desktop** installed and running.
- (Optional but recommended) An NVIDIA GPU with updated drivers for CUDA support.

### 2. Environment Setup
Navigate to the root directory and create a virtual environment:
```bash
cd Code
python -m venv venv
```

Activate the virtual environment:
- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **Linux/Mac:** `source venv/bin/activate`

### 3. Install Dependencies
If you have a CUDA-enabled GPU, install the PyTorch CUDA wheels first, then install the remaining requirements:
```bash
# Install required dependencies
pip install -r requirements.txt
```

### 4. Start the Data Backend (Redis & PostgreSQL)
Launch the required infrastructure services via Docker:
```bash
docker compose up -d
```
*Note: PostgreSQL is mapped to host port `5433` to prevent conflicts with local native Postgres installations.*

### 5. Run the Ingestion API
Start the FastAPI server. This will automatically initialize the database schema and spawn the Redis background worker.
```bash
uvicorn app.main:app --reload
```
You can verify the API is running and connected to the backend by visiting: `http://localhost:8000/api/v1/health`

### 6. Ingest Sample POS Data
In a new terminal (with the virtual environment activated), load the sample POS transactions into the database:
```bash
python app/ingest_pos.py --csv "..\dataset_resource\POS - sample transactionsb1e826f.csv"
```

### 7. Run the Computer Vision Engine
With the API server running, you can now launch the tracker. This script will perform inference on your video stream and emit events to Redis.
```bash
# Optional: To define spatial zones via interactive UI
python pipeline/mapper.py --image path_to_layout_image.jpg

# Run the tracker
python pipeline/tracker.py --video path_to_video.mp4 --show
```

### 8. View Analytics
Once the CV engine has emitted events into the system, you can retrieve business intelligence by querying the endpoints:
- **Conversion Rate:** `GET http://localhost:8000/api/v1/analytics/conversion`
- **Demographics Basket Value:** `GET http://localhost:8000/api/v1/analytics/demographics`
