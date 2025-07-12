from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime

from ..database import get_db
from ..models.rca import RCA, RCAStatusHistory
from ..models.alert import Alert, AlertGroup
from ..models.schemas import (
    RCACreate, RCAResponse, RCAUpdate, RCAFilters,
    APIResponse, PaginatedResponse, RCAStatusHistoryResponse
)
from ..services.llm_service import LLMService
from ..services.rag_service import RAGService
from ..services.vector_service import VectorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rca", tags=["rca"])


@router.post("/generate", response_model=APIResponse)
async def generate_rca(
    group_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate RCA for an alert group using LLM and RAG"""
    try:
        # Check if alert group exists
        alert_group = db.query(AlertGroup).filter(AlertGroup.group_id == group_id).first()
        if not alert_group:
            raise HTTPException(status_code=404, detail="Alert group not found")
        
        # Check if RCA already exists
        existing_rca = db.query(RCA).filter(RCA.group_id == group_id).first()
        if existing_rca:
            return APIResponse(
                success=True,
                message="RCA already exists for this group",
                data={"rca_id": existing_rca.rca_id}
            )
        
        # Get alerts in the group
        alerts = db.query(Alert).filter(Alert.group_id == group_id).all()
        if not alerts:
            raise HTTPException(status_code=400, detail="No alerts found in the group")
        
        # Prepare alerts data for analysis
        alerts_data = []
        for alert in alerts:
            alert_data = {
                "alert_id": alert.alert_id,
                "title": alert.title,
                "description": alert.description or "",
                "severity": alert.severity,
                "source_system": alert.source_system,
                "metric_name": alert.metric_name,
                "metric_value": alert.metric_value,
                "threshold": alert.threshold,
                "tags": alert.tags or {},
                "labels": alert.labels or {},
                "created_at": alert.created_at.isoformat() if alert.created_at else "",
                "raw_data": alert.raw_data or {}
            }
            alerts_data.append(alert_data)
        
        # Generate RCA in background
        background_tasks.add_task(
            _generate_rca_task,
            db.bind,  # Pass engine instead of session
            group_id,
            alerts_data
        )
        
        return APIResponse(
            success=True,
            message="RCA generation started",
            data={"group_id": group_id, "status": "generating"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating RCA for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _generate_rca_task(engine, group_id: str, alerts_data: List[dict]):
    """Background task to generate RCA"""
    from sqlalchemy.orm import sessionmaker
    
    try:
        # Create new session for background task
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        try:
            # Initialize services
            llm_service = LLMService()
            rag_service = RAGService()
            
            # Get context from RAG
            context = ""
            if rag_service.is_available():
                context = rag_service.get_context_for_rca_generation(alerts_data)
            
            # Generate RCA using LLM
            rca_result = llm_service.generate_rca(alerts_data, context)
            
            # Create RCA record
            rca = RCA(
                group_id=group_id,
                title=rca_result.get("title", "Alert Group Analysis"),
                root_cause=rca_result.get("root_cause", "Analysis in progress"),
                impact_analysis=rca_result.get("impact_analysis", ""),
                recommended_actions=rca_result.get("recommended_actions", ""),
                affected_systems=rca_result.get("affected_systems", []),
                timeline=rca_result.get("timeline", {}),
                severity=rca_result.get("severity", "medium"),
                confidence_score=rca_result.get("confidence_score", "medium"),
                analysis_method="llm_rag",
                status="open"
            )
            
            db.add(rca)
            db.commit()
            db.refresh(rca)
            
            # Create status history
            status_history = RCAStatusHistory(
                rca_id=rca.rca_id,
                new_status="open",
                changed_by="system",
                change_reason="RCA generated automatically"
            )
            db.add(status_history)
            db.commit()
            
            logger.info(f"RCA {rca.rca_id} generated successfully for group {group_id}")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in background RCA generation: {e}")


@router.get("/", response_model=PaginatedResponse)
async def get_rcas(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[List[str]] = Query(None),
    severity: Optional[List[str]] = Query(None),
    assigned_to: Optional[str] = Query(None),
    search_query: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get RCAs with filtering and pagination"""
    try:
        # Build query
        query = db.query(RCA)
        
        # Apply filters
        if status:
            query = query.filter(RCA.status.in_(status))
        
        if severity:
            query = query.filter(RCA.severity.in_(severity))
        
        if assigned_to:
            query = query.filter(RCA.assigned_to.ilike(f"%{assigned_to}%"))
        
        if search_query:
            query = query.filter(
                RCA.title.ilike(f"%{search_query}%") |
                RCA.root_cause.ilike(f"%{search_query}%")
            )
        
        if start_date:
            query = query.filter(RCA.created_at >= start_date)
        
        if end_date:
            query = query.filter(RCA.created_at <= end_date)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * size
        rcas = query.order_by(RCA.created_at.desc()).offset(offset).limit(size).all()
        
        # Calculate total pages
        total_pages = (total + size - 1) // size
        
        return PaginatedResponse(
            items=[RCAResponse.from_orm(rca) for rca in rcas],
            total=total,
            page=page,
            size=size,
            pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error getting RCAs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rca_id}", response_model=RCAResponse)
async def get_rca(
    rca_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific RCA by ID with alert group details"""
    try:
        rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
        
        if not rca:
            raise HTTPException(status_code=404, detail="RCA not found")
        
        # Load alert group data
        alert_group = db.query(AlertGroup).filter(AlertGroup.group_id == rca.group_id).first()
        
        rca_data = RCAResponse.from_orm(rca)
        if alert_group:
            from ..models.schemas import AlertGroupResponse
            rca_data.alert_group = AlertGroupResponse.from_orm(alert_group)
        
        return rca_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RCA {rca_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{rca_id}", response_model=APIResponse)
async def update_rca(
    rca_id: str,
    rca_update: RCAUpdate,
    changed_by: Optional[str] = Query(None),
    change_reason: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Update an RCA"""
    try:
        rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
        
        if not rca:
            raise HTTPException(status_code=404, detail="RCA not found")
        
        # Store previous status for history
        previous_status = rca.status
        
        # Update fields
        update_data = rca_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rca, field, value)
        
        rca.updated_at = datetime.utcnow()
        
        # If status is being set to closed, set closed_at
        if rca_update.status == "closed":
            rca.closed_at = datetime.utcnow()
        
        # Create status history if status changed
        if rca_update.status and rca_update.status != previous_status:
            status_history = RCAStatusHistory(
                rca_id=rca_id,
                previous_status=previous_status,
                new_status=rca_update.status,
                changed_by=changed_by or "unknown",
                change_reason=change_reason or f"Status changed to {rca_update.status}"
            )
            db.add(status_history)
            
            # If status changed to closed, store in vector DB
            if rca_update.status == "closed":
                vector_service = VectorService()
                vector_service.store_closed_rca(db, rca_id)
        
        db.commit()
        
        return APIResponse(
            success=True,
            message="RCA updated successfully",
            data={"rca_id": rca_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating RCA {rca_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rca_id}/alerts", response_model=APIResponse)
async def get_rca_alerts(
    rca_id: str,
    db: Session = Depends(get_db)
):
    """Get all alerts related to an RCA"""
    try:
        rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
        
        if not rca:
            raise HTTPException(status_code=404, detail="RCA not found")
        
        # Get alerts in the group
        alerts = db.query(Alert).filter(Alert.group_id == rca.group_id).all()
        
        from ..models.schemas import AlertResponse
        alerts_data = [AlertResponse.from_orm(alert) for alert in alerts]
        
        return APIResponse(
            success=True,
            message=f"Found {len(alerts_data)} alerts for RCA",
            data={"alerts": alerts_data}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alerts for RCA {rca_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{rca_id}/history", response_model=APIResponse)
async def get_rca_status_history(
    rca_id: str,
    db: Session = Depends(get_db)
):
    """Get status change history for an RCA"""
    try:
        rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
        
        if not rca:
            raise HTTPException(status_code=404, detail="RCA not found")
        
        history = db.query(RCAStatusHistory).filter(
            RCAStatusHistory.rca_id == rca_id
        ).order_by(RCAStatusHistory.changed_at.desc()).all()
        
        history_data = [RCAStatusHistoryResponse.from_orm(h) for h in history]
        
        return APIResponse(
            success=True,
            message=f"Found {len(history_data)} status changes",
            data={"history": history_data}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RCA history {rca_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{rca_id}", response_model=APIResponse)
async def delete_rca(
    rca_id: str,
    db: Session = Depends(get_db)
):
    """Delete an RCA"""
    try:
        rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
        
        if not rca:
            raise HTTPException(status_code=404, detail="RCA not found")
        
        # Delete status history first (foreign key constraint)
        db.query(RCAStatusHistory).filter(RCAStatusHistory.rca_id == rca_id).delete()
        
        # Delete RCA
        db.delete(rca)
        db.commit()
        
        return APIResponse(
            success=True,
            message="RCA deleted successfully",
            data={"rca_id": rca_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting RCA {rca_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-vectorize", response_model=APIResponse)
async def bulk_vectorize_closed_rcas(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Bulk vectorize closed RCAs that haven't been vectorized yet"""
    try:
        vector_service = VectorService()
        result = vector_service.bulk_store_closed_rcas(db, limit)
        
        return APIResponse(
            success=result.get("successful", 0) > 0,
            message="Bulk vectorization completed",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Error in bulk vectorization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/historical", response_model=APIResponse)
async def search_historical_incidents(
    query: str = Query(..., min_length=3),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Search historical incidents from vector database"""
    try:
        vector_service = VectorService()
        results = vector_service.search_historical_incidents(query, limit)
        
        return APIResponse(
            success=True,
            message=f"Found {len(results)} historical incidents",
            data={"incidents": results}
        )
        
    except Exception as e:
        logger.error(f"Error searching historical incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", response_model=APIResponse)
async def get_rca_stats(
    db: Session = Depends(get_db)
):
    """Get RCA statistics for the dashboard"""
    try:
        # RCA counts by status
        status_stats = {}
        for status in ["open", "in_progress", "closed"]:
            count = db.query(RCA).filter(RCA.status == status).count()
            status_stats[status] = count
        
        # RCA counts by severity
        severity_stats = {}
        for severity in ["critical", "high", "medium", "low"]:
            count = db.query(RCA).filter(RCA.severity == severity).count()
            severity_stats[severity] = count
        
        # Recent RCAs
        recent_rcas = db.query(RCA).order_by(RCA.created_at.desc()).limit(5).all()
        recent_rcas_data = [
            {
                "rca_id": rca.rca_id,
                "title": rca.title,
                "status": rca.status,
                "severity": rca.severity,
                "created_at": rca.created_at
            }
            for rca in recent_rcas
        ]
        
        # Vector DB stats
        vector_service = VectorService()
        vector_stats = vector_service.get_vector_db_stats()
        
        return APIResponse(
            success=True,
            message="RCA statistics retrieved successfully",
            data={
                "total_rcas": sum(status_stats.values()),
                "status_distribution": status_stats,
                "severity_distribution": severity_stats,
                "recent_rcas": recent_rcas_data,
                "vector_db": vector_stats
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting RCA stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
