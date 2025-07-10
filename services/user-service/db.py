import sqlite3
import os

DB_PATH = "/app/user_data.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                name TEXT
            )
        ''')
        # Plants table (extended)
        c.execute('''
            CREATE TABLE IF NOT EXISTS plants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT,
                thresholds TEXT,
                species TEXT,
                location TEXT,
                user_id INTEGER
            )
        ''')
        # User-Plants assignment table (optional, for many-to-many)
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_plants (
                user_id INTEGER,
                plant_id INTEGER,
                PRIMARY KEY (user_id, plant_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (plant_id) REFERENCES plants(id)
            )
        ''')
        conn.commit()

def add_user(telegram_id, name=None):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO users (telegram_id, name) VALUES (?, ?)', (telegram_id, name))
        conn.commit()
        c.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        return c.fetchone()[0]

def get_user_by_telegram_id(telegram_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        return c.fetchone()

def add_plant(name, type_, thresholds, species=None, location=None, user_id=None):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO plants (name, type, thresholds, species, location, user_id) VALUES (?, ?, ?, ?, ?, ?)',
                  (name, type_, thresholds, species, location, user_id))
        conn.commit()
        return c.lastrowid

def assign_plant_to_user(user_id, plant_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO user_plants (user_id, plant_id) VALUES (?, ?)', (user_id, plant_id))
        conn.commit()

def get_plants_for_user(user_id):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT * FROM plants WHERE user_id = ?
        ''', (user_id,))
        return c.fetchall()

def get_all_plants():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM plants')
        return c.fetchall()

# Call this on service startup
def ensure_db():
    print(f"[DB] Using database file: {os.path.abspath(DB_PATH)}")
    need_init = False
    if not os.path.exists(DB_PATH):
        need_init = True
    else:
        with get_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('SELECT 1 FROM users LIMIT 1')
                c.execute('SELECT 1 FROM plants LIMIT 1')
            except Exception:
                need_init = True
    if need_init:
        print("[DB] Initializing DB schema...")
        init_db() 