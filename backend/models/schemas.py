from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class RCAStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


# Alert Schemas
class AlertBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: AlertSeverity
    source_system: str
    tags: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[AlertSeverity] = None
    status: Optional[AlertStatus] = None
    tags: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, Any]] = None


class AlertResponse(AlertBase):
    id: int
    alert_id: str
    group_id: Optional[str] = None
    status: AlertStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Alert Group Schemas
class AlertGroupBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: AlertSeverity


class AlertGroupCreate(AlertGroupBase):
    pass


class AlertGroupResponse(AlertGroupBase):
    id: int
    group_id: str
    alert_count: int
    similar_pattern: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    alerts: List[AlertResponse] = []

    class Config:
        from_attributes = True


# RCA Schemas
class RCABase(BaseModel):
    title: str
    root_cause: str
    impact_analysis: Optional[str] = None
    recommended_actions: Optional[str] = None
    affected_systems: Optional[List[str]] = None
    timeline: Optional[Dict[str, Any]] = None
    severity: AlertSeverity
    confidence_score: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class RCACreate(RCABase):
    group_id: str


class RCAUpdate(BaseModel):
    title: Optional[str] = None
    root_cause: Optional[str] = None
    impact_analysis: Optional[str] = None
    recommended_actions: Optional[str] = None
    status: Optional[RCAStatus] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class RCAResponse(RCABase):
    id: int
    rca_id: str
    group_id: str
    status: RCAStatus
    analysis_method: str
    is_vectorized: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    alert_group: Optional[AlertGroupResponse] = None

    class Config:
        from_attributes = True


# Status History Schema
class RCAStatusHistoryResponse(BaseModel):
    id: int
    rca_id: str
    previous_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None
    changed_at: datetime

    class Config:
        from_attributes = True


# Filter and Search Schemas
class AlertFilters(BaseModel):
    severity: Optional[List[AlertSeverity]] = None
    status: Optional[List[AlertStatus]] = None
    source_system: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_query: Optional[str] = None


class RCAFilters(BaseModel):
    status: Optional[List[RCAStatus]] = None
    severity: Optional[List[AlertSeverity]] = None
    assigned_to: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_query: Optional[str] = None


# API Response Schemas
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
