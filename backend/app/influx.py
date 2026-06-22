# influx.py - Scrittura opzionale su InfluxDB dal backend.
#
# NOTA ARCHITETTURALE: nel nostro stack il percorso canonico verso InfluxDB è
# Node-RED (ESP32 → MQTT → Node-RED → InfluxDB → Grafana). Il backend scrive
# su Influx solo se INFLUX_ENABLED=true, utile se vuoi bypassare Node-RED.
# Import "pigro" così il backend gira anche senza la libreria installata.

# Importa la configurazione: URL, token, org, bucket e il flag di abilitazione
from . import config

# Variabile globale che tiene in memoria il write_api una volta creato.
# Inizialmente è None: verrà inizializzata solo alla prima scrittura.
# Questo pattern si chiama "lazy initialization" (inizializzazione pigra):
# non si crea la connessione finché non serve davvero.
_write_api = None


def _get_writer():
    # Restituisce il writer di InfluxDB, creandolo se non esiste ancora.
    # Usando "global" diciamo a Python che vogliamo modificare la variabile
    # globale _write_api, non crearne una locale.
    global _write_api

    # Se il writer esiste già, lo restituisce subito senza ricreare la connessione
    if _write_api is not None:
        return _write_api

    # Importa la libreria InfluxDB solo qui, non in cima al file.
    # Così se la libreria non è installata, il backend parte lo stesso
    # finché INFLUX_ENABLED=false (che è il default).
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS

    # Crea il client InfluxDB con le credenziali da config.py
    client = InfluxDBClient(
        url=config.INFLUX_URL,
        token=config.INFLUX_TOKEN,
        org=config.INFLUX_ORG
    )

    # Crea il write_api in modalità SYNCHRONOUS: aspetta la conferma di scrittura
    # prima di andare avanti. Più sicuro per un prototipo didattico.
    _write_api = client.write_api(write_options=SYNCHRONOUS)
    return _write_api


def write_reading(reading: dict):
    # Scrive una lettura su InfluxDB.
    # Viene chiamata da mqtt_ingest.py per ogni messaggio ricevuto dall'ESP32.

    # Se INFLUX_ENABLED=false (default), esce subito senza fare nulla.
    # In questo caso i dati vanno su InfluxDB tramite Node-RED, non da qui.
    if not config.INFLUX_ENABLED:
        return

    try:
        # Importa Point: è il formato dati di InfluxDB (simile a un record con tag e campi)
        from influxdb_client import Point

        writer = _get_writer()

        # Costruisce il "point" da scrivere su InfluxDB.
        # Un point è composto da:
        # - measurement: nome della "tabella" (qui "vitals")
        # - tag: metadati indicizzati usati per filtrare (device_id, source)
        # - field: valori numerici effettivi da storicizzare (bpm, temp, contact)
        p = (
            Point("vitals")
            .tag("device_id", reading["device_id"])         # es. "ALVEA_04"
            .tag("source", reading.get("source", "unknown")) # "sim" o "ad8232"
            .field("bpm", float(reading.get("bpm", 0)))
            .field("temperature", float(reading.get("temperature", 0)))
            # sensor_contact è booleano ma InfluxDB vuole un numero: 1=contatto, 0=staccato
            .field("sensor_contact", 1 if reading.get("sensor_contact") else 0)
        )

        # Scrive il point nel bucket configurato
        writer.write(bucket=config.INFLUX_BUCKET, record=p)

    except Exception as e:
        # Se la scrittura fallisce (es. InfluxDB non raggiungibile) logga l'errore
        # ma NON blocca il flusso: il dato è già salvato nel DB SQLite,
        # InfluxDB è solo uno strato aggiuntivo per Grafana.
        print("[influx] scrittura fallita:", e)