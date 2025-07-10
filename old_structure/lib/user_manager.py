import json
import os
import logging
from datetime import datetime
import sqlite3
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)

class UserManager:
    def __init__(self, db_path: str = "data/users.db"):
        """Initialize the UserManager with a SQLite database."""
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self._create_backup_dir()

    def _create_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=20)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Initialize the database with necessary tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute('PRAGMA foreign_keys = ON')

            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    telegram_id TEXT UNIQUE,
                    username TEXT,
                    created_at TIMESTAMP,
                    last_login TIMESTAMP,
                    settings JSON,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Create plants table (user-specific plants)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_plants (
                    plant_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    name TEXT,
                    type TEXT,
                    created_at TIMESTAMP,
                    settings JSON,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Create sensor_data table (user-specific sensor readings)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    data_id INTEGER PRIMARY KEY,
                    plant_id INTEGER,
                    timestamp TIMESTAMP,
                    temperature REAL,
                    humidity REAL,
                    soil_moisture INTEGER,
                    FOREIGN KEY (plant_id) REFERENCES user_plants (plant_id)
                )
            ''')

            # Create alerts table (user-specific alerts)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    plant_id INTEGER,
                    type TEXT,
                    message TEXT,
                    timestamp TIMESTAMP,
                    status TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (plant_id) REFERENCES user_plants (plant_id)
                )
            ''')

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_plant_id ON sensor_data(plant_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp ON sensor_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON alerts(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)')

            conn.commit()

    def _validate_sensor_data(self, temperature: float, humidity: float, soil_moisture: int) -> bool:
        """Validate sensor data ranges."""
        return (
            -40 <= temperature <= 80 and  # Reasonable temperature range
            0 <= humidity <= 100 and      # Humidity percentage
            0 <= soil_moisture <= 1000    # Soil moisture range
        )

    def create_user(self, telegram_id: str, username: str) -> int:
        """Create a new user and return their user_id."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute('''
                        INSERT INTO users (telegram_id, username, created_at, last_login)
                        VALUES (?, ?, ?, ?)
                    ''', (telegram_id, username, datetime.now(), datetime.now()))
                    
                    user_id = cursor.lastrowid
                    conn.commit()
                    logging.info(f"Created new user: {username} (ID: {user_id})")
                    return user_id
                except sqlite3.IntegrityError:
                    # User already exists
                    cursor.execute('SELECT user_id FROM users WHERE telegram_id = ?', (telegram_id,))
                    user_id = cursor.fetchone()[0]
                    return user_id

    def get_user(self, telegram_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user information by telegram_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, username, created_at, last_login, settings
                FROM users 
                WHERE telegram_id = ? AND is_active = 1
            ''', (telegram_id,))
            
            user = cursor.fetchone()
            
            if user:
                return {
                    'user_id': user[0],
                    'username': user[1],
                    'created_at': user[2],
                    'last_login': user[3],
                    'settings': json.loads(user[4]) if user[4] else {}
                }
            return None

    def add_plant(self, user_id: int, name: str, plant_type: str, settings: Dict[str, Any]) -> int:
        """Add a new plant for a user and return the plant_id."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Validate user exists and is active
                cursor.execute('SELECT 1 FROM users WHERE user_id = ? AND is_active = 1', (user_id,))
                if not cursor.fetchone():
                    raise ValueError("User not found or inactive")

                cursor.execute('''
                    INSERT INTO user_plants (user_id, name, type, created_at, settings)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, name, plant_type, datetime.now(), json.dumps(settings)))
                
                plant_id = cursor.lastrowid
                conn.commit()
                logging.info(f"Added new plant: {name} for user {user_id}")
                return plant_id

    def get_user_plants(self, user_id: int) -> List[Dict[str, Any]]:
        """Retrieve all plants for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT plant_id, name, type, created_at, settings
                FROM user_plants WHERE user_id = ?
            ''', (user_id,))
            
            plants = cursor.fetchall()
            
            return [{
                'plant_id': plant[0],
                'name': plant[1],
                'type': plant[2],
                'created_at': plant[3],
                'settings': json.loads(plant[4]) if plant[4] else {}
            } for plant in plants]

    def save_sensor_data(self, plant_id: int, temperature: float, humidity: float, soil_moisture: int):
        """Save sensor readings for a specific plant."""
        if not self._validate_sensor_data(temperature, humidity, soil_moisture):
            raise ValueError("Invalid sensor data values")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Validate plant exists and is active
            cursor.execute('SELECT 1 FROM user_plants WHERE plant_id = ? AND is_active = 1', (plant_id,))
            if not cursor.fetchone():
                raise ValueError("Plant not found or inactive")
            
            cursor.execute('''
                INSERT INTO sensor_data (plant_id, timestamp, temperature, humidity, soil_moisture)
                VALUES (?, ?, ?, ?, ?)
            ''', (plant_id, datetime.now(), temperature, humidity, soil_moisture))
            
            conn.commit()

    def get_plant_data(self, plant_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve sensor data for a specific plant."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, temperature, humidity, soil_moisture
                FROM sensor_data
                WHERE plant_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (plant_id, limit))
            
            data = cursor.fetchall()
            
            return [{
                'timestamp': row[0],
                'temperature': row[1],
                'humidity': row[2],
                'soil_moisture': row[3]
            } for row in data]

    def create_alert(self, user_id: int, plant_id: int, alert_type: str, message: str) -> int:
        """Create a new alert for a user and plant."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Validate user and plant exist and are active
                cursor.execute('''
                    SELECT 1 FROM users u 
                    JOIN user_plants p ON u.user_id = p.user_id 
                    WHERE u.user_id = ? AND p.plant_id = ? 
                    AND u.is_active = 1 AND p.is_active = 1
                ''', (user_id, plant_id))
                
                if not cursor.fetchone():
                    raise ValueError("User or plant not found or inactive")
                
                cursor.execute('''
                    INSERT INTO alerts (user_id, plant_id, type, message, timestamp, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, plant_id, alert_type, message, datetime.now(), 'active'))
                
                alert_id = cursor.lastrowid
                conn.commit()
                logging.info(f"Created new alert for user {user_id} and plant {plant_id}")
                return alert_id

    def get_user_alerts(self, user_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve alerts for a user, optionally filtered by status."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT alert_id, plant_id, type, message, timestamp, status
                FROM alerts
                WHERE user_id = ?
            '''
            params = [user_id]
            
            if status:
                query += ' AND status = ?'
                params.append(status)
                
            query += ' ORDER BY timestamp DESC'
            
            cursor.execute(query, params)
            alerts = cursor.fetchall()
            
            return [{
                'alert_id': alert[0],
                'plant_id': alert[1],
                'type': alert[2],
                'message': alert[3],
                'timestamp': alert[4],
                'status': alert[5]
            } for alert in alerts]

    def update_user_settings(self, user_id: int, settings: Dict[str, Any]):
        """Update user settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users
                SET settings = ?
                WHERE user_id = ?
            ''', (json.dumps(settings), user_id))
            
            conn.commit()

    def update_plant_settings(self, plant_id: int, settings: Dict[str, Any]):
        """Update plant settings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_plants
                SET settings = ?
                WHERE plant_id = ?
            ''', (json.dumps(settings), plant_id))
            
            conn.commit()

    def backup_database(self):
        """Create a backup of the database."""
        with self._lock:
            backup_path = os.path.join(
                os.path.dirname(self.db_path),
                "backups",
                f"users_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            )
            
            with self._get_connection() as source:
                backup = sqlite3.connect(backup_path)
                source.backup(backup)
                backup.close()
            
            logging.info(f"Database backup created: {backup_path}")

    def cleanup_old_data(self, days: int = 30):
        """Remove old sensor data and alerts."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete old sensor data
                cursor.execute('''
                    DELETE FROM sensor_data 
                    WHERE timestamp < datetime('now', ?)
                ''', (f'-{days} days',))
                
                # Delete old alerts
                cursor.execute('''
                    DELETE FROM alerts 
                    WHERE timestamp < datetime('now', ?)
                ''', (f'-{days} days',))
                
                conn.commit()
                logging.info(f"Cleaned up data older than {days} days")

    def deactivate_user(self, user_id: int):
        """Deactivate a user and their plants."""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Deactivate user's plants
                cursor.execute('''
                    UPDATE user_plants 
                    SET is_active = 0 
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Deactivate user
                cursor.execute('''
                    UPDATE users 
                    SET is_active = 0 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                logging.info(f"Deactivated user {user_id} and their plants")

# Example usage
if __name__ == "__main__":
    # Initialize the user manager
    user_manager = UserManager()
    
    try:
        # Create a test user
        user_id = user_manager.create_user("123456789", "test_user")
        
        # Add a test plant
        plant_id = user_manager.add_plant(
            user_id,
            "Test Plant",
            "Fern",
            {
                "temperature_threshold": 25.0,
                "humidity_threshold": 60.0,
                "moisture_threshold": 300
            }
        )
        
        # Save some test sensor data
        user_manager.save_sensor_data(plant_id, 24.5, 55.0, 350)
        
        # Create a test alert
        user_manager.create_alert(
            user_id,
            plant_id,
            "temperature",
            "Temperature is above threshold"
        )
        
        # Create a backup
        user_manager.backup_database()
        
        # Clean up old data
        user_manager.cleanup_old_data(days=30)
        
        # Retrieve and print user's plants
        plants = user_manager.get_user_plants(user_id)
        print("User's plants:", plants)
        
        # Retrieve and print plant data
        plant_data = user_manager.get_plant_data(plant_id)
        print("Plant data:", plant_data)
        
        # Retrieve and print user's alerts
        alerts = user_manager.get_user_alerts(user_id)
        print("User's alerts:", alerts)
        
    except Exception as e:
        logging.error(f"Error in test: {e}") 