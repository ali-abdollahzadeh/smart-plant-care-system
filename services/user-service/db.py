import os
import logging
from database.postgres import execute_query, test_connection

logger = logging.getLogger(__name__)

def init_db():
    """Initialize database schema - now handled by migrations"""
    try:
        # Test connection to ensure database is available
        if test_connection():
            logger.info("Database connection successful")
            return True
        else:
            logger.error("Database connection failed")
            return False
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

def add_user(telegram_id, name=None):
    """Add a new user to the database"""
    try:
        query = """
            INSERT INTO users (telegram_id, display_name)
            VALUES (%s, %s)
            ON CONFLICT (telegram_id) DO NOTHING
            RETURNING id
        """
        result = execute_query(query, (telegram_id, name))
        if result and len(result) > 0:
            user_id = result[0]['id']
            logger.info(f"Added user: telegram_id={telegram_id}, user_id={user_id}")
            return user_id
        else:
            logger.warning(f"User already exists: telegram_id={telegram_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to add user: {e}")
        return None

def get_user_by_telegram_id(telegram_id):
    """Get user by Telegram ID"""
    try:
        query = "SELECT * FROM users WHERE telegram_id = %s"
        result = execute_query(query, (telegram_id,))
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get user by telegram_id: {e}")
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    try:
        query = "SELECT * FROM users WHERE id = %s"
        result = execute_query(query, (user_id,))
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get user by id: {e}")
        return None

def update_user(user_id, **kwargs):
    """Update user information"""
    try:
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = NOW()")
        params.append(user_id)
        
        query = f"""
            UPDATE users 
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        
        result = execute_query(query, params)
        logger.info(f"Updated user: user_id={user_id}, changes={list(kwargs.keys())}")
        return result > 0
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        return False

def get_plants_for_user(user_id):
    """Get all plants assigned to a user using user_plants junction table"""
    try:
        query = """
            SELECT p.* FROM plants p
            JOIN user_plants up ON p.id = up.plant_id
            WHERE up.user_id = %s AND p.active = TRUE
            ORDER BY p.created_at DESC
        """
        result = execute_query(query, (user_id,))
        return result
    except Exception as e:
        logger.error(f"Failed to get plants for user: {e}")
        return []

def get_all_plants():
    """Get all active plants"""
    try:
        query = """
            SELECT 
                p.*,
                up.user_id AS user_id,
                u.display_name AS user_name
            FROM plants p
            LEFT JOIN user_plants up ON p.id = up.plant_id
            LEFT JOIN users u ON up.user_id = u.id
            WHERE p.active = TRUE
            ORDER BY p.created_at DESC
        """
        result = execute_query(query)
        return result
    except Exception as e:
        logger.error(f"Failed to get all plants: {e}")
        return []

def assign_plant_to_user(plant_id, user_id):
    """Assign a plant to a user using user_plants junction table"""
    try:
        # First check if assignment already exists
        check_query = """
            SELECT 1 FROM user_plants 
            WHERE user_id = %s AND plant_id = %s
        """
        existing = execute_query(check_query, (user_id, plant_id))
        
        if existing:
            logger.info(f"Plant {plant_id} already assigned to user {user_id}")
            return True
        
        # Insert new assignment
        query = """
            INSERT INTO user_plants (user_id, plant_id, assigned_at)
            VALUES (%s, %s, NOW())
        """
        result = execute_query(query, (user_id, plant_id))
        if result:
            logger.info(f"Assigned plant {plant_id} to user {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to assign plant to user: {e}")
        return False

def add_plant(name, species=None, location=None, thresholds=None, care_info=None, user_id=None):
    """Add a new plant"""
    try:
        query = """
            INSERT INTO plants (name, species, location, thresholds, care_info)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        result = execute_query(query, (name, species, location, thresholds, care_info))
        if result:
            plant_id = result[0]['id']
            logger.info(f"Added plant: name={name}, plant_id={plant_id}")
            
            # If user_id is provided, assign the plant to the user
            if user_id:
                assign_plant_to_user(plant_id, user_id)
            
            return plant_id
        return None
    except Exception as e:
        logger.error(f"Failed to add plant: {e}")
        return None

def get_plant_by_id(plant_id):
    """Get plant by ID"""
    try:
        query = """
            SELECT p.*, u.display_name as user_name 
            FROM plants p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.id = %s
        """
        result = execute_query(query, (plant_id,))
        if result:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get plant by id: {e}")
        return None

def update_plant(plant_id, **kwargs):
    """Update plant information"""
    try:
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in kwargs.items():
            if value is not None:
                set_clauses.append(f"{key} = %s")
                params.append(value)
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = NOW()")
        params.append(plant_id)
        
        query = f"""
            UPDATE plants 
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        
        result = execute_query(query, params)
        logger.info(f"Updated plant: plant_id={plant_id}, changes={list(kwargs.keys())}")
        return result > 0
    except Exception as e:
        logger.error(f"Failed to update plant: {e}")
        return False

def delete_plant(plant_id):
    """Soft delete a plant (set active = FALSE)"""
    try:
        query = """
            UPDATE plants 
            SET active = FALSE, updated_at = NOW()
            WHERE id = %s
        """
        result = execute_query(query, (plant_id,))
        if result > 0:
            logger.info(f"Deleted plant: plant_id={plant_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to delete plant: {e}")
        return False

def get_user_statistics(user_id):
    """Get user statistics"""
    try:
        query = """
            SELECT 
                COUNT(*) as total_plants,
                COUNT(CASE WHEN active = TRUE THEN 1 END) as active_plants
            FROM plants 
            WHERE user_id = %s
        """
        result = execute_query(query, (user_id,))
        if result:
            return result[0]
        return {'total_plants': 0, 'active_plants': 0}
    except Exception as e:
        logger.error(f"Failed to get user statistics: {e}")
        return {'total_plants': 0, 'active_plants': 0}

def ensure_db():
    """Ensure database is ready - simplified version"""
    try:
        if test_connection():
            logger.info("Database connection verified")
            return True
        else:
            logger.error("Database connection failed")
            return False
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False
