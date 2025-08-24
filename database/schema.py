"""
Database schema definitions for Smart Plant Care System
"""

# PostgreSQL Schema
POSTGRES_SCHEMA = {
    'users': '''
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_id TEXT UNIQUE,
            username TEXT,
            display_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''',
    
    'plants': '''
        CREATE TABLE IF NOT EXISTS plants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            species TEXT,
            location TEXT,
            thresholds JSONB,
            care_info JSONB,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''',
    
    'devices': '''
        CREATE TABLE IF NOT EXISTS devices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            type TEXT,
            config JSONB,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            plant_id UUID REFERENCES plants(id) ON DELETE SET NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''',
    
    'services': '''
        CREATE TABLE IF NOT EXISTS services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            type TEXT,
            config JSONB,
            endpoint TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    ''',
    
    'user_plants': '''
        CREATE TABLE IF NOT EXISTS user_plants (
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            plant_id UUID REFERENCES plants(id) ON DELETE CASCADE,
            assigned_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, plant_id)
        );
    '''
}

# InfluxDB Schema (measurements and tags)
INFLUXDB_SCHEMA = {
    'sensor_readings': {
        'measurement': 'sensor_readings',
        'tags': [
            'plant_id',
            'user_id', 
            'device_id',
            'plant_name',
            'plant_species',
            'location'
        ],
        'fields': [
            'temperature',
            'humidity',
            'soil_moisture',
            'lighting',
            'watering',
            'fan_speed',
            'ph_level',
            'nutrient_level'
        ]
    },
    
    'actuator_events': {
        'measurement': 'actuator_events',
        'tags': [
            'plant_id',
            'user_id',
            'device_id',
            'actuator_type'
        ],
        'fields': [
            'action',
            'value',
            'duration',
            'success'
        ]
    },
    
    'alerts': {
        'measurement': 'alerts',
        'tags': [
            'plant_id',
            'user_id',
            'device_id',
            'alert_type',
            'severity'
        ],
        'fields': [
            'message',
            'threshold_value',
            'current_value',
            'resolved'
        ]
    }
}

# Indexes for better performance
POSTGRES_INDEXES = [
    'CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);',
    'CREATE INDEX IF NOT EXISTS idx_plants_user_id ON plants(user_id);',
    'CREATE INDEX IF NOT EXISTS idx_plants_active ON plants(active);',
    'CREATE INDEX IF NOT EXISTS idx_devices_user_id ON devices(user_id);',
    'CREATE INDEX IF NOT EXISTS idx_devices_plant_id ON devices(plant_id);',
    'CREATE INDEX IF NOT EXISTS idx_devices_active ON devices(active);',
    'CREATE INDEX IF NOT EXISTS idx_services_type ON services(type);',
    'CREATE INDEX IF NOT EXISTS idx_services_active ON services(active);'
]

# Sample data for testing
SAMPLE_DATA = {
    'users': [
        {
            'telegram_id': '123456789',
            'username': 'test_user',
            'display_name': 'Test User'
        }
    ],
    
    'plants': [
        {
            'name': 'Monstera Deliciosa',
            'species': 'Monstera',
            'location': 'living_room',
            'thresholds': {
                'temperature': {'min': 18, 'max': 30},
                'humidity': {'min': 40, 'max': 80},
                'soil_moisture': {'min': 300, 'max': 800}
            },
            'care_info': {
                'watering_frequency': 'weekly',
                'light_requirements': 'indirect_bright'
            }
        }
    ],
    
    'devices': [
        {
            'name': 'Raspberry Pi Sensor',
            'type': 'sensor',
            'config': {
                'location': 'living_room',
                'capabilities': ['temperature', 'humidity', 'soil_moisture']
            }
        }
    ]
} 