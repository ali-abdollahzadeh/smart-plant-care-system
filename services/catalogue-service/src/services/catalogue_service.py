from sqlalchemy.orm import Session
from ..repositories.plant_repository import PlantRepository
from ..repositories.threshold_repository import ThresholdRepository
from ..repositories.alert_repository import AlertRepository

class CatalogueService:
    def __init__(self, db: Session):
        self.plants = PlantRepository(db)
        self.thresholds = ThresholdRepository(db)
        self.alerts = AlertRepository(db)

    def create_plant(self, name: str, plant_type: str = None):
        return self.plants.create_plant(name, plant_type)

    def list_plants(self):
        return self.plants.get_all()

    def get_plant(self, plant_id: int):
        return self.plants.get_by_id(plant_id)

    def set_threshold(self, plant_id: int = None, plant_type: str = None, sensor: str = None,
                      min_val: float = None, max_val: float = None, hysteresis: float = 0.0):
        return self.thresholds.upsert_threshold(plant_id, plant_type, sensor, min_val, max_val, hysteresis)

    def get_thresholds(self, plant_id: int = None, plant_type: str = None):
        results = []
        if plant_id:
            # Specific thresholds for this plant
            specific = self.thresholds.get_by_plant(plant_id)
            results.extend(specific)
            # Also include thresholds by plant_type
            if plant_type:
                global_ts = self.thresholds.get_by_type(plant_type)
            else:
                global_ts = []
            # Avoid duplicate sensor entries (prefer plant-specific over global)
            specific_sensors = {t.sensor for t in specific}
            for t in global_ts:
                if t.sensor not in specific_sensors:
                    results.append(t)
        elif plant_type:
            results = self.thresholds.get_by_type(plant_type)
        else:
            results = []  # no filter provided, could return all if needed
        return results

    def log_alert(self, plant_id: int, sensor: str, value: float, severity: str = 'warning', note: str = None):
        return self.alerts.create_alert(plant_id, sensor, value, severity, note)

    def get_alerts(self, plant_id: int = None):
        return self.alerts.get_by_plant(plant_id)
