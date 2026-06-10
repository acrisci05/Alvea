# influx.py - Scrittura opzionale su InfluxDB dal backend.
#
# NOTA ARCHITETTURALE: nel nostro stack il percorso canonico verso InfluxDB e'
# Node-RED (ESP32 -> MQTT -> Node-RED -> InfluxDB -> Grafana). Il backend scrive
# su Influx solo se INFLUX_ENABLED=true, utile se vuoi bypassare Node-RED.
# Import "pigro" cosi' il backend gira anche senza la libreria installata.
from . import config

_write_api = None


def _get_writer():
    global _write_api
    if _write_api is not None:
        return _write_api
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS
    client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN,
                            org=config.INFLUX_ORG)
    _write_api = client.write_api(write_options=SYNCHRONOUS)
    return _write_api


def write_reading(reading: dict):
    if not config.INFLUX_ENABLED:
        return
    try:
        from influxdb_client import Point
        writer = _get_writer()
        p = (
            Point("vitals")
            .tag("device_id", reading["device_id"])
            .tag("source", reading.get("source", "unknown"))
            .field("bpm", float(reading.get("bpm", 0)))
            .field("temperature", float(reading.get("temperature", 0)))
            .field("sensor_contact", 1 if reading.get("sensor_contact") else 0)
        )
        writer.write(bucket=config.INFLUX_BUCKET, record=p)
    except Exception as e:
        print("[influx] scrittura fallita:", e)
