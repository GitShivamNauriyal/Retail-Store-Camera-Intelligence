# System Design Architecture

## Overview
The Retail Store Camera Intelligence API is designed as a highly scalable, decoupled, and event-driven architecture. This architecture separates the computationally expensive Computer Vision (CV) inference tasks from the asynchronous data ingestion and analytics backend, ensuring the system remains responsive, fault-tolerant, and performant on edge hardware.

## Event-Driven Architecture

Our pipeline consists of four distinct stages:

1. **Python Native Edge Computer Vision:** 
   The video streams are processed locally by our Tracker module (`pipeline/tracker.py`) using PyTorch, YOLOv8, and ByteTrack. By running the CV engine as a standalone process, we ensure that deep learning inference is not blocked by database I/O.
2. **Redis Stream:** 
   As the Tracker identifies events (e.g., crossing a spatial boundary into a billing zone), it immediately emits JSON payloads to a Redis stream (`store_events_stream`). Redis serves as an ultra-fast, in-memory message broker that decouples the CV producer from the API consumer.
3. **FastAPI Background Worker:** 
   A lightweight, asynchronous background task runs within the FastAPI lifecycle (`app/ingestion.py`). It continuously polls the Redis stream (via XREAD) for new events, normalizes the data schema on the fly, and batches the inserts.
4. **PostgreSQL Data Layer:** 
   The asynchronous worker performs bulk upserts into the PostgreSQL database. The business intelligence routes then query this relational data to serve real-time analytics.
5. **Live Grafana Visualization:**
   A pre-configured Grafana instance connects directly to the PostgreSQL data layer to render real-time dashboards containing Footfall, Conversion Rates, and Demographic Breakdowns without imposing extra load on the FastAPI worker.

## Handling Real-World Uncertainty

In a physical retail environment, cameras are rarely perfect, and store layouts are complex. We handle this spatial and temporal uncertainty using two main strategies:

### 1. Spatial Polygon Mapping
Traditional object tracking relies on bounding box overlaps or simple grid coordinates, which fail in uniquely shaped store layouts. We built an interactive mapping tool (`pipeline/mapper.py`) that allows operators to draw custom polygon boundaries around regions of interest (e.g., the Billing Queue or Lipstick Aisle) over an image of the physical store layout.
During live tracking, we calculate the bottom-center coordinate of a customer's bounding box (their physical "footprint") and use point-in-polygon geometry (`cv2.pointPolygonTest`) to robustly determine zone presence, eliminating noise from occlusions or angled camera views.

### 2. Temporal Fuzzy Joining
Linking visual tracking data with Point of Sale (POS) transactions is complex because:
1. Camera clocks and POS system clocks are almost never perfectly synchronized.
2. The exact moment a person is standing in the "Billing" zone is inherently earlier or slightly later than the exact moment the POS receipt is finalized.

To calculate accurate Store Conversion Rates, we implemented a **+/- 3 Minute Fuzzy Temporal Join** directly within PostgreSQL. When our API calculates conversions (`GET /api/v1/analytics/conversion`), it joins `tracked_events` and `pos_transactions` with the following rule:
- The customer must have been physically detected in a billing/checkout zone.
- We extract the absolute time difference in seconds between the camera event and the POS transaction using PostgreSQL's `EPOCH` function.
- We successfully link the records if the difference is `<= 180` seconds (3 minutes).

This probabilistic matching overcomes real-world friction and allows us to accurately map demographic predictions (age, gender) to actual revenue (Average Order Value).

## Hackathon Demo Constraints & Injections

For the purposes of a seamless live demonstration without manual pre-configuration:
1. **Unified Zones:** A default `zones.json` file is utilized which classifies the entire camera frame as a `BILLING_ZONE`, ensuring immediate data flow into the dashboard without the manual polygon tracing step.
2. **Mock Demographics:** Since YOLOv8n only natively identifies the "person" class and lacks age/gender estimators, realistic mock demographic attributes (weighted appropriately) are injected by the tracker in real-time.
3. **Demo Query Mode:** The historical POS sample data (from April 2026) cannot strictly fuzzy-match against the live video feed processing time (June 2026) within a 3-minute window. To successfully demonstrate the architecture, the Grafana live queries compute the ratios probabilistically from the real-time footfall.
