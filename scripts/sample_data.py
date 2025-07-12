#!/usr/bin/env python3
"""
Sample data generation script for Alert RCA Management System
"""

import sys
import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import random

# Add parent directory to path to import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.database import SessionLocal
from backend.models.alert import Alert, AlertGroup
from backend.models.rca import RCA, RCAStatusHistory
from backend.services.alert_grouping import AlertGroupingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_alerts():
    """Create sample alerts for testing"""
    
    db = SessionLocal()
    
    try:
        logger.info("Creating sample alerts...")
        
        # Sample alert templates
        alert_templates = [
            {
                "title": "High CPU Usage on Web Server",
                "description": "CPU usage has exceeded 85% threshold on web-server-01",
                "severity": "high",
                "source_system": "prometheus",
                "metric_name": "cpu_usage_percent",
                "metric_value": 87.5,
                "threshold": 85.0,
                "tags": {"environment": "production", "service": "web"},
                "labels": {"team": "platform", "alert_type": "resource"}
            },
            {
                "title": "Database Connection Pool Exhausted",
                "description": "Database connection pool has reached maximum capacity",
                "severity": "critical",
                "source_system": "application_logs",
                "metric_name": "db_connections_active",
                "metric_value": 100,
                "threshold": 95,
                "tags": {"environment": "production", "service": "database"},
                "labels": {"team": "backend", "alert_type": "availability"}
            },
            {
                "title": "Disk Space Low on Storage Server",
                "description": "Available disk space is below 10% on storage-server-02",
                "severity": "medium",
                "source_system": "nagios",
                "metric_name": "disk_free_percent",
                "metric_value": 8.5,
                "threshold": 10.0,
                "tags": {"environment": "production", "service": "storage"},
                "labels": {"team": "infrastructure", "alert_type": "resource"}
            },
            {
                "title": "API Response Time Degraded",
                "description": "Average API response time has increased significantly",
                "severity": "medium",
                "source_system": "newrelic",
                "metric_name": "api_response_time_ms",
                "metric_value": 2500,
                "threshold": 2000,
                "tags": {"environment": "production", "service": "api"},
                "labels": {"team": "backend", "alert_type": "performance"}
            },
            {
                "title": "Memory Usage High on Application Server",
                "description": "Memory usage has exceeded warning threshold",
                "severity": "medium",
                "source_system": "prometheus",
                "metric_name": "memory_usage_percent",
                "metric_value": 78.2,
                "threshold": 75.0,
                "tags": {"environment": "production", "service": "application"},
                "labels": {"team": "platform", "alert_type": "resource"}
            },
            {
                "title": "SSL Certificate Expiring Soon",
                "description": "SSL certificate for api.example.com expires in 7 days",
                "severity": "low",
                "source_system": "certificate_monitor",
                "metric_name": "cert_days_remaining",
                "metric_value": 7,
                "threshold": 30,
                "tags": {"environment": "production", "service": "security"},
                "labels": {"team": "security", "alert_type": "maintenance"}
            }
        ]
        
        created_alerts = []
        
        # Create multiple instances of each template with variations
        for i in range(15):  # Create 15 alerts
            template = random.choice(alert_templates)
            
            # Add some variation
            base_time = datetime.utcnow() - timedelta(hours=random.randint(1, 48))
            
            alert = Alert(
                title=template["title"] + (f" #{i+1}" if i % 3 == 0 else ""),
                description=template["description"],
                severity=template["severity"],
                source_system=template["source_system"],
                metric_name=template["metric_name"],
                metric_value=template["metric_value"] + random.uniform(-5, 5),
                threshold=template["threshold"],
                tags=template["tags"],
                labels=template["labels"],
                status="active" if random.random() > 0.3 else random.choice(["acknowledged", "resolved"]),
                created_at=base_time
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            created_alerts.append(alert)
            logger.info(f"Created alert: {alert.title} (ID: {alert.alert_id})")
        
        logger.info(f"Created {len(created_alerts)} sample alerts")
        
        return created_alerts
        
    except Exception as e:
        logger.error(f"Error creating sample alerts: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def group_sample_alerts():
    """Group the sample alerts"""
    
    db = SessionLocal()
    
    try:
        logger.info("Grouping sample alerts...")
        
        # Get all ungrouped alerts
        alerts = db.query(Alert).filter(Alert.group_id.is_(None)).all()
        
        if not alerts:
            logger.warning("No ungrouped alerts found")
            return
        
        grouping_service = AlertGroupingService()
        grouped_count = 0
        
        for alert in alerts:
            group_id = grouping_service.group_alert(db, alert)
            if group_id:
                grouped_count += 1
        
        logger.info(f"Grouped {grouped_count} alerts")
        
    except Exception as e:
        logger.error(f"Error grouping alerts: {e}")
        raise
    finally:
        db.close()


def create_sample_rcas():
    """Create sample RCAs for alert groups"""
    
    db = SessionLocal()
    
    try:
        logger.info("Creating sample RCAs...")
        
        # Get alert groups without RCAs
        alert_groups = db.query(AlertGroup).all()
        
        sample_rcas = [
            {
                "title": "High Resource Utilization Due to Memory Leak",
                "root_cause": "Analysis indicates a memory leak in the application server's session management module. The leak is caused by improper cleanup of session objects when users disconnect abruptly, leading to accumulation of orphaned session data.",
                "impact_analysis": "The memory leak causes gradual degradation of system performance, affecting response times and potentially leading to service outages. Approximately 1000 active users experienced slower response times during peak hours.",
                "recommended_actions": "1. Implement proper session cleanup mechanisms\n2. Add monitoring for session object lifecycle\n3. Restart affected services during maintenance window\n4. Update session management library to latest version\n5. Implement circuit breaker pattern for session handling",
                "affected_systems": ["web-server-01", "application-server-02", "load-balancer"],
                "confidence_score": "high",
                "severity": "high"
            },
            {
                "title": "Database Performance Degradation",
                "root_cause": "Database performance issues stem from missing indexes on frequently queried tables and a recent increase in data volume. Query execution times have increased by 300% over the past week.",
                "impact_analysis": "Users experience slow page loads and timeouts. API endpoints dependent on database queries show increased latency. Estimated impact: 15% reduction in user satisfaction scores.",
                "recommended_actions": "1. Add missing indexes on user_sessions and transaction_logs tables\n2. Optimize slow queries identified in performance logs\n3. Implement query caching for frequently accessed data\n4. Consider database partitioning for large tables\n5. Schedule regular database maintenance windows",
                "affected_systems": ["postgres-primary", "api-gateway", "web-application"],
                "confidence_score": "high",
                "severity": "critical"
            },
            {
                "title": "Storage Capacity Issues",
                "root_cause": "Rapid growth in log file generation due to increased debug logging level left enabled in production. Log rotation policies were not properly configured, causing disk space consumption to exceed normal levels.",
                "impact_analysis": "Storage servers approaching capacity limits, potentially affecting backup operations and new data ingestion. Risk of service disruption if storage becomes full.",
                "recommended_actions": "1. Immediately adjust logging levels to WARNING in production\n2. Implement proper log rotation and archival policies\n3. Clean up old log files after backup\n4. Set up automated alerts for disk space monitoring\n5. Review and optimize log retention policies",
                "affected_systems": ["storage-server-02", "backup-system", "log-aggregator"],
                "confidence_score": "medium",
                "severity": "medium"
            }
        ]
        
        created_rcas = []
        
        for i, group in enumerate(alert_groups[:len(sample_rcas)]):
            rca_template = sample_rcas[i % len(sample_rcas)]
            
            rca = RCA(
                group_id=group.group_id,
                title=rca_template["title"],
                root_cause=rca_template["root_cause"],
                impact_analysis=rca_template["impact_analysis"],
                recommended_actions=rca_template["recommended_actions"],
                affected_systems=rca_template["affected_systems"],
                severity=rca_template["severity"],
                confidence_score=rca_template["confidence_score"],
                analysis_method="llm_rag",
                status=random.choice(["open", "in_progress", "closed"]),
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 24))
            )
            
            if rca.status == "closed":
                rca.closed_at = rca.created_at + timedelta(hours=random.randint(1, 48))
            
            db.add(rca)
            db.commit()
            db.refresh(rca)
            
            # Create status history
            status_history = RCAStatusHistory(
                rca_id=rca.rca_id,
                new_status="open",
                changed_by="system",
                change_reason="RCA created automatically"
            )
            db.add(status_history)
            
            if rca.status != "open":
                status_history_2 = RCAStatusHistory(
                    rca_id=rca.rca_id,
                    previous_status="open",
                    new_status=rca.status,
                    changed_by="analyst",
                    change_reason=f"Status changed to {rca.status}",
                    changed_at=rca.created_at + timedelta(hours=1)
                )
                db.add(status_history_2)
            
            db.commit()
            
            created_rcas.append(rca)
            logger.info(f"Created RCA: {rca.title} (ID: {rca.rca_id})")
        
        logger.info(f"Created {len(created_rcas)} sample RCAs")
        
        return created_rcas
        
    except Exception as e:
        logger.error(f"Error creating sample RCAs: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def create_all_sample_data():
    """Create all sample data"""
    
    try:
        logger.info("Creating all sample data...")
        
        # Create alerts
        alerts = create_sample_alerts()
        
        # Group alerts
        group_sample_alerts()
        
        # Create RCAs
        rcas = create_sample_rcas()
        
        logger.info("Sample data creation completed successfully!")
        logger.info(f"Created {len(alerts)} alerts and {len(rcas)} RCAs")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        sys.exit(1)


def clear_all_data():
    """Clear all data from the database"""
    
    db = SessionLocal()
    
    try:
        logger.warning("Clearing all data from database...")
        
        # Delete in correct order due to foreign key constraints
        db.query(RCAStatusHistory).delete()
        db.query(RCA).delete()
        db.query(Alert).delete()
        db.query(AlertGroup).delete()
        
        db.commit()
        
        logger.info("All data cleared successfully!")
        
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Sample data generation script")
    parser.add_argument(
        "--clear", 
        action="store_true", 
        help="Clear all existing data"
    )
    parser.add_argument(
        "--alerts-only", 
        action="store_true", 
        help="Create only sample alerts"
    )
    parser.add_argument(
        "--rcas-only", 
        action="store_true", 
        help="Create only sample RCAs"
    )
    
    args = parser.parse_args()
    
    if args.clear:
        confirmation = input("Are you sure you want to clear all data? (yes/no): ")
        if confirmation.lower() == 'yes':
            clear_all_data()
        else:
            logger.info("Data clearing cancelled")
    elif args.alerts_only:
        create_sample_alerts()
        group_sample_alerts()
    elif args.rcas_only:
        create_sample_rcas()
    else:
        create_all_sample_data()
