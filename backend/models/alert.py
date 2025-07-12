from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from ..database import Base


class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(255), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(255), index=True, nullable=True)
    
    # Alert details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False)  # critical, high, medium, low
    source_system = Column(String(100), nullable=False)
    
    # Metadata
    tags = Column(JSON, nullable=True)
    labels = Column(JSON, nullable=True)
    
    # Status
    status = Column(String(50), default="active")  # active, resolved, acknowledged
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Alert specific fields
    metric_name = Column(String(255), nullable=True)
    metric_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    
    # Raw alert data
    raw_data = Column(JSON, nullable=True)
    
    # Relationships
    group_alerts = relationship("AlertGroup", back_populates="alerts")


class AlertGroup(Base):
    __tablename__ = "alert_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(255), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Group details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), nullable=False)
    
    # Group characteristics
    alert_count = Column(Integer, default=0)
    similar_pattern = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), default="active")  # active, grouped, resolved
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    alerts = relationship("Alert", back_populates="group_alerts")
    rca = relationship("RCA", back_populates="alert_group", uselist=False)
