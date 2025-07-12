import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import json

from ..config import settings

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = None
        self.collection = None
        self._initialize_chromadb()

    def _initialize_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=settings.chromadb_persist_dir
            )
            
            # Get or create collection for RCA data
            self.collection = self.chroma_client.get_or_create_collection(
                name="rca_knowledge_base",
                metadata={"description": "Historical RCA data for similar alerts"}
            )
            
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.collection = None

    def is_available(self) -> bool:
        """Check if RAG service is available"""
        return self.chroma_client is not None and self.collection is not None

    def add_rca_to_knowledge_base(self, rca_data: Dict[str, Any], alerts_data: List[Dict[str, Any]]) -> bool:
        """
        Add RCA and associated alerts to the knowledge base
        
        Args:
            rca_data: RCA information
            alerts_data: Associated alerts data
            
        Returns:
            bool: Success status
        """
        try:
            if not self.is_available():
                logger.warning("RAG service not available")
                return False

            # Create document text for embedding
            document_text = self._create_document_text(rca_data, alerts_data)
            
            # Generate embedding
            embedding = self.embedding_model.encode([document_text])[0].tolist()
            
            # Prepare metadata
            metadata = {
                "rca_id": rca_data.get("rca_id", "unknown"),
                "group_id": rca_data.get("group_id", "unknown"),
                "severity": rca_data.get("severity", "unknown"),
                "alert_count": len(alerts_data),
                "source_systems": list(set([alert.get("source_system", "unknown") for alert in alerts_data])),
                "created_at": rca_data.get("created_at", ""),
                "confidence_score": rca_data.get("confidence_score", "unknown")
            }
            
            # Add to collection
            self.collection.add(
                documents=[document_text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[rca_data.get("rca_id", f"rca_{len(alerts_data)}")]
            )
            
            logger.info(f"Added RCA {rca_data.get('rca_id')} to knowledge base")
            return True
            
        except Exception as e:
            logger.error(f"Error adding RCA to knowledge base: {e}")
            return False

    def find_similar_rcas(self, alerts_data: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar RCAs from the knowledge base
        
        Args:
            alerts_data: Current alerts to find similar RCAs for
            top_k: Number of similar RCAs to return
            
        Returns:
            List of similar RCA contexts
        """
        try:
            if not self.is_available():
                logger.warning("RAG service not available")
                return []

            # Create query text from current alerts
            query_text = self._create_query_text(alerts_data)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query_text])[0].tolist()
            
            # Search for similar documents
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            similar_rcas = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    
                    # Calculate similarity score (1 - distance)
                    similarity_score = max(0, 1 - distance)
                    
                    # Only include results above threshold
                    if similarity_score >= 0.7:  # 70% similarity threshold
                        similar_rcas.append({
                            'document': doc,
                            'metadata': metadata,
                            'similarity_score': similarity_score
                        })
            
            logger.info(f"Found {len(similar_rcas)} similar RCAs")
            return similar_rcas
            
        except Exception as e:
            logger.error(f"Error finding similar RCAs: {e}")
            return []

    def get_context_for_rca_generation(self, alerts_data: List[Dict[str, Any]]) -> str:
        """
        Get relevant context from knowledge base for RCA generation
        
        Args:
            alerts_data: Current alerts
            
        Returns:
            Formatted context string
        """
        try:
            similar_rcas = self.find_similar_rcas(alerts_data, top_k=3)
            
            if not similar_rcas:
                return "No similar historical incidents found."
            
            context_parts = ["Based on similar historical incidents:"]
            
            for i, rca in enumerate(similar_rcas, 1):
                metadata = rca['metadata']
                similarity = rca['similarity_score']
                
                context_parts.append(f"\n{i}. Similar Incident (Similarity: {similarity:.2f}):")
                context_parts.append(f"   - Severity: {metadata.get('severity', 'Unknown')}")
                context_parts.append(f"   - Alert Count: {metadata.get('alert_count', 'Unknown')}")
                context_parts.append(f"   - Systems: {', '.join(metadata.get('source_systems', []))}")
                context_parts.append(f"   - Confidence: {metadata.get('confidence_score', 'Unknown')}")
                
                # Extract key insights from the document
                doc_text = rca['document']
                insights = self._extract_key_insights(doc_text)
                if insights:
                    context_parts.append(f"   - Key Insights: {insights}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting context for RCA generation: {e}")
            return "Error retrieving historical context."

    def _create_document_text(self, rca_data: Dict[str, Any], alerts_data: List[Dict[str, Any]]) -> str:
        """Create searchable document text from RCA and alerts data"""
        
        text_parts = []
        
        # RCA information
        text_parts.append(f"Title: {rca_data.get('title', '')}")
        text_parts.append(f"Root Cause: {rca_data.get('root_cause', '')}")
        text_parts.append(f"Impact Analysis: {rca_data.get('impact_analysis', '')}")
        text_parts.append(f"Recommended Actions: {rca_data.get('recommended_actions', '')}")
        text_parts.append(f"Severity: {rca_data.get('severity', '')}")
        
        # Affected systems
        affected_systems = rca_data.get('affected_systems', [])
        if affected_systems:
            text_parts.append(f"Affected Systems: {', '.join(affected_systems)}")
        
        # Alert information
        text_parts.append(f"Alert Count: {len(alerts_data)}")
        
        # Alert details
        alert_titles = [alert.get('title', '') for alert in alerts_data]
        text_parts.append(f"Alert Titles: {'; '.join(alert_titles[:5])}")  # First 5 titles
        
        # Source systems
        source_systems = list(set([alert.get('source_system', '') for alert in alerts_data]))
        text_parts.append(f"Source Systems: {', '.join(source_systems)}")
        
        # Metrics
        metrics = list(set([alert.get('metric_name', '') for alert in alerts_data if alert.get('metric_name')]))
        if metrics:
            text_parts.append(f"Metrics: {', '.join(metrics)}")
        
        # Tags and labels
        all_tags = []
        all_labels = []
        for alert in alerts_data:
            if alert.get('tags'):
                all_tags.extend([f"{k}:{v}" for k, v in alert['tags'].items()])
            if alert.get('labels'):
                all_labels.extend([f"{k}:{v}" for k, v in alert['labels'].items()])
        
        if all_tags:
            text_parts.append(f"Tags: {'; '.join(list(set(all_tags))[:10])}")
        if all_labels:
            text_parts.append(f"Labels: {'; '.join(list(set(all_labels))[:10])}")
        
        return "\n".join(filter(None, text_parts))

    def _create_query_text(self, alerts_data: List[Dict[str, Any]]) -> str:
        """Create query text from current alerts"""
        
        text_parts = []
        
        # Alert titles
        alert_titles = [alert.get('title', '') for alert in alerts_data]
        text_parts.append(f"Alert Titles: {'; '.join(alert_titles[:5])}")
        
        # Source systems
        source_systems = list(set([alert.get('source_system', '') for alert in alerts_data]))
        text_parts.append(f"Source Systems: {', '.join(source_systems)}")
        
        # Severities
        severities = list(set([alert.get('severity', '') for alert in alerts_data]))
        text_parts.append(f"Severities: {', '.join(severities)}")
        
        # Metrics
        metrics = list(set([alert.get('metric_name', '') for alert in alerts_data if alert.get('metric_name')]))
        if metrics:
            text_parts.append(f"Metrics: {', '.join(metrics)}")
        
        # Common keywords from descriptions
        descriptions = [alert.get('description', '') for alert in alerts_data if alert.get('description')]
        if descriptions:
            # Extract common words (simple approach)
            all_words = []
            for desc in descriptions:
                words = desc.lower().split()
                all_words.extend([word for word in words if len(word) > 4])
            
            # Get most common words
            word_counts = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            common_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            if common_words:
                keywords = [word for word, count in common_words]
                text_parts.append(f"Keywords: {', '.join(keywords)}")
        
        return "\n".join(filter(None, text_parts))

    def _extract_key_insights(self, document_text: str) -> str:
        """Extract key insights from RCA document"""
        
        # Simple extraction - look for key phrases
        lines = document_text.split('\n')
        insights = []
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['root cause:', 'solution:', 'fix:', 'resolution:']):
                # Extract the insight part
                if ':' in line:
                    insight = line.split(':', 1)[1].strip()
                    if len(insight) > 10:  # Meaningful insight
                        insights.append(insight[:100])  # Limit length
        
        return '; '.join(insights[:2]) if insights else ""

    def search_knowledge_base(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Search the knowledge base with a text query
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            if not self.is_available():
                return []

            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            
            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            search_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    
                    search_results.append({
                        'document': doc,
                        'metadata': metadata,
                        'similarity_score': max(0, 1 - distance)
                    })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base collection"""
        try:
            if not self.is_available():
                return {"error": "RAG service not available"}

            count = self.collection.count()
            
            return {
                "total_documents": count,
                "collection_name": "rca_knowledge_base",
                "embedding_model": "all-MiniLM-L6-v2",
                "status": "active"
            }
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
