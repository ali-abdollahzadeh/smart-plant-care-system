"""
Database Initialization Service

This service runs database migrations and setup when the system starts.
It ensures all databases are properly configured before other services start.
"""
import os
import time
import logging
import sys
from database.migrations import run_migrations, check_database_status, get_database_info
from database.postgres import test_connection
from database.influxdb import test_connection as test_influx_connection

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def wait_for_databases():
    """Wait for databases to be ready"""
    logger.info("Waiting for databases to be ready...")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            # Test PostgreSQL
            postgres_ok = test_connection()
            
            # Test InfluxDB
            influx_ok = test_influx_connection()
            
            # Proceed as soon as PostgreSQL is ready; InfluxDB can be configured later
            if postgres_ok:
                if not influx_ok:
                    logger.warning("InfluxDB not ready or unauthorized; proceeding with Postgres-ready state")
                logger.info("Databases readiness condition satisfied (Postgres ready)")
                return True
            else:
                logger.info(f"Database check attempt {attempt + 1}/{max_attempts}")
                logger.warning("PostgreSQL not ready yet")
                    
        except Exception as e:
            logger.warning(f"Database check failed (attempt {attempt + 1}): {e}")
        
        attempt += 1
        time.sleep(2)
    
    logger.error("Databases failed to become ready within timeout")
    return False

def run_setup():
    """Run the complete database setup"""
    logger.info("Starting database initialization...")
    
    # Wait for databases to be ready
    if not wait_for_databases():
        logger.error("Failed to connect to databases")
        return False
    
    # Run migrations
    logger.info("Running database migrations...")
    if not run_migrations():
        logger.error("Database migrations failed")
        return False
    
    # Check final status
    logger.info("Checking final database status...")
    status = check_database_status()
    
    if status['postgres']:
        if not status['influxdb']:
            logger.warning("InfluxDB not ready or unauthorized; proceeding with successful Postgres initialization")
        logger.info("Database initialization completed successfully!")
        
        # Get database info
        info = get_database_info()
        if info:
            logger.info("Database information:")
            logger.info(f"  PostgreSQL tables: {info['postgres']}")
        
        return True
    else:
        logger.error("Database initialization failed")
        logger.error(f"Status: {status}")
        return False

def main():
    """Main function"""
    try:
        success = run_setup()
        if success:
            logger.info("Database initialization service completed successfully")
            sys.exit(0)
        else:
            logger.error("Database initialization service failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Database initialization service interrupted")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Database initialization service error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 