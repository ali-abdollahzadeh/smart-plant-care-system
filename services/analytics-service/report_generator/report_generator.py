import logging
import datetime
from typing import List, Tuple, Optional

from database.influxdb import query_data


def _fetch_influx_series(days: int = 7, plant_id: Optional[str] = None) -> Tuple[List[float], List[float], List[float]]:
    """Query InfluxDB for the last `days` of sensor readings.

    Returns three series: temperature, humidity, soil_moisture.
    """
    # Build Flux query
    bucket_var = 'sensor_data'
    time_range = f"- {days}d" if days else "-7d"

    filters = [
        'r._measurement == "sensor_readings"',
        '(r._field == "temperature" or r._field == "humidity" or r._field == "soil_moisture")',
    ]
    if plant_id:
        filters.append(f'r.plant_id == "{plant_id}"')

    filter_clause = ' and '.join(filters)

    flux = (
        f'from(bucket: "{bucket_var}")\n'
        f'  |> range(start: {time_range})\n'
        f'  |> filter(fn: (r) => {filter_clause})\n'
        f'  |> keep(columns: ["_time", "_field", "_value"])\n'
    )

    temps: List[float] = []
    hums: List[float] = []
    moistures: List[float] = []

    try:
        tables = query_data(flux)
        for table in tables:
            for record in table.records:
                value = record.get_value()
                field = record.get_field()
                if value is None:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                if field == 'temperature':
                    temps.append(numeric)
                elif field == 'humidity':
                    hums.append(numeric)
                elif field == 'soil_moisture':
                    moistures.append(numeric)
    except Exception as e:
        logging.error(f"Failed to query InfluxDB for report: {e}")

    return temps, hums, moistures


def generate_weekly_report(days: int = 7, plant_id: Optional[str] = None):
    """Generate an aggregate report from InfluxDB for the requested window.

    If `plant_id` is provided, aggregates are scoped to that plant.
    """
    temps, hums, moistures = _fetch_influx_series(days=days, plant_id=plant_id)

    report = {}
    if temps:
        report['temperature'] = {
            'avg': round(sum(temps) / len(temps), 2),
            'min': min(temps),
            'max': max(temps)
        }
    if hums:
        report['humidity'] = {
            'avg': round(sum(hums) / len(hums), 2),
            'min': min(hums),
            'max': max(hums)
        }
    if moistures:
        report['soil_moisture'] = {
            'avg': round(sum(moistures) / len(moistures), 2),
            'min': min(moistures),
            'max': max(moistures)
        }
    report['generated_at'] = datetime.datetime.now().isoformat()
    if plant_id:
        report['plant_id'] = plant_id
    report['window_days'] = days
    return report
