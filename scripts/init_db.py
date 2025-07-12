#!/usr/bin/env python3
"""
Database initialization script for Alert RCA Management System
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to path to import backend modules
sys.path.append(str(Path(__file__).parent.parent))

from backend.database import create_tables, drop_tables
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize the database with all tables"""
    
    try:
        logger.info("Initializing database...")
        logger.info(f"Database URL: {settings.database_url}")
        
        # Create all tables
        create_tables()
        logger.info("Database tables created successfully")
        
        # Verify tables were created
        from backend.database import engine
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['alerts', 'alert_groups', 'rca', 'rca_status_history']
        
        logger.info(f"Created tables: {tables}")
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✅ Table '{table}' created successfully")
            else:
                logger.warning(f"⚠️  Table '{table}' not found")
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


def reset_database():
    """Reset the database by dropping and recreating all tables"""
    
    try:
        logger.warning("Resetting database - this will delete all data!")
        
        # Drop all tables
        drop_tables()
        logger.info("All tables dropped")
        
        # Recreate tables
        create_tables()
        logger.info("All tables recreated")
        
        logger.info("Database reset completed successfully!")
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "--reset", 
        action="store_true", 
        help="Reset database (drop and recreate all tables)"
    )
    
    args = parser.parse_args()
    
    if args.reset:
        confirmation = input("Are you sure you want to reset the database? This will delete all data! (yes/no): ")
        if confirmation.lower() == 'yes':
            reset_database()
        else:
            logger.info("Database reset cancelled")
    else:
        init_database()
