# Architectural Decisions & Trade-Offs

Detailed justification of technical choices made during the challenge.

## 1. Detection Model Selection

- **Option A**: YOLOv8 Nano (Selected)
- **Option B**: YOLOv8 Medium / Large
- **Option C**: RT-DETR

*Rationale:* ...

## 2. Event Schema Design

*Rationale:* ...

## 3. Ingestion and Database Choice

- **Option A**: FastAPI + Redis Streams + PostgreSQL (Selected)
- **Option B**: direct write to SQLite
- **Option C**: Kafka message bus

*Rationale:* ...
