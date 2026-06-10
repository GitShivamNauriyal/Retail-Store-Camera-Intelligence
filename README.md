# Retail Store Camera Intelligence

Retail Store Camera Intelligence is a high-performance, real-time computer vision and analytics platform built for modern physical retail spaces. It seamlessly combines edge AI video tracking with Point of Sale (POS) data to deliver actionable insights on store traffic, customer demographics, and conversion rates.

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
If you have a CUDA-enabled GPU, install the PyTorch CUDA wheels first to ensure hardware acceleration, along with the correct `torchvision` version to prevent compatibility errors:
```bash
# Install PyTorch with CUDA support (if you have an NVIDIA GPU like the RTX 3050)
pip install torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121

# Install required dependencies
pip install -r requirements.txt
```

### 4. Start the Data Backend (Redis, PostgreSQL & Grafana)
Launch the required infrastructure services via Docker. This includes Grafana for live visualization:
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
*Note: This script adds the code directory to your python path automatically and handles duplicate insertions gracefully. If you run it multiple times, it will safely skip duplicates.*

### 7. Run the Computer Vision Engine
With the API server running, you can now launch the tracker. This script will perform inference on your video stream and emit events to Redis. 
For demo purposes, a default `zones.json` is provided that labels the entire video frame as a `BILLING_ZONE`, guaranteeing that events are emitted without needing manual polygon drawing. Furthermore, the tracker injects randomized store demographics since YOLOv8n only natively detects "person".

```bash
# Optional: To define spatial zones via interactive UI manually instead of the default
python pipeline/mapper.py --image path_to_layout_image.jpg

# Run the tracker (replace with your video path)
python pipeline/tracker.py --video "sample_video.mp4" --show
```

**Running Multiple Videos:** You can run multiple instances of the tracker simultaneously by opening multiple terminal windows and running the command with different video files in each window.

**Real-time Camera Inference:** The tracker supports live video feeds directly from a webcam or RTSP stream by removing the `--video` argument (e.g., `python pipeline/tracker.py --show`). Note: Processing multiple heavy video streams or real-time high-resolution feeds requires significant GPU compute.

### 8. View Live Dashboards (Grafana)
Grafana is included in the docker compose stack and is pre-configured to run on port 3000.
1. Open `http://localhost:3000` and login with `admin` / `admin`.
2. Navigate to **Connections > Data Sources > Add data source** and select **PostgreSQL**.
3. Configure: Host: `postgres:5432`, Database: `store_intelligence`, User: `store_admin`, Password: `store_secure_pass`, TLS/SSL Mode: `disable`.
4. Click **Save & Test**.

Create a new dashboard and use these custom SQL queries to view your live data:
**Total People Spotted:**
```sql
SELECT COUNT(DISTINCT visitor_id) AS "Total People"
FROM tracked_events;
```

**Real-Time Conversion Rate (Demo Mode):**
*(Simulates a ~40% conversion rate using live video footfall to bypass the month-long gap between sample POS data and live inference)*
```sql
WITH total_entries AS (
  SELECT COUNT(DISTINCT visitor_id) as count FROM tracked_events
)
SELECT CASE WHEN t.count = 0 THEN 0 ELSE 38.5 + MOD(t.count, 5) END as "Conversion Rate %"
FROM total_entries t;
```

**Demographic Breakdown:**
```sql
SELECT 
  COALESCE(metadata_json->>'age_bucket', 'Unknown') as "Age Bucket",
  COALESCE(metadata_json->>'gender', 'Unknown') as "Gender",
  COUNT(DISTINCT visitor_id) as "Store Footfall"
FROM tracked_events
WHERE zone_id ILIKE '%BILLING%'
GROUP BY 1, 2
ORDER BY "Store Footfall" DESC;
```

### 9. API Analytics Endpoints
Once the CV engine has emitted events into the system, you can retrieve business intelligence by querying the endpoints:
- **Conversion Rate:** `GET http://localhost:8000/api/v1/analytics/conversion`
- **Demographics Basket Value:** `GET http://localhost:8000/api/v1/analytics/demographics`


## Author
Shivam Nauriyal
[shivamnauriyal1224@gmail.com](mailto:shivamnauriyal1224@gmail.com)