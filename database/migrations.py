"""
Database migration scripts for Smart Plant Care System
"""
import logging
import json
from datetime import datetime
from .postgres import execute_query, test_connection
from .influxdb import test_connection as test_influx_connection
from .schema import POSTGRES_SCHEMA, POSTGRES_INDEXES, SAMPLE_DATA, DEFAULT_PLANT_CATALOG

logger = logging.getLogger(__name__)

def create_postgres_schema():
    """Create PostgreSQL schema and tables"""
    try:
        logger.info("Creating PostgreSQL schema...")
        
        # Ensure pgcrypto is available for gen_random_uuid()
        try:
            execute_query('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
            logger.info('Ensured pgcrypto extension is enabled')
        except Exception as e:
            logger.warning(f"Could not create pgcrypto extension (may already exist or insufficient perms): {e}")

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
            
            # execute_query returns list of RealDictRow; extract by key
            first_row = user_result[0]
            user_id = first_row['id'] if isinstance(first_row, dict) else first_row[0]
            
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

def seed_default_plant_catalogue():
    """Seed default plant catalogue entries as unassigned plants (once)."""
    try:
        logger.info("Seeding default plant catalogue...")

        for item in DEFAULT_PLANT_CATALOG:
            name = item.get('display_name') or item.get('species')
            species = item.get('species')
            thresholds = json.dumps(item.get('default_thresholds', {}))
            care_info = json.dumps(item.get('care_info', {}))

            # Avoid duplicates: check if a plant with same name and species exists
            exists = execute_query(
                """
                SELECT 1 FROM plants 
                WHERE name = %s AND species = %s AND active = TRUE
                LIMIT 1
                """,
                (name, species)
            )

            if exists:
                continue

            execute_query(
                """
                INSERT INTO plants (name, species, location, thresholds, care_info)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (name, species, None, thresholds, care_info)
            )

        logger.info("Default plant catalogue seeded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to seed default plant catalogue: {e}")
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
    
    # InfluxDB is optional for Postgres migrations; continue even if it fails
    try:
        if not test_influx_connection():
            logger.warning("InfluxDB connection failed; proceeding with PostgreSQL migrations only")
    except Exception as e:
        logger.warning(f"InfluxDB check errored; proceeding anyway: {e}")
    
    # Create PostgreSQL schema
    if not create_postgres_schema():
        logger.error("PostgreSQL schema creation failed")
        return False
    
    # Seed PostgreSQL data
    if not seed_postgres_data():
        logger.error("PostgreSQL data seeding failed")
        return False

    # Seed default plant catalogue
    if not seed_default_plant_catalogue():
        logger.error("Default plant catalogue seeding failed")
        return False
    
    # Setup InfluxDB
    # Do not fail the whole migration if InfluxDB setup fails
    try:
        if not create_influxdb_buckets():
            logger.warning("InfluxDB setup failed; continuing")
    except Exception as e:
        logger.warning(f"InfluxDB setup errored; continuing: {e}")
    
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