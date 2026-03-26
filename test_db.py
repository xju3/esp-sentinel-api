#!/usr/bin/env python3
"""
Database connection and table creation test script
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config.settings import settings
from src.core.logging import setup_logging
from src.dal.database import engine, Base, SessionLocal
from src.dal import models
from sqlalchemy import text

logger = setup_logging()

def test_database_connection():
    """Test basic database connection"""
    try:
        logger.info("Testing database connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {e}")
        return False

def test_table_creation():
    """Test table creation"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Table creation failed: {e}")
        return False

def test_table_exists():
    """Test if machine_events table exists"""
    try:
        logger.info("Checking if machine_events table exists...")
        with SessionLocal() as session:
            result = session.execute(text("SHOW TABLES LIKE 'machine_events'"))
            exists = result.fetchone() is not None
            if exists:
                logger.info("✓ machine_events table exists")
                
                # Check row count
                count_result = session.execute(text("SELECT COUNT(*) FROM machine_events"))
                count = count_result.fetchone()[0]
                logger.info(f"✓ machine_events table has {count} rows")
            else:
                logger.error("✗ machine_events table does not exist")
            return exists
    except Exception as e:
        logger.error(f"✗ Table check failed: {e}")
        return False

def test_recent_data():
    """Check recent machine events data"""
    try:
        logger.info("Checking recent machine events data...")
        with SessionLocal() as session:
            # Get the 5 most recent records
            result = session.execute(text("""
                SELECT id, sn, event_type, timestamp, temperature, created_at 
                FROM machine_events 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            rows = result.fetchall()
            if rows:
                logger.info(f"✓ Found {len(rows)} recent records:")
                for row in rows:
                    logger.info(f"  ID: {row[0]}, SN: {row[1]}, Event: {row[2]}, Temp: {row[3]}, Created: {row[4]}")
            else:
                logger.warning("✗ No records found in machine_events table")
            
            return len(rows) > 0
    except Exception as e:
        logger.error(f"✗ Recent data check failed: {e}")
        return False

def main():
    logger.info("Starting database diagnostic tests...")
    logger.info(f"Database URL: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Table Creation", test_table_creation),
        ("Table Existence", test_table_exists),
        ("Recent Data Check", test_recent_data),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        success = test_func()
        results.append((test_name, success))
    
    logger.info("\n--- Test Summary ---")
    all_passed = True
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        logger.info(f"{test_name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.error("✗ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())