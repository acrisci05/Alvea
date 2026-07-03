# influx.py - Scrittura opzionale su InfluxDB dal backend FastAPI.

from datetime import datetime, timezone
from . import config

_write_api = None

def _get_writer():
    """Inizializza il client InfluxDB al primo utilizzo (lazy init)."""
    global _write_api
    if _write_api is not None:
        return _write_api
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS
    client = InfluxDBClient(
        url=config.INFLUX_URL,
        token=config.INFLUX_TOKEN,
        org=config.INFLUX_ORG
    )
    _write_api = client.write_api(write_options=SYNCHRONOUS)
    return _write_api


def write_reading(reading: dict):
    """Scrive una lettura su InfluxDB come punto nella measurement 'vitals'.
    I tag (device_id, patient_id, source) sono indicizzati e usati da Grafana
    per filtrare per paziente o device. I field sono i valori numerici delle
    serie temporali su cui si calcolano medie, min, max.
    Parametri
    ----------
    reading : dict
        Dizionario con i campi del payload firmware (da ReadingIn.model_dump()).
    """
    if not config.INFLUX_ENABLED:
        return  # percorso Node-RED è quello canonico; non scrivere due volte

    try:
        from influxdb_client import Point
        writer = _get_writer()

        # Converti il timestamp Unix del firmware in datetime UTC.
        # Se il firmware non lo manda, usa l'ora corrente del server.
        ts_unix = reading.get("timestamp")
        if ts_unix:
            ts = datetime.fromtimestamp(ts_unix, tz=timezone.utc)
        else:
            ts = datetime.now(tz=timezone.utc)

        p = (
            Point("vitals")
            # --- Tag: indicizzati, usati per filtrare in Grafana ---
            .tag("device_id", reading["device_id"])
            .tag("source",    reading.get("source", "unknown"))

            # patient_id può essere None se il paziente non è ancora assegnato
            .tag("patient_id", reading.get("patient_id") or "unassigned")

            # --- Field: valori numerici delle serie temporali ---
            .field("bpm",              float(reading.get("bpm") or 0))
            .field("skin_temperature", float(reading.get("skin_temperature") or 0))
            .field("respiration_rate", float(reading.get("respiration_rate") or 0))
            .field("sensor_contact",   1 if reading.get("sensor_contact") else 0)

            # battery_pct può essere None se l'ADC della batteria è guasto
            .field("battery_pct", float(reading.get("battery_pct") or -1))

            # Timestamp esplicito: usa quello del firmware, non quello di arrivo
            .time(ts)
        )

        writer.write(bucket=config.INFLUX_BUCKET, record=p)

    except Exception as e:
        # Errore non bloccante: il dato è già salvato su SQLite
        print(f"[influx] scrittura fallita: {e}")
