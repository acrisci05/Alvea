# mqtt_ingest.py - Task in background: consuma la telemetria da MQTT.
#
# Per ogni messaggio su alvea/monitor/data:
#   1) valida il payload (Pydantic)
#   2) assicura l'esistenza del device
#   3) salva la lettura su DB (e opzionalmente su InfluxDB)
#   4) valuta le soglie -> salva gli eventuali alert
#   5) fa broadcast realtime (WebSocket + SSE) verso i client
#
# Pattern derivato da test_mqtt/main.py del corso (aiomqtt + lifespan).

import asyncio  # per la gestione asincrona e il sleep tra i retry
import json     # per decodificare il payload JSON che arriva dall'ESP32
import aiomqtt  # libreria asincrona per connettersi al broker MQTT

# Importa i moduli interni del backend
from . import config, crud, alerts, influx
from .database import AsyncSessionLocal  # fabbrica di sessioni DB
from .realtime import publish_event      # funzione che manda i dati in real-time ai client
from .schemas import ReadingIn           # schema Pydantic per validare il payload


async def listen_to_mqtt():
    # Funzione principale del listener MQTT. Viene avviata come task in background
    # dal lifespan di FastAPI (in main.py) e gira per tutta la vita dell'applicazione.

    print("[mqtt] avvio listener su", f"{config.MQTT_HOST}:{config.MQTT_PORT}")

    # Loop infinito: se la connessione al broker cade, riprova automaticamente
    while True:
        try:
            # Apre la connessione al broker MQTT (es. Eclipse Mosquitto nel container Docker).
            # "async with" garantisce che la connessione venga chiusa correttamente
            # anche in caso di errore.
            async with aiomqtt.Client(config.MQTT_HOST, config.MQTT_PORT) as client:

                # Si sottoscrive al topic su cui l'ESP32 pubblica la telemetria...
                await client.subscribe(config.TOPIC_DATA)
                print("[mqtt] sottoscritto a", config.TOPIC_DATA)

                # ...e al topic separato su cui il firmware pubblica gli alert
                # hardware/locali (batteria scarica, leads-off persistente,
                # tachipnea rilevata localmente). Senza questa sottoscrizione
                # quegli alert non arrivano mai al backend (vedi alerts.py
                # del firmware / AlertManager._send -> TOPIC_ALERT).
                await client.subscribe(config.TOPIC_ALERT)
                print("[mqtt] sottoscritto a", config.TOPIC_ALERT)

                # Loop asincrono: aspetta e processa ogni messaggio in arrivo.
                # "async for" non blocca: mentre aspetta un messaggio, FastAPI
                # può continuare a servire le richieste HTTP.
                async for message in client.messages:
                    topic_str = str(message.topic)
                    payload_str = message.payload.decode()

                    # Smista il messaggio in base al topic: la telemetria
                    # (.../telemetry) e gli alert hardware (.../alerts) hanno
                    # schema e gestione diversi.
                    if topic_str.endswith("/alerts"):
                        await _handle_alert_message(payload_str)
                    else:
                        await _handle_message(payload_str)

        except asyncio.CancelledError:
            # Viene lanciato quando FastAPI si sta spegnendo (lifespan → mqtt_task.cancel()).
            # Usciamo dal loop in modo pulito senza stampare un errore.
            print("[mqtt] listener interrotto")
            return

        except Exception as e:
            # Qualsiasi altro errore (broker non raggiungibile, rete caduta, ecc.):
            # logga l'errore e aspetta 5 secondi prima di riprovare a connettersi.
            # Questo rende il sistema resiliente a riavvii del broker o problemi di rete.
            print("[mqtt] errore, retry in 5s:", e)
            await asyncio.sleep(5)


async def _handle_message(payload_str: str):
    # Gestisce un singolo messaggio MQTT ricevuto dall'ESP32.
    # Il prefisso _ indica che è una funzione privata, usata solo internamente.

    # === STEP 1: VALIDAZIONE PAYLOAD ===
    try:
        # Decodifica la stringa JSON in un dizionario Python
        data = json.loads(payload_str)

        # Valida il dizionario con lo schema Pydantic ReadingIn.
        # Se mancano campi obbligatori o i tipi sono sbagliati, lancia un'eccezione.
        # model_dump() converte l'oggetto Pydantic in un dizionario normale.
        reading = ReadingIn(**data).model_dump()

    except Exception as e:
        # Payload malformato (JSON invalido, campi mancanti, tipi errati):
        # logga e scarta il messaggio senza bloccare il listener.
        print("[mqtt] payload non valido, scartato:", e)
        return

    # === STEP 2, 3, 4: DATABASE ===
    # Apre una sessione DB per tutte le operazioni di scrittura.
    # "async with" garantisce che la sessione venga chiusa alla fine del blocco.
    async with AsyncSessionLocal() as db:

        # STEP 2: assicura che il device esista nel DB.
        # Se la cavigliera manda dati prima che il caregiver la registri, la crea senza owner.
        await crud.ensure_device(db, reading["device_id"])

        # STEP 3a: salva la lettura nel DB SQLite
        saved = await crud.save_reading(db, reading)

        # STEP 3b: scrive su InfluxDB (solo se INFLUX_ENABLED=true in config.py)
        # Se disabilitato, questa funzione esce subito senza fare nulla.
        influx.write_reading(reading)

        # STEP 4: valuta le soglie cliniche sulla lettura appena ricevuta.
        # "fired" è una lista di alert (può essere vuota se tutto è nella norma).
        fired = alerts.evaluate(reading)

        # Salva ogni alert generato nel DB, uno per uno.
        for a in fired:
            await crud.save_alert(db, reading["device_id"], a)

    # === STEP 5: BROADCAST REALTIME ===
    # Manda i dati a tutti i client connessi (app mobile via WebSocket, dashboard via SSE).
    # Viene fatto FUORI dal blocco "async with db" perché non riguarda il DB:
    # anche se il broadcast fallisse, il dato è già salvato in modo sicuro.
    await publish_event({
        "type": "reading",                              # tipo di evento (il client lo usa per distinguere)
        "device_id": reading["device_id"],              # quale cavigliera ha prodotto i dati
        "patient_id": reading.get("patient_id"),        # paziente assegnato (può essere None)
        "ts": str(saved.ts),                            # timestamp assegnato dal DB
        "respiration_rate": reading.get("respiration_rate"),  # frequenza respiratoria (EDR)
        "bpm": reading.get("bpm"),                       # battito cardiaco
        "skin_temperature": reading.get("skin_temperature"),  # temperatura cutanea
        "spo2": reading.get("spo2"),                     # saturazione ossigeno
        "battery_pct": reading.get("battery_pct"),        # batteria residua (può essere None se ADC guasto)
        "sensor_contact": reading.get("sensor_contact"), # fascia a contatto?
        "device_status": reading.get("device_status"),  # stato diagnostico testuale del firmware
        "alerts": fired,                                 # lista degli alert generati (può essere [])
    })


# Mappa gravità del firmware (AlertManager._build_alert, vedi alerts.py
# firmware) -> severity usata dal backend (alerts.py / models.Alert).
_FIRMWARE_SEVERITY_MAP = {
    "WARNING": "warning",
    "CRITICAL": "critical",
    "INFO": "technical",
}


async def _handle_alert_message(payload_str: str):
    """Gestisce un alert hardware/locale pubblicato dal firmware su
    alvea/devices/<device_id>/alerts (vedi AlertManager in alerts.py del
    firmware: batteria scarica, leads-off persistente, tachipnea rilevata
    localmente, guasto sensore temperatura).

    Il firmware usa un formato diverso da quello generato da
    backend.alerts.evaluate(): {device_id, patient_id, parametro,
    descrizione, gravita, timestamp}. Qui lo traduciamo nel formato salvato
    da crud.save_alert(): {kind, severity, message, value}.
    """
    try:
        data = json.loads(payload_str)
        device_id = data["device_id"]
    except Exception as e:
        print("[mqtt] alert payload non valido, scartato:", e)
        return

    alert = {
        "kind": data.get("parametro", "unknown"),
        "severity": _FIRMWARE_SEVERITY_MAP.get(data.get("gravita"), "warning"),
        "message": data.get("descrizione", ""),
        "value": None,  # il firmware non invia un valore numerico isolato per questi alert
    }

    async with AsyncSessionLocal() as db:
        await crud.ensure_device(db, device_id)
        saved = await crud.save_alert(db, device_id, alert)

    # Broadcast realtime: stesso canale usato per le letture, type diverso
    # così l'app può distinguere un evento "reading" da un alert standalone.
    await publish_event({
        "type": "alert",
        "device_id": device_id,
        "patient_id": data.get("patient_id"),
        "ts": str(saved.ts),
        "kind": alert["kind"],
        "severity": alert["severity"],
        "message": alert["message"],
    })
