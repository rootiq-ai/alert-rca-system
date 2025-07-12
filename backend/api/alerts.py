from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from ..database import get_db
from ..models.alert import Alert, AlertGroup
from ..models.schemas import (
    AlertCreate, AlertResponse, AlertUpdate, AlertFilters,
    AlertGroupResponse, APIResponse, PaginatedResponse
)
from ..services.alert_grouping import AlertGroupingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", response_model=APIResponse)
async def create_alert(
    alert: AlertCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert and automatically group it"""
    try:
        # Create alert instance
        db_alert = Alert(
            title=alert.title,
            description=alert.description,
            severity=alert.severity,
            source_system=alert.source_system,
            tags=alert.tags,
            labels=alert.labels,
            metric_name=alert.metric_name,
            metric_value=alert.metric_value,
            threshold=alert.threshold,
            raw_data=alert.raw_data,
            status="active"
        )
        
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        
        # Auto-group the alert
        grouping_service = AlertGroupingService()
        group_id = grouping_service.group_alert(db, db_alert)
        
        logger.info(f"Created alert {db_alert.alert_id} and assigned to group {group_id}")
        
        return APIResponse(
            success=True,
            message="Alert created and grouped successfully",
            data={
                "alert_id": db_alert.alert_id,
                "group_id": group_id
            }
        )
        
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def get_alerts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[List[str]] = Query(None),
    status: Optional[List[str]] = Query(None),
    source_system: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get alerts with filtering and pagination"""
    try:
        # Build query
        query = db.query(Alert)
        
        # Apply filters
        if severity:
            query = query.filter(Alert.severity.in_(severity))
        
        if status:
            query = query.filter(Alert.status.in_(status))
        
        if source_system:
            query = query.filter(Alert.source_system.ilike(f"%{source_system}%"))
        
        if search_query:
            query = query.filter(
                Alert.title.ilike(f"%{search_query}%") |
                Alert.description.ilike(f"%{search_query}%")
            )
        
        if start_date:
            query = query.filter(Alert.created_at >= start_date)
        
        if end_date:
            query = query.filter(Alert.created_at <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(size).all()
        
        # Calculate total pages
        total_pages = (total + size - 1) // size
        
        return PaginatedResponse(
            items=[AlertResponse.from_orm(alert) for alert in alerts],
            total=total,
            page=page,
            size=size,
            pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific alert by ID"""
    try:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return AlertResponse.from_orm(alert)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{alert_id}", response_model=APIResponse)
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an alert"""
    try:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Update fields
        update_data = alert_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(alert, field, value)
        
        alert.updated_at = datetime.utcnow()
        
        # If status is being set to resolved, set resolved_at
        if alert_update.status == "resolved":
            alert.resolved_at = datetime.utcnow()
        
        db.commit()
        
        return APIResponse(
            success=True,
            message="Alert updated successfully",
            data={"alert_id": alert_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{alert_id}", response_model=APIResponse)
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db)
):
    """Delete an alert"""
    try:
        alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        db.delete(alert)
        db.commit()
        
        return APIResponse(
            success=True,
            message="Alert deleted successfully",
            data={"alert_id": alert_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/", response_model=PaginatedResponse)
async def get_alert_groups(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    severity: Optional[List[str]] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get alert groups with pagination"""
    try:
        # Build query
        query = db.query(AlertGroup)
        
        # Apply filters
        if severity:
            query = query.filter(AlertGroup.severity.in_(severity))
        
        if status:
            query = query.filter(AlertGroup.status == status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        groups = query.order_by(AlertGroup.created_at.desc()).offset(offset).limit(size).all()
        
        # Calculate total pages
        total_pages = (total + size - 1) // size
        
        # Load alerts for each group
        result_groups = []
        for group in groups:
            group_alerts = db.query(Alert).filter(Alert.group_id == group.group_id).all()
            group_data = AlertGroupResponse.from_orm(group)
            group_data.alerts = [AlertResponse.from_orm(alert) for alert in group_alerts]
            result_groups.append(group_data)
        
        return PaginatedResponse(
            items=result_groups,
            total=total,
            page=page,
            size=size,
            pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error getting alert groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/groups/{group_id}", response_model=AlertGroupResponse)
async def get_alert_group(
    group_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific alert group with its alerts"""
    try:
        group = db.query(AlertGroup).filter(AlertGroup.group_id == group_id).first()
        
        if not group:
            raise HTTPException(status_code=404, detail="Alert group not found")
        
        # Get alerts in the group
        alerts = db.query(Alert).filter(Alert.group_id == group_id).all()
        
        group_data = AlertGroupResponse.from_orm(group)
        group_data.alerts = [AlertResponse.from_orm(alert) for alert in alerts]
        
        return group_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regroup", response_model=APIResponse)
async def regroup_alerts(
    hours_back: int = Query(24, ge=1, le=168),  # Max 1 week
    db: Session = Depends(get_db)
):
    """Regroup alerts from the last N hours"""
    try:
        grouping_service = AlertGroupingService()
        result = grouping_service.regroup_alerts(db, hours_back)
        
        return APIResponse(
            success=result.get("regrouping_completed", False),
            message=f"Regrouping completed for last {hours_back} hours",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error regrouping alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk", response_model=APIResponse)
async def create_bulk_alerts(
    alerts: List[AlertCreate],
    db: Session = Depends(get_db)
):
    """Create multiple alerts at once"""
    try:
        created_alerts = []
        grouping_service = AlertGroupingService()
        
        for alert_data in alerts:
            # Create alert
            db_alert = Alert(
                title=alert_data.title,
                description=alert_data.description,
                severity=alert_data.severity,
                source_system=alert_data.source_system,
                tags=alert_data.tags,
                labels=alert_data.labels,
                metric_name=alert_data.metric_name,
                metric_value=alert_data.metric_value,
                threshold=alert_data.threshold,
                raw_data=alert_data.raw_data,
                status="active"
            )
            
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
            
            # Auto-group the alert
            group_id = grouping_service.group_alert(db, db_alert)
            
            created_alerts.append({
                "alert_id": db_alert.alert_id,
                "group_id": group_id
            })
        
        return APIResponse(
            success=True,
            message=f"Created {len(created_alerts)} alerts successfully",
            data={"created_alerts": created_alerts}
        )
        
    except Exception as e:
        logger.error(f"Error creating bulk alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=APIResponse)
async def get_alert_stats(
    hours_back: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """Get alert statistics for the dashboard"""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Total alerts
        total_alerts = db.query(Alert).filter(Alert.created_at >= cutoff_time).count()
        
        # Alerts by severity
        severity_stats = {}
        for severity in ["critical", "high", "medium", "low"]:
            count = db.query(Alert).filter(
                Alert.created_at >= cutoff_time,
                Alert.severity == severity
            ).count()
            severity_stats[severity] = count
        
        # Alerts by status
        status_stats = {}
        for status in ["active", "acknowledged", "resolved"]:
            count = db.query(Alert).filter(
                Alert.created_at >= cutoff_time,
                Alert.status == status
            ).count()
            status_stats[status] = count
        
        # Alert groups
        total_groups = db.query(AlertGroup).filter(AlertGroup.created_at >= cutoff_time).count()
        
        # Top source systems
        source_systems = db.query(Alert.source_system, db.func.count(Alert.id).label('count')).filter(
            Alert.created_at >= cutoff_time
        ).group_by(Alert.source_system).order_by(db.text('count DESC')).limit(10).all()
        
        return APIResponse(
            success=True,
            message="Alert statistics retrieved successfully",
            data={
                "time_range_hours": hours_back,
                "total_alerts": total_alerts,
                "total_groups": total_groups,
                "severity_distribution": severity_stats,
                "status_distribution": status_stats,
                "top_source_systems": [{"system": sys, "count": count} for sys, count in source_systems]
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
