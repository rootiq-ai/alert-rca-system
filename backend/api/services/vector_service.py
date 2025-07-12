import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.rca import RCA
from ..models.alert import Alert, AlertGroup
from .rag_service import RAGService

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self):
        self.rag_service = RAGService()

    def store_closed_rca(self, db: Session, rca_id: str) -> bool:
        """
        Store a closed RCA and its associated alerts in the vector database
        
        Args:
            db: Database session
            rca_id: ID of the RCA to store
            
        Returns:
            bool: Success status
        """
        try:
            # Get RCA data
            rca = db.query(RCA).filter(RCA.rca_id == rca_id).first()
            if not rca:
                logger.error(f"RCA {rca_id} not found")
                return False

            if rca.status != "closed":
                logger.warning(f"RCA {rca_id} is not closed, cannot store in vector DB")
                return False

            # Get associated alert group and alerts
            alert_group = db.query(AlertGroup).filter(AlertGroup.group_id == rca.group_id).first()
            if not alert_group:
                logger.error(f"Alert group {rca.group_id} not found")
                return False

            alerts = db.query(Alert).filter(Alert.group_id == rca.group_id).all()
            if not alerts:
                logger.error(f"No alerts found for group {rca.group_id}")
                return False

            # Prepare RCA data for vectorization
            rca_data = {
                "rca_id": rca.rca_id,
                "group_id": rca.group_id,
                "title": rca.title,
                "root_cause": rca.root_cause,
                "impact_analysis": rca.impact_analysis,
                "recommended_actions": rca.recommended_actions,
                "severity": rca.severity,
                "confidence_score": rca.confidence_score,
                "affected_systems": rca.affected_systems or [],
                "timeline": rca.timeline or {},
                "created_at": rca.created_at.isoformat() if rca.created_at else "",
                "closed_at": rca.closed_at.isoformat() if rca.closed_at else "",
                "analysis_method": rca.analysis_method,
                "notes": rca.notes or ""
            }

            # Prepare alerts data
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
                    "status": alert.status,
                    "created_at": alert.created_at.isoformat() if alert.created_at else "",
                    "raw_data": alert.raw_data or {}
                }
                alerts_data.append(alert_data)

            # Store in vector database
            success = self.rag_service.add_rca_to_knowledge_base(rca_data, alerts_data)
            
            if success:
                # Update RCA to mark as vectorized
                rca.is_vectorized = True
                rca.vector_id = rca.rca_id  # Use RCA ID as vector ID
                db.commit()
                
                logger.info(f"Successfully stored RCA {rca_id} in vector database")
                return True
            else:
                logger.error(f"Failed to store RCA {rca_id} in vector database")
                return False

        except Exception as e:
            logger.error(f"Error storing RCA {rca_id} in vector database: {e}")
            return False

    def bulk_store_closed_rcas(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """
        Bulk store closed RCAs that haven't been vectorized yet
        
        Args:
            db: Database session
            limit: Maximum number of RCAs to process
            
        Returns:
            Dict with processing statistics
        """
        try:
            # Find closed RCAs that haven't been vectorized
            closed_rcas = db.query(RCA).filter(
                RCA.status == "closed",
                RCA.is_vectorized == False
            ).limit(limit).all()

            if not closed_rcas:
                return {
                    "processed": 0,
                    "successful": 0,
                    "failed": 0,
                    "message": "No closed RCAs to vectorize"
                }

            successful = 0
            failed = 0

            for rca in closed_rcas:
                if self.store_closed_rca(db, rca.rca_id):
                    successful += 1
                else:
                    failed += 1

            return {
                "processed": len(closed_rcas),
                "successful": successful,
                "failed": failed,
                "message": f"Processed {len(closed_rcas)} closed RCAs"
            }

        except Exception as e:
            logger.error(f"Error in bulk storing RCAs: {e}")
            return {
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "error": str(e)
            }

    def search_historical_incidents(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search historical incidents in the vector database
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of historical incidents
        """
        try:
            if not self.rag_service.is_available():
                logger.warning("RAG service not available for historical search")
                return []

            results = self.rag_service.search_knowledge_base(query, top_k)
            
            # Format results for API response
            formatted_results = []
            for result in results:
                metadata = result.get('metadata', {})
                
                formatted_result = {
                    "rca_id": metadata.get('rca_id', 'unknown'),
                    "group_id": metadata.get('group_id', 'unknown'),
                    "severity": metadata.get('severity', 'unknown'),
                    "alert_count": metadata.get('alert_count', 0),
                    "source_systems": metadata.get('source_systems', []),
                    "created_at": metadata.get('created_at', ''),
                    "confidence_score": metadata.get('confidence_score', 'unknown'),
                    "similarity_score": result.get('similarity_score', 0),
                    "summary": result.get('document', '')[:200] + '...' if result.get('document') else ''
                }
                formatted_results.append(formatted_result)

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching historical incidents: {e}")
            return []

    def get_similar_incidents_for_alerts(self, alerts_data: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar historical incidents for current alerts
        
        Args:
            alerts_data: Current alerts data
            top_k: Number of similar incidents to return
            
        Returns:
            List of similar incidents
        """
        try:
            if not self.rag_service.is_available():
                return []

            similar_rcas = self.rag_service.find_similar_rcas(alerts_data, top_k)
            
            # Format for response
            formatted_incidents = []
            for rca in similar_rcas:
                metadata = rca.get('metadata', {})
                
                incident = {
                    "rca_id": metadata.get('rca_id', 'unknown'),
                    "severity": metadata.get('severity', 'unknown'),
                    "alert_count": metadata.get('alert_count', 0),
                    "source_systems": metadata.get('source_systems', []),
                    "confidence_score": metadata.get('confidence_score', 'unknown'),
                    "similarity_score": rca.get('similarity_score', 0),
                    "insights": self._extract_insights_from_document(rca.get('document', ''))
                }
                formatted_incidents.append(incident)

            return formatted_incidents

        except Exception as e:
            logger.error(f"Error finding similar incidents: {e}")
            return []

    def _extract_insights_from_document(self, document: str) -> Dict[str, str]:
        """Extract key insights from a document"""
        
        insights = {
            "root_cause": "",
            "solution": "",
            "prevention": ""
        }
        
        lines = document.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            
            if 'root cause:' in line_lower:
                current_section = 'root_cause'
                if ':' in line:
                    insights['root_cause'] = line.split(':', 1)[1].strip()
                continue
            elif 'recommended actions:' in line_lower or 'solution:' in line_lower:
                current_section = 'solution'
                if ':' in line:
                    insights['solution'] = line.split(':', 1)[1].strip()
                continue
            elif 'prevention:' in line_lower or 'prevent:' in line_lower:
                current_section = 'prevention'
                if ':' in line:
                    insights['prevention'] = line.split(':', 1)[1].strip()
                continue
            
            # Add content to current section
            if current_section and not insights[current_section]:
                insights[current_section] = line
        
        return insights

    def get_vector_db_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database"""
        try:
            if not self.rag_service.is_available():
                return {"status": "unavailable", "error": "RAG service not available"}

            stats = self.rag_service.get_collection_stats()
            return {
                "status": "available",
                "stats": stats
            }

        except Exception as e:
            logger.error(f"Error getting vector DB stats: {e}")
            return {"status": "error", "error": str(e)}

    def test_vector_similarity(self, text1: str, text2: str) -> float:
        """
        Test similarity between two texts using the vector service
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            if not self.rag_service.is_available():
                return 0.0

            # Create embeddings
            embeddings = self.rag_service.embedding_model.encode([text1, text2])
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)

        except Exception as e:
            logger.error(f"Error testing vector similarity: {e}")
            return 0.0

    def cleanup_old_vectors(self, days_old: int = 365) -> Dict[str, Any]:
        """
        Clean up old vectors from the database (placeholder for future implementation)
        
        Args:
            days_old: Remove vectors older than this many days
            
        Returns:
            Cleanup statistics
        """
        # This would be implemented when needed for maintenance
        return {
            "message": "Vector cleanup not implemented yet",
            "status": "pending"
        }
