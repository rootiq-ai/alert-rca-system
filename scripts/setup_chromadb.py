#!/usr/bin/env python3
"""
ChromaDB setup script for Alert RCA Management System
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.services.rag_service import RAGService
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_chromadb():
    """Setup ChromaDB for the RAG service"""
    
    try:
        logger.info("Setting up ChromaDB...")
        logger.info(f"ChromaDB persist directory: {settings.chromadb_persist_dir}")
        
        # Create persist directory if it doesn't exist
        persist_dir = Path(settings.chromadb_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created persist directory: {persist_dir}")
        
        # Initialize RAG service
        rag_service = RAGService()
        
        if rag_service.is_available():
            logger.info("✅ ChromaDB initialized successfully")
            
            # Get collection stats
            stats = rag_service.get_collection_stats()
            logger.info(f"Collection stats: {stats}")
            
        else:
            logger.error("❌ Failed to initialize ChromaDB")
            sys.exit(1)
        
        logger.info("ChromaDB setup completed successfully!")
        
    except Exception as e:
        logger.error(f"ChromaDB setup failed: {e}")
        sys.exit(1)


def test_chromadb():
    """Test ChromaDB functionality"""
    
    try:
        logger.info("Testing ChromaDB functionality...")
        
        rag_service = RAGService()
        
        if not rag_service.is_available():
            logger.error("ChromaDB is not available")
            return False
        
        # Test data
        test_rca_data = {
            "rca_id": "test-rca-001",
            "group_id": "test-group-001", 
            "title": "Test RCA for ChromaDB",
            "root_cause": "This is a test root cause analysis",
            "impact_analysis": "Test impact analysis",
            "recommended_actions": "Test recommended actions",
            "severity": "medium",
            "confidence_score": "high",
            "created_at": "2024-01-01T00:00:00Z"
        }
        
        test_alerts_data = [
            {
                "alert_id": "test-alert-001",
                "title": "Test Alert 1",
                "description": "Test alert description",
                "severity": "medium",
                "source_system": "test-system",
                "created_at": "2024-01-01T00:00:00Z"
            }
        ]
        
        # Test adding data
        logger.info("Testing data addition...")
        success = rag_service.add_rca_to_knowledge_base(test_rca_data, test_alerts_data)
        
        if success:
            logger.info("✅ Test data added successfully")
        else:
            logger.error("❌ Failed to add test data")
            return False
        
        # Test searching
        logger.info("Testing search functionality...")
        results = rag_service.find_similar_rcas(test_alerts_data, top_k=1)
        
        if results:
            logger.info(f"✅ Search successful, found {len(results)} results")
            logger.info(f"First result similarity: {results[0].get('similarity_score', 0):.3f}")
        else:
            logger.warning("⚠️  No search results found")
        
        # Test text search
        logger.info("Testing text search...")
        text_results = rag_service.search_knowledge_base("test root cause", top_k=1)
        
        if text_results:
            logger.info(f"✅ Text search successful, found {len(text_results)} results")
        else:
            logger.warning("⚠️  No text search results found")
        
        # Get final stats
        stats = rag_service.get_collection_stats()
        logger.info(f"Final collection stats: {stats}")
        
        logger.info("ChromaDB testing completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"ChromaDB testing failed: {e}")
        return False


def reset_chromadb():
    """Reset ChromaDB by clearing all data"""
    
    try:
        logger.warning("Resetting ChromaDB - this will delete all vector data!")
        
        # Remove persist directory
        persist_dir = Path(settings.chromadb_persist_dir)
        if persist_dir.exists():
            import shutil
            shutil.rmtree(persist_dir)
            logger.info(f"Removed persist directory: {persist_dir}")
        
        # Recreate directory and initialize
        setup_chromadb()
        
        logger.info("ChromaDB reset completed successfully!")
        
    except Exception as e:
        logger.error(f"ChromaDB reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ChromaDB setup script")
    parser.add_argument(
        "--test", 
        action="store_true", 
        help="Test ChromaDB functionality"
    )
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset ChromaDB (delete all vector data)"
    )
    
    args = parser.parse_args()
    
    if args.reset:
        confirmation = input("Are you sure you want to reset ChromaDB? This will delete all vector data! (yes/no): ")
        if confirmation.lower() == 'yes':
            reset_chromadb()
        else:
            logger.info("ChromaDB reset cancelled")
    elif args.test:
        test_chromadb()
    else:
        setup_chromadb()
