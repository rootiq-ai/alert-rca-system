from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..database import Base


class RCA(Base):
    __tablename__ = "rca"
    
    id = Column(Integer, primary_key=True, index=True)
    rca_id = Column(String(255), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(255), ForeignKey("alert_groups.group_id"), nullable=False)
    
    # RCA Content
    title = Column(String(500), nullable=False)
    root_cause = Column(Text, nullable=False)
    impact_analysis = Column(Text, nullable=True)
    recommended_actions = Column(Text, nullable=True)
    
    # Additional details
    affected_systems = Column(JSON, nullable=True)
    timeline = Column(JSON, nullable=True)
    severity = Column(String(50), nullable=False)
    
    # Status management
    status = Column(String(50), default="open")  # open, in_progress, closed
    
    # Analysis metadata
    confidence_score = Column(String(50), nullable=True)  # high, medium, low
    analysis_method = Column(String(100), default="llm_rag")
    
    # User interactions
    assigned_to = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Vector storage info
    is_vectorized = Column(Boolean, default=False)
    vector_id = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    alert_group = relationship("AlertGroup", back_populates="rca")
    status_history = relationship("RCAStatusHistory", back_populates="rca")


class RCAStatusHistory(Base):
    __tablename__ = "rca_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    rca_id = Column(String(255), ForeignKey("rca.rca_id"), nullable=False)
    
    # Status change details
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    changed_by = Column(String(255), nullable=True)
    change_reason = Column(Text, nullable=True)
    
    # Timestamp
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    rca = relationship("RCA", back_populates="status_history")
