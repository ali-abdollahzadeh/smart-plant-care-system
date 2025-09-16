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
            'user_telegram_id': '123456789',  # Reference to the test user
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

# Default plant catalogue to seed into the system (unassigned plants)
DEFAULT_PLANT_CATALOG = [
    {
        "species": "Snake Plant",
        "display_name": "Snake Plant",
        "default_thresholds": {
            "temperature": {"min": 10, "max": 30},
            "humidity": {"min": 30, "max": 50},
            "soil_moisture": {"min": 250, "max": 600}
        },
        "care_info": {
            "watering_frequency": "Every 2–4 weeks",
            "light": "Low to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Spider Plant",
        "display_name": "Spider Plant",
        "default_thresholds": {
            "temperature": {"min": 10, "max": 27},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Peace Lily",
        "display_name": "Peace Lily",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 26},
            "humidity": {"min": 50, "max": 80},
            "soil_moisture": {"min": 400, "max": 750}
        },
        "care_info": {
            "watering_frequency": "Every 4–5 days",
            "light": "Low to medium light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "ZZ Plant",
        "display_name": "ZZ Plant",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 30},
            "humidity": {"min": 30, "max": 50},
            "soil_moisture": {"min": 250, "max": 600}
        },
        "care_info": {
            "watering_frequency": "Every 2–4 weeks",
            "light": "Low to medium light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Aloe Vera",
        "display_name": "Aloe Vera",
        "default_thresholds": {
            "temperature": {"min": 13, "max": 27},
            "humidity": {"min": 30, "max": 50},
            "soil_moisture": {"min": 250, "max": 600}
        },
        "care_info": {
            "watering_frequency": "Every 2–4 weeks",
            "light": "Bright, direct light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Pothos (Epipremnum)",
        "display_name": "Pothos (Epipremnum)",
        "default_thresholds": {
            "temperature": {"min": 12, "max": 30},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Low to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Rubber Plant",
        "display_name": "Rubber Plant",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 29},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Fiddle Leaf Fig",
        "display_name": "Fiddle Leaf Fig",
        "default_thresholds": {
            "temperature": {"min": 16, "max": 29},
            "humidity": {"min": 50, "max": 70},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Monstera Deliciosa",
        "display_name": "Monstera Deliciosa",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 30},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Medium to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Dracaena",
        "display_name": "Dracaena",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 27},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 300, "max": 650}
        },
        "care_info": {
            "watering_frequency": "Every 2–3 weeks",
            "light": "Low to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Philodendron",
        "display_name": "Philodendron",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 30},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Low to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Boston Fern",
        "display_name": "Boston Fern",
        "default_thresholds": {
            "temperature": {"min": 12, "max": 24},
            "humidity": {"min": 50, "max": 80},
            "soil_moisture": {"min": 450, "max": 800}
        },
        "care_info": {
            "watering_frequency": "Every 2–3 days",
            "light": "Indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Calathea",
        "display_name": "Calathea",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 27},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 450, "max": 800}
        },
        "care_info": {
            "watering_frequency": "Every 2–3 days",
            "light": "Indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Dieffenbachia",
        "display_name": "Dieffenbachia",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 27},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Medium light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Croton",
        "display_name": "Croton",
        "default_thresholds": {
            "temperature": {"min": 16, "max": 29},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Jade Plant",
        "display_name": "Jade Plant",
        "default_thresholds": {
            "temperature": {"min": 10, "max": 27},
            "humidity": {"min": 30, "max": 50},
            "soil_moisture": {"min": 250, "max": 600}
        },
        "care_info": {
            "watering_frequency": "Every 2–4 weeks",
            "light": "Bright light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Areca Palm",
        "display_name": "Areca Palm",
        "default_thresholds": {
            "temperature": {"min": 18, "max": 28},
            "humidity": {"min": 40, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Chinese Evergreen",
        "display_name": "Chinese Evergreen",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 27},
            "humidity": {"min": 50, "max": 60},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Low to bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Anthurium",
        "display_name": "Anthurium",
        "default_thresholds": {
            "temperature": {"min": 16, "max": 30},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 350, "max": 700}
        },
        "care_info": {
            "watering_frequency": "Weekly",
            "light": "Bright, indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    },
    {
        "species": "Prayer Plant (Maranta)",
        "display_name": "Prayer Plant (Maranta)",
        "default_thresholds": {
            "temperature": {"min": 15, "max": 26},
            "humidity": {"min": 60, "max": 80},
            "soil_moisture": {"min": 400, "max": 750}
        },
        "care_info": {
            "watering_frequency": "Every 4–5 days",
            "light": "Indirect light",
            "notes": "Adjust care depending on indoor conditions."
        }
    }
]