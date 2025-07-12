import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import hashlib

from ..models.alert import Alert, AlertGroup
from ..config import settings

logger = logging.getLogger(__name__)


class AlertGroupingService:
    def __init__(self):
        # Initialize sentence transformer for similarity calculation
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.similarity_threshold = settings.similarity_threshold
        self.grouping_window = timedelta(minutes=settings.alert_grouping_window_minutes)

    def group_alert(self, db: Session, alert: Alert) -> Optional[str]:
        """
        Group an alert with existing alert groups or create a new group
        
        Args:
            db: Database session
            alert: Alert to be grouped
            
        Returns:
            group_id: ID of the group the alert was assigned to
        """
        try:
            # Find recent alerts within the grouping window
            cutoff_time = datetime.utcnow() - self.grouping_window
            recent_alerts = db.query(Alert).filter(
                Alert.created_at >= cutoff_time,
                Alert.id != alert.id,
                Alert.status == "active"
            ).all()

            if not recent_alerts:
                # No recent alerts, create new group
                return self._create_new_group(db, alert)

            # Find the best matching group
            best_group_id = self._find_best_matching_group(db, alert, recent_alerts)
            
            if best_group_id:
                # Add alert to existing group
                self._add_to_existing_group(db, alert, best_group_id)
                return best_group_id
            else:
                # No similar group found, create new group
                return self._create_new_group(db, alert)

        except Exception as e:
            logger.error(f"Error grouping alert {alert.alert_id}: {e}")
            return self._create_new_group(db, alert)

    def _find_best_matching_group(self, db: Session, alert: Alert, recent_alerts: List[Alert]) -> Optional[str]:
        """Find the best matching group for the alert"""
        
        # Get unique group IDs from recent alerts
        group_ids = list(set([a.group_id for a in recent_alerts if a.group_id]))
        
        if not group_ids:
            return None

        alert_text = self._create_alert_text(alert)
        alert_embedding = self.model.encode([alert_text])

        best_similarity = 0
        best_group_id = None

        for group_id in group_ids:
            # Get alerts in this group
            group_alerts = [a for a in recent_alerts if a.group_id == group_id]
            
            # Calculate similarity with group
            group_similarity = self._calculate_group_similarity(alert_embedding, group_alerts)
            
            if group_similarity > best_similarity and group_similarity >= self.similarity_threshold:
                best_similarity = group_similarity
                best_group_id = group_id

        return best_group_id

    def _calculate_group_similarity(self, alert_embedding: np.ndarray, group_alerts: List[Alert]) -> float:
        """Calculate similarity between alert and a group of alerts"""
        
        group_texts = [self._create_alert_text(alert) for alert in group_alerts]
        group_embeddings = self.model.encode(group_texts)
        
        # Calculate similarities
        similarities = cosine_similarity(alert_embedding, group_embeddings)[0]
        
        # Return average similarity
        return np.mean(similarities)

    def _create_alert_text(self, alert: Alert) -> str:
        """Create text representation of alert for similarity calculation"""
        
        text_parts = [
            alert.title,
            alert.description or "",
            alert.source_system,
            alert.metric_name or "",
            alert.severity
        ]
        
        # Add tags and labels
        if alert.tags:
            text_parts.extend([f"{k}:{v}" for k, v in alert.tags.items()])
        
        if alert.labels:
            text_parts.extend([f"{k}:{v}" for k, v in alert.labels.items()])
        
        return " ".join(filter(None, text_parts))

    def _create_new_group(self, db: Session, alert: Alert) -> str:
        """Create a new alert group"""
        
        # Generate group ID
        group_id = self._generate_group_id(alert)
        
        # Create alert group
        alert_group = AlertGroup(
            group_id=group_id,
            title=f"Alert Group: {alert.title[:100]}",
            description=f"Automatically created group for alerts similar to: {alert.title}",
            severity=alert.severity,
            alert_count=1,
            similar_pattern=self._extract_pattern(alert),
            status="active"
        )
        
        db.add(alert_group)
        
        # Assign alert to group
        alert.group_id = group_id
        
        db.commit()
        
        logger.info(f"Created new alert group {group_id} for alert {alert.alert_id}")
        return group_id

    def _add_to_existing_group(self, db: Session, alert: Alert, group_id: str):
        """Add alert to existing group"""
        
        # Find the group
        alert_group = db.query(AlertGroup).filter(AlertGroup.group_id == group_id).first()
        
        if alert_group:
            # Update group
            alert_group.alert_count += 1
            alert_group.updated_at = datetime.utcnow()
            
            # Update severity if this alert is more severe
            severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            if severity_order.get(alert.severity, 0) > severity_order.get(alert_group.severity, 0):
                alert_group.severity = alert.severity
            
            # Assign alert to group
            alert.group_id = group_id
            
            db.commit()
            
            logger.info(f"Added alert {alert.alert_id} to existing group {group_id}")

    def _generate_group_id(self, alert: Alert) -> str:
        """Generate a unique group ID based on alert characteristics"""
        
        # Use alert characteristics to generate consistent group ID
        group_data = f"{alert.source_system}_{alert.severity}_{alert.metric_name or 'unknown'}"
        hash_object = hashlib.md5(group_data.encode())
        base_id = hash_object.hexdigest()[:8]
        
        # Add timestamp to ensure uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
        return f"group_{base_id}_{timestamp}"

    def _extract_pattern(self, alert: Alert) -> str:
        """Extract pattern from alert for similarity matching"""
        
        patterns = []
        
        # Add source system pattern
        patterns.append(f"source:{alert.source_system}")
        
        # Add severity pattern
        patterns.append(f"severity:{alert.severity}")
        
        # Add metric pattern if available
        if alert.metric_name:
            patterns.append(f"metric:{alert.metric_name}")
        
        # Add common words from title
        title_words = alert.title.lower().split()
        common_words = [word for word in title_words if len(word) > 3][:3]
        if common_words:
            patterns.append(f"keywords:{','.join(common_words)}")
        
        return "|".join(patterns)

    def regroup_alerts(self, db: Session, hours_back: int = 24) -> Dict[str, Any]:
        """
        Regroup alerts from the last N hours
        
        Args:
            db: Database session
            hours_back: How many hours back to regroup
            
        Returns:
            Dict with regrouping statistics
        """
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            alerts = db.query(Alert).filter(
                Alert.created_at >= cutoff_time,
                Alert.status == "active"
            ).order_by(Alert.created_at).all()

            # Reset group assignments
            for alert in alerts:
                alert.group_id = None
            
            db.commit()

            # Regroup alerts
            grouped_count = 0
            new_groups = 0
            
            for alert in alerts:
                if not alert.group_id:  # Only process ungrouped alerts
                    group_id = self.group_alert(db, alert)
                    if group_id:
                        grouped_count += 1
                        # Check if this is a new group
                        group_alerts = db.query(Alert).filter(Alert.group_id == group_id).count()
                        if group_alerts == 1:
                            new_groups += 1

            return {
                "processed_alerts": len(alerts),
                "grouped_alerts": grouped_count,
                "new_groups": new_groups,
                "regrouping_completed": True
            }

        except Exception as e:
            logger.error(f"Error regrouping alerts: {e}")
            return {
                "error": str(e),
                "regrouping_completed": False
            }
