# Architecture Design - Store Intelligence System

Overview of the computer vision and ingestion system architecture.

## System Architecture

```mermaid
graph TD
    V[CCTV Video Streams] --> CV[Python CV Pipeline]
    CV --> R[Redis Streams Ingestion Buffer]
    R --> W[FastAPI Background Worker]
    W --> PG[PostgreSQL DB]
    POS[POS Transactions CSV] --> W
    PG --> G[Grafana Dashboard]
    PG --> API[FastAPI REST Endpoints]
```

## AI-Assisted Decisions

*(To be compiled dynamically as the project develops)*
