# crud.py - Operazioni sul database (Create, Read, Update, Delete).
#
# Questo file contiene tutte le funzioni che leggono e scrivono sul DB.
# Gli endpoint in main.py non toccano mai il DB direttamente: delegano
# sempre a queste funzioni. Questo separa la logica HTTP dalla logica dati.
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from . import models, schemas, auth


# ===================== CAREGIVER =====================

async def get_caregiver_by_username(db: AsyncSession, username: str):
    """Cerca un caregiver per username. Usata al login e nella verifica JWT."""
    res = await db.execute(
        select(models.Caregiver).where(models.Caregiver.username == username)
    )
    return res.scalars().first()

async def create_caregiver(db: AsyncSession, data: schemas.CaregiverCreate):
    """Crea un nuovo account caregiver. La password viene hashata con bcrypt."""
    user = models.Caregiver(
        username=data.username,
        hashed_password=auth.hash_password(data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ===================== DEVICE =====================

async def get_device(db: AsyncSession, device_id: str):
    """Cerca un device per device_id (es. 'ALVEA_04')."""
    res = await db.execute(
        select(models.Device).where(models.Device.device_id == device_id)
    )
    return res.scalars().first()

async def get_devices_for_owner(db: AsyncSession, owner_id: int):
    """Restituisce tutti i device associati a un caregiver.
    Usata da GET /devices per mostrare solo i device dell'utente autenticato.
    """
    res = await db.execute(
        select(models.Device).where(models.Device.owner_id == owner_id)
    )
    return res.scalars().all()

async def create_device(db: AsyncSession, data: schemas.DeviceCreate, owner_id: int):
    """Crea e associa una nuova cavigliera al caregiver autenticato."""
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
    """Crea il device nel DB se non esiste ancora.

    La telemetria MQTT può arrivare prima che il caregiver registri
    manualmente il device nell'app. In quel caso lo creiamo senza owner;
    il caregiver lo rivendicherà in seguito tramite POST /devices.
    """
    dev = await get_device(db, device_id)
    if dev is None:
        dev = models.Device(device_id=device_id)
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
    return dev


# ===================== READING =====================

async def save_reading(db: AsyncSession, r: dict):
    """Salva una singola lettura di telemetria nel DB.

    Il dizionario 'r' viene da ReadingIn.model_dump() in mqtt_ingest.py
    e contiene tutti i parametri vitali inviati dal firmware.
    """
    reading = models.Reading(
        device_id        = r["device_id"],
        patient_id       = r.get("patient_id"),       # può essere None se non assegnato
        bpm              = r.get("bpm"),
        skin_temperature = r.get("skin_temperature"),  # nome allineato al firmware
        spo2             = r.get("spo2"),
        respiration_rate = r.get("respiration_rate"),
        battery_pct      = r.get("battery_pct"),       # può essere None se ADC guasto
        sensor_contact   = r.get("sensor_contact"),
        device_status    = r.get("device_status"),
        source           = r.get("source"),
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading

async def get_recent_readings(db: AsyncSession, device_id: str, limit: int = 120):
    """Restituisce le ultime `limit` letture in ordine cronologico crescente.

    Ordine crescente (reversed) perché l'app usa questi dati per disegnare
    grafici da sinistra (più vecchio) a destra (più recente).
    Default 120 letture = circa 2 minuti di dati a 1 Hz.
    """
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(limit)
    )
    return list(reversed(res.scalars().all()))

async def get_latest_reading(db: AsyncSession, device_id: str):
    """Restituisce l'ultima lettura disponibile per il device.

    Usata da GET /devices/{id}/latest: l'app la chiama al primo caricamento
    della schermata di monitoraggio, prima che il WebSocket sia connesso.
    """
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(1)
    )
    return res.scalars().first()


# ===================== ALERT =====================

async def save_alert(db: AsyncSession, device_id: str, a: dict):
    """Salva un allarme generato da alerts.evaluate() nel DB.

    Chiamata da mqtt_ingest.py per ogni alert prodotto da una lettura.
    """
    alert = models.Alert(
        device_id = device_id,
        kind      = a["kind"],      # es. "spo2_low", "resp_high", "contact_lost"
        severity  = a["severity"],  # "warning" | "critical" | "technical"
        message   = a["message"],
        value     = a.get("value"), # valore numerico che ha scatenato l'allarme
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert

async def get_recent_alerts(db: AsyncSession, device_id: str, limit: int = 50):
    """Restituisce gli ultimi `limit` allarmi in ordine cronologico decrescente
    (il più recente per primo, utile per la lista alert nell'app).
    """
    res = await db.execute(
        select(models.Alert)
        .where(models.Alert.device_id == device_id)
        .order_by(desc(models.Alert.ts))
        .limit(limit)
    )
    return res.scalars().all()