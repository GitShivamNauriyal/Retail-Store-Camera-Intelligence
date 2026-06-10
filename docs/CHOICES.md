# Architectural Choices & Justifications

Building an edge-capable Store Intelligence system requires carefully balancing performance, memory constraints, and data reliability. Below are the core technical choices we made and why.

## 1. Why PostgreSQL over SQLite?
While SQLite is simpler to set up, it natively employs database-level or table-level locking during writes. In our system, the CV pipeline is constantly streaming hundreds of tracking events per minute, which would result in severe lock contention in SQLite, dropping events or bottlenecking the FastAPI worker. 
**PostgreSQL** was chosen because it allows high-concurrency asynchronous writes without blocking reads. Furthermore, our Business Intelligence endpoints (like Conversion Rate and Demographics) require complex temporal queries. PostgreSQL natively supports advanced date/time math (like `EXTRACT(EPOCH FROM ...)`) enabling our highly efficient, database-level fuzzy time-series joining.

## 2. Why Redis Streams?
We introduced **Redis Streams** as an intermediary message queue between the CV pipeline and the database. 
- **Shock Absorber:** The CV engine produces data at varying burst rates (e.g., when a crowd enters). The API database might momentarily lag during complex read queries. Redis acts as a backpressure queue, buffering the events in memory.
- **Frame Rate Protection:** If the CV script had to wait for a database acknowledgment on every bounding box update, the video frame rate would plummet. By offloading events to Redis asynchronously, the tracker never drops frames waiting on I/O.

## 3. Why YOLOv8n (Nano)?
Our hardware constraint required deploying the entire stack on an 8GB RAM host machine with a consumer-grade GPU. 
- **VRAM Constraints:** Larger object detection models (like YOLOv8x or YOLOv10) would consume excessive Video RAM, starving the ByteTrack multi-object tracking algorithm and the OS itself. 
- **Speed over Perfection:** In a retail tracking environment, the goal is high FPS consistency rather than perfect precision on a single frame. Missing a person in one frame is acceptable because the ByteTrack tracker maintains identity history. **YOLOv8n** is highly optimized for edge hardware, ensuring real-time inference without memory exhaustion.

## 4. Why Grafana for the Frontend UI?
Building a custom React or Vue frontend for a hackathon often diverts critical time away from the core Machine Learning and backend engineering challenges. 
**Grafana** natively connects to PostgreSQL and allows for complex SQL-driven visualizations out-of-the-box. By leveraging Grafana, we eliminated the need to write custom charting UI components, allowing the database queries to handle the heavy lifting for real-time Conversion Rate and Demographic rendering.

## 5. Why Inject Mock Demographics for the Demo?
The problem statement required demographic aggregation (Age and Gender). While advanced models (like DeepFace or specialized MobileNets) can extract demographics, they are extremely slow and would bottleneck the 8GB RAM hardware constraint alongside YOLOv8. 
For this hackathon implementation, we deployed the highly efficient YOLOv8n (which only detects `person`) and injected **mock store demographics** into the event payload. This architectural choice proves that our database schema, event pipeline, and analytics queries fully support demographic aggregation, without melting the edge hardware during the live demonstration.
