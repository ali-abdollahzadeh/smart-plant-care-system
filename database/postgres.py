import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connection pool for better performance
_connection_pool = None

def get_postgres_connection():
    """Get a PostgreSQL connection from the pool"""
    global _connection_pool
    
    if _connection_pool is None:
        _init_connection_pool()
    
    try:
        return _connection_pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        raise

def return_postgres_connection(conn):
    """Return a connection to the pool"""
    global _connection_pool
    
    if _connection_pool and conn:
        try:
            _connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")

def _init_connection_pool():
    """Initialize the connection pool"""
    global _connection_pool
    
    try:
        # Get database URL from environment
        url = os.environ.get('POSTGRES_URL', 'postgresql://plant_user:password123@postgres:5432/smart_plant_care')
        
        # Parse connection parameters
        if url.startswith('postgresql://'):
            url = url.replace('postgresql://', '')
        
        # Extract components
        if '@' in url:
            auth_part, rest = url.split('@', 1)
            if ':' in auth_part:
                user, password = auth_part.split(':', 1)
            else:
                user, password = auth_part, ''
            
            if '/' in rest:
                host_port, database = rest.split('/', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                else:
                    host, port = host_port, '5432'
            else:
                host, port = rest, '5432'
                database = 'smart_plant_care'
        else:
            # Fallback to environment variables
            host = os.environ.get('POSTGRES_HOST', 'postgres')
            port = os.environ.get('POSTGRES_PORT', '5432')
            database = os.environ.get('POSTGRES_DB', 'smart_plant_care')
            user = os.environ.get('POSTGRES_USER', 'plant_user')
            password = os.environ.get('POSTGRES_PASSWORD', 'password123')
        
        logger.info(f"Initializing PostgreSQL connection pool to {host}:{port}/{database}")
        
        # Create connection pool
        _connection_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
        
        logger.info("PostgreSQL connection pool initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
        raise

def execute_query(query, params=None):
    """Execute a query and return results"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount
            
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query execution failed: {e}")
        raise
    finally:
        if conn:
            return_postgres_connection(conn)

def execute_many(query, params_list):
    """Execute a query with multiple parameter sets"""
    conn = None
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Batch query execution failed: {e}")
        raise
    finally:
        if conn:
            return_postgres_connection(conn)

def test_connection():
    """Test database connection"""
    try:
        result = execute_query("SELECT 1 as test")
        logger.info("PostgreSQL connection test successful")
        return True
    except Exception as e:
        logger.error(f"PostgreSQL connection test failed: {e}")
        return False 