# Database models and Pydantic event schemas
from sqlalchemy import String, Integer, Float, Boolean, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

# --- SQLAlchemy Declarative Base and Models ---

class Base(DeclarativeBase):
    pass

class Store(Base):
    __tablename__ = "stores"
    store_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Camera(Base):
    __tablename__ = "cameras"
    camera_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class Zone(Base):
    __tablename__ = "zones"
    zone_id: Mapped[str] = mapped_column(String, primary_key=True)
    store_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    zone_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    zone_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_revenue_zone: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)

class TrackedEvent(Base):
    __tablename__ = "tracked_events"
    event_id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    store_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    camera_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    visitor_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    zone_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    dwell_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

class POSTransaction(Base):
    __tablename__ = "pos_transactions"
    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_date: Mapped[str] = mapped_column(String, index=True)
    order_time: Mapped[str] = mapped_column(String, index=True)
    store_id: Mapped[str] = mapped_column(String, index=True)
    product_id: Mapped[str] = mapped_column(String)
    brand_name: Mapped[str] = mapped_column(String)
    total_amount: Mapped[float] = mapped_column(Float)
    
    # Combined timestamp for easier querying
    transaction_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
# --- Pydantic Schemas for Ingestion API ---

class EventInboundSchema(BaseModel):
    event_id: Optional[str] = None
    store_id: Optional[str] = None
    store_code: Optional[str] = None
    camera_id: Optional[str] = None
    visitor_id: Optional[str] = None
    id_token: Optional[str] = None
    track_id: Optional[Any] = None
    event_type: str
    timestamp: Optional[str] = None
    event_timestamp: Optional[str] = None
    event_time: Optional[str] = None
    zone_id: Optional[str] = None
    dwell_ms: Optional[int] = 0
    is_staff: Optional[bool] = False
    gender_pred: Optional[str] = None
    age_pred: Optional[int] = None
    age_bucket: Optional[str] = None
    is_face_hidden: Optional[bool] = None
    group_id: Optional[str] = None
    group_size: Optional[int] = None
    confidence: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None

    # For zone/queue events
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None
    is_revenue_zone: Optional[str] = None
    zone_hotspot_x: Optional[float] = None
    zone_hotspot_y: Optional[float] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    queue_event_id: Optional[str] = None
    queue_join_ts: Optional[str] = None
    queue_served_ts: Optional[str] = None
    queue_exit_ts: Optional[str] = None
    wait_seconds: Optional[int] = None
    queue_position_at_join: Optional[int] = None
    abandoned: Optional[bool] = None
