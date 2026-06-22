# crud.py - Operazioni sul database (async). Pattern del corso esteso.
#
# CRUD sta per Create, Read, Update, Delete: le quattro operazioni base
# su qualsiasi database. Ogni funzione qui corrisponde a una di queste operazioni.
# Tutti i metodi sono "async" perché FastAPI lavora in modo asincrono:
# mentre aspetta il database, può servire altre richieste nel frattempo.

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession  # sessione DB asincrona
from sqlalchemy.future import select              # per costruire query SELECT
from sqlalchemy import desc                       # per ordinare in modo decrescente

from . import models, schemas, auth


# =============================================================================
# CAREGIVER (genitore / operatore)
# =============================================================================

async def get_caregiver_by_username(db: AsyncSession, username: str):
    # Cerca un caregiver nel DB tramite username.
    # Usata al login (per verificare le credenziali) e alla registrazione
    # (per controllare che lo username non sia già preso).
    # .scalars().first() → restituisce il primo risultato o None se non esiste.
    res = await db.execute(select(models.Caregiver).where(models.Caregiver.username == username))
    return res.scalars().first()


async def create_caregiver(db: AsyncSession, data: schemas.CaregiverCreate):
    # Crea un nuovo account caregiver nel DB.
    # La password viene hashata con bcrypt prima di salvarla:
    # nel DB non viene mai memorizzata la password in chiaro.
    user = models.Caregiver(
        username=data.username,
        hashed_password=auth.hash_password(data.password)
    )
    db.add(user)        # aggiunge l'oggetto alla sessione (non ancora nel DB)
    await db.commit()   # esegue l'INSERT nel DB
    await db.refresh(user)  # rilegge dal DB per ottenere l'id assegnato
    return user


# =============================================================================
# DEVICE (cavigliera)
# =============================================================================

async def get_device(db: AsyncSession, device_id: str):
    # Cerca una cavigliera nel DB tramite il suo identificativo univoco (es. "ALVEA_04").
    # Restituisce il device o None se non esiste.
    res = await db.execute(select(models.Device).where(models.Device.device_id == device_id))
    return res.scalars().first()


async def get_devices_for_owner(db: AsyncSession, owner_id: int):
    # Restituisce tutte le cavigliere associate a un determinato caregiver.
    # Garantisce che ogni utente veda solo i propri device, mai quelli degli altri.
    res = await db.execute(select(models.Device).where(models.Device.owner_id == owner_id))
    return res.scalars().all()


async def create_device(db: AsyncSession, data: schemas.DeviceCreate, owner_id: int):
    # Crea una nuova cavigliera nel DB e la associa subito al caregiver.
    dev = models.Device(
        device_id=data.device_id,
        baby_name=data.baby_name,
        owner_id=owner_id
    )
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev


async def ensure_device(db: AsyncSession, device_id: str):
    # Assicura che il device esista nel DB, creandolo se necessario.
    # Serve perché la telemetria dell'ESP32 può arrivare PRIMA che il caregiver
    # abbia registrato il device tramite l'app. In quel caso lo creiamo
    # senza owner (owner_id=None): il caregiver lo rivendicherà dopo con POST /devices.
    dev = await get_device(db, device_id)
    if dev is None:
        dev = models.Device(device_id=device_id)
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
    return dev


# =============================================================================
# READING (lettura di telemetria)
# =============================================================================

async def save_reading(db: AsyncSession, r: dict):
    # Salva una singola lettura di telemetria nel DB.
    # Viene chiamata da mqtt_ingest.py ogni volta che arriva un messaggio dall'ESP32.
    reading = models.Reading(
        device_id=r["device_id"],
        resp_rate=r.get("resp_rate"),       # frequenza respiratoria (può essere None)
        bpm=r.get("bpm"),                   # battito cardiaco
        temperature=r.get("temperature"),   # temperatura cutanea
        sensor_contact=r.get("sensor_contact"),  # fascia a contatto? True/False
        source=r.get("source"),             # "sim" (simulatore) o "ad8232" (reale)
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading  # restituisce la lettura con l'id e il timestamp assegnati dal DB


async def get_recent_readings(db: AsyncSession, device_id: str, limit: int = 120):
    # Restituisce le ultime N letture di un device, ordinate dalla più vecchia
    # alla più recente (utile per graficare l'andamento temporale).
    # Default: 120 letture = 2 minuti di dati a 1 Hz.
    # order_by(desc(...)) → prende le più recenti, reversed() → le rimette in ordine cronologico
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(limit)
    )
    return list(reversed(res.scalars().all()))


async def get_latest_reading(db: AsyncSession, device_id: str):
    # Restituisce solo l'ultima lettura disponibile per un device.
    # Usata dall'endpoint GET /devices/{id}/latest per mostrare il valore corrente.
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(1)
    )
    return res.scalars().first()


# =============================================================================
# ALERT
# =============================================================================

async def save_alert(db: AsyncSession, device_id: str, a: dict):
    # Salva un alert nel DB.
    # Viene chiamata da mqtt_ingest.py per ogni alert generato da alerts.evaluate().
    # Un singolo messaggio MQTT può generare più alert (es. bpm alto + temp alta).
    alert = models.Alert(
        device_id=device_id,
        kind=a["kind"],         # tipo: "bpm_low", "resp_high", "contact_lost", ...
        severity=a["severity"], # gravità: "warning", "critical", "technical"
        message=a["message"],   # testo leggibile dall'utente
        value=a.get("value")    # valore numerico che ha scatenato l'alert (può essere None)
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def get_recent_alerts(db: AsyncSession, device_id: str, limit: int = 50):
    # Restituisce gli ultimi N alert di un device, dal più recente al più vecchio.
    # Usata dall'endpoint GET /devices/{id}/alerts per mostrare lo storico allarmi.
    res = await db.execute(
        select(models.Alert)
        .where(models.Alert.device_id == device_id)
        .order_by(desc(models.Alert.ts))
        .limit(limit)
    )
    return res.scalars().all()