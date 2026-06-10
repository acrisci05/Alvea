# mqtt_ingest.py - Task in background: consuma la telemetria da MQTT.
#
# Per ogni messaggio su pulseguard/baby/data:
#   1) valida il payload (Pydantic)
#   2) assicura l'esistenza del device
#   3) salva la lettura su DB (e opzionalmente su InfluxDB)
#   4) valuta le soglie -> salva gli eventuali alert
#   5) fa broadcast realtime (WebSocket + SSE) verso i client
#
# Pattern derivato da test_mqtt/main.py del corso (aiomqtt + lifespan).
import asyncio
import json
import aiomqtt

from . import config, crud, alerts, influx
from .database import AsyncSessionLocal
from .realtime import publish_event
from .schemas import ReadingIn


async def listen_to_mqtt():
    print("[mqtt] avvio listener su", f"{config.MQTT_HOST}:{config.MQTT_PORT}")
    while True:
        try:
            async with aiomqtt.Client(config.MQTT_HOST, config.MQTT_PORT) as client:
                await client.subscribe(config.TOPIC_DATA)
                print("[mqtt] sottoscritto a", config.TOPIC_DATA)
                async for message in client.messages:
                    await _handle_message(message.payload.decode())
        except asyncio.CancelledError:
            print("[mqtt] listener interrotto")
            return
        except Exception as e:
            print("[mqtt] errore, retry in 5s:", e)
            await asyncio.sleep(5)


async def _handle_message(payload_str: str):
    try:
        data = json.loads(payload_str)
        reading = ReadingIn(**data).model_dump()
    except Exception as e:
        print("[mqtt] payload non valido, scartato:", e)
        return

    async with AsyncSessionLocal() as db:
        await crud.ensure_device(db, reading["device_id"])
        saved = await crud.save_reading(db, reading)
        influx.write_reading(reading)

        fired = alerts.evaluate(reading)
        for a in fired:
            await crud.save_alert(db, reading["device_id"], a)

    await publish_event({
        "type": "reading",
        "device_id": reading["device_id"],
        "ts": str(saved.ts),
        "bpm": reading["bpm"],
        "temperature": reading["temperature"],
        "sensor_contact": reading["sensor_contact"],
        "alerts": fired,
    })
