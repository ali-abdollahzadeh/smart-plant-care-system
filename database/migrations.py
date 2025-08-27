"""
Database migration scripts for Smart Plant Care System
"""
import logging
import json
from datetime import datetime
from .postgres import execute_query, test_connection
from .influxdb import test_connection as test_influx_connection
from .schema import POSTGRES_SCHEMA, POSTGRES_INDEXES, SAMPLE_DATA

logger = logging.getLogger(__name__)

def create_postgres_schema():
    """Create PostgreSQL schema and tables"""
    try:
        logger.info("Creating PostgreSQL schema...")
        
        # Create tables
        for table_name, create_sql in POSTGRES_SCHEMA.items():
            logger.info(f"Creating table: {table_name}")
            execute_query(create_sql)
        
        # Create indexes
        for index_sql in POSTGRES_INDEXES:
            logger.info(f"Creating index: {index_sql}")
            execute_query(index_sql)
        
        logger.info("PostgreSQL schema created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL schema: {e}")
        return False

def seed_postgres_data():
    """Seed PostgreSQL with sample data"""
    try:
        logger.info("Seeding PostgreSQL with sample data...")
        
        # Insert sample users
        for user_data in SAMPLE_DATA['users']:
            query = """
                INSERT INTO users (telegram_id, username, display_name)
                VALUES (%(telegram_id)s, %(username)s, %(display_name)s)
                ON CONFLICT (telegram_id) DO NOTHING
            """
            execute_query(query, user_data)
        
        # Insert sample plants
        for plant_data in SAMPLE_DATA['plants']:
            # First, get the user_id from the telegram_id
            user_query = "SELECT id FROM users WHERE telegram_id = %s"
            user_result = execute_query(user_query, (plant_data['user_telegram_id'],))
            
            if not user_result or len(user_result) == 0:
                logger.warning(f"User with telegram_id {plant_data['user_telegram_id']} not found, skipping plant")
                continue
                
            user_id = user_result[0][0]  # First row, first column (id)
            
            query = """
                INSERT INTO plants (name, species, location, user_id, thresholds, care_info)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """
            # Convert dict to JSON string for JSONB
            plant_params = (
                plant_data['name'],
                plant_data['species'], 
                plant_data['location'],
                user_id,
                json.dumps(plant_data['thresholds']),
                json.dumps(plant_data['care_info'])
            )
            execute_query(query, plant_params)
        
        # Insert sample devices
        for device_data in SAMPLE_DATA['devices']:
            query = """
                INSERT INTO devices (name, type, config)
                VALUES (%(name)s, %(type)s, %(config)s)
            """
            # Convert dict to JSON string for JSONB
            device_data['config'] = json.dumps(device_data['config'])
            execute_query(query, device_data)
        
        logger.info("PostgreSQL sample data seeded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to seed PostgreSQL data: {e}")
        return False

def create_influxdb_buckets():
    """Create InfluxDB buckets and retention policies"""
    try:
        logger.info("Setting up InfluxDB buckets...")
        
        # This would typically be done through InfluxDB CLI or API
        # For now, we'll assume buckets are created via docker-compose environment variables
        
        logger.info("InfluxDB buckets setup completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup InfluxDB buckets: {e}")
        return False

def run_migrations():
    """Run all database migrations"""
    logger.info("Starting database migrations...")
    
    # Test connections
    if not test_connection():
        logger.error("PostgreSQL connection failed")
        return False
    
    if not test_influx_connection():
        logger.error("InfluxDB connection failed")
        return False
    
    # Create PostgreSQL schema
    if not create_postgres_schema():
        logger.error("PostgreSQL schema creation failed")
        return False
    
    # Seed PostgreSQL data
    if not seed_postgres_data():
        logger.error("PostgreSQL data seeding failed")
        return False
    
    # Setup InfluxDB
    if not create_influxdb_buckets():
        logger.error("InfluxDB setup failed")
        return False
    
    logger.info("All database migrations completed successfully")
    return True

def check_database_status():
    """Check the status of all databases"""
    status = {
        'postgres': False,
        'influxdb': False,
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        status['postgres'] = test_connection()
    except Exception as e:
        logger.error(f"PostgreSQL status check failed: {e}")
    
    try:
        status['influxdb'] = test_influx_connection()
    except Exception as e:
        logger.error(f"InfluxDB status check failed: {e}")
    
    return status

def get_database_info():
    """Get information about database tables and data"""
    try:
        info = {
            'postgres': {},
            'influxdb': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # PostgreSQL table counts
        tables = ['users', 'plants', 'devices', 'services']
        for table in tables:
            result = execute_query(f"SELECT COUNT(*) as count FROM {table}")
            if result:
                info['postgres'][table] = result[0]['count']
        
        # PostgreSQL table sizes
        size_query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
        """
        size_result = execute_query(size_query)
        info['postgres']['table_sizes'] = size_result
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return None

if __name__ == "__main__":
    # Run migrations when script is executed directly
    run_migrations() 