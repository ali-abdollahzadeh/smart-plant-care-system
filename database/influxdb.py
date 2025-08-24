import os
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global client instance
_influx_client = None
_write_api = None
_query_api = None

def get_influxdb_client():
    """Get InfluxDB client instance"""
    global _influx_client
    if _influx_client is None:
        _init_influxdb_client()
    return _influx_client

def get_write_api():
    """Get InfluxDB write API"""
    global _write_api
    if _write_api is None:
        _init_influxdb_client()
    return _write_api

def get_query_api():
    """Get InfluxDB query API"""
    global _query_api
    if _query_api is None:
        _init_influxdb_client()
    return _query_api

def _init_influxdb_client():
    """Initialize InfluxDB client and APIs"""
    global _influx_client, _write_api, _query_api

    try:
        # Get configuration from environment
        url = os.environ.get('INFLUXDB_URL', 'http://influxdb:8086')
        token = os.environ.get('INFLUXDB_TOKEN', 'bFfgCm1QSnKYZDIi_6OQr-lJKhRYDNOapiXKjO9pbdUM2FWmsUNpTeWgBeUmjtvVYycWuxHLkg6QuStmadOegg==')
        org = os.environ.get('INFLUXDB_ORG', 'smart_plant_care')

        logger.info(f"Initializing InfluxDB client to {url}")

        # Create client with token
        _influx_client = InfluxDBClient(url=url, token=token, org=org)

        # Create APIs
        _write_api = _influx_client.write_api(write_options=SYNCHRONOUS)
        _query_api = _influx_client.query_api()

        logger.info("InfluxDB client initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize InfluxDB client: {e}")
        raise

def write_point(measurement, tags=None, fields=None, timestamp=None):
    """Write a single data point to InfluxDB"""
    try:
        point = Point(measurement)

        if tags:
            for key, value in tags.items():
                if value is not None:
                    point.tag(key, str(value))

        if fields:
            for key, value in fields.items():
                if value is not None:
                    if isinstance(value, (int, float)):
                        point.field(key, value)
                    else:
                        point.field(key, str(value))

        if timestamp:
            point.time(timestamp)

        bucket = os.environ.get('INFLUXDB_BUCKET', 'sensor_data')
        write_api = get_write_api()
        write_api.write(bucket=bucket, record=point)

        logger.debug(f"Wrote point to {measurement}: {tags}")

    except Exception as e:
        logger.error(f"Failed to write point to InfluxDB: {e}")
        raise

def write_points(points):
    """Write multiple data points to InfluxDB"""
    try:
        bucket = os.environ.get('INFLUXDB_BUCKET', 'sensor_data')
        write_api = get_write_api()
        write_api.write(bucket=bucket, record=points)
        logger.debug(f"Wrote {len(points)} points to InfluxDB")

    except Exception as e:
        logger.error(f"Failed to write points to InfluxDB: {e}")
        raise

def query_data(query):
    """Execute a Flux query and return results"""
    try:
        query_api = get_query_api()
        result = query_api.query(query=query)
        return result

    except Exception as e:
        logger.error(f"Failed to execute InfluxDB query: {e}")
        raise

def test_connection():
    """Test InfluxDB connection"""
    try:
        bucket = os.environ.get('INFLUXDB_BUCKET', 'sensor_data')
        query = f'from(bucket: "{bucket}") |> range(start: -1m) |> limit(n: 1)'
        result = query_data(query)
        logger.info("InfluxDB connection test successful")
        return True
    except Exception as e:
        logger.error(f"InfluxDB connection test failed: {e}")
        return False

def close_connection():
    """Close InfluxDB connection"""
    global _influx_client, _write_api, _query_api

    try:
        if _write_api:
            _write_api.close()
        if _influx_client:
            _influx_client.close()

        _influx_client = None
        _write_api = None
        _query_api = None

        logger.info("InfluxDB connection closed")

    except Exception as e:
        logger.error(f"Failed to close InfluxDB connection: {e}")
