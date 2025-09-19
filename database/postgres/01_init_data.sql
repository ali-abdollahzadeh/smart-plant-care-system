-- Initialize basic data for Smart Plant Care System

-- Insert a default plant
INSERT INTO plants (id, name, type, created_at) VALUES 
(1, 'My Smart Plant', 'Indoor Plant', NOW())
ON CONFLICT (id) DO NOTHING;

-- Insert default thresholds for the plant
INSERT INTO thresholds (plant_id, sensor, min_val, max_val, hysteresis) VALUES 
(1, 'temperature', 18.0, 28.0, 1.0),
(1, 'humidity', 30.0, 70.0, 5.0),
(1, 'soil_moisture', 20.0, 80.0, 10.0)
ON CONFLICT DO NOTHING;

-- Create a default user assignment (will be updated when real users register)
-- This ensures the plant has an owner
