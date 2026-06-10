# crud.py - Operazioni sul database (async). Pattern del corso esteso.
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from . import models, schemas, auth


# --- Caregiver ---
async def get_caregiver_by_username(db: AsyncSession, username: str):
    res = await db.execute(select(models.Caregiver).where(models.Caregiver.username == username))
    return res.scalars().first()

async def create_caregiver(db: AsyncSession, data: schemas.CaregiverCreate):
    user = models.Caregiver(username=data.username,
                            hashed_password=auth.hash_password(data.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# --- Device ---
async def get_device(db: AsyncSession, device_id: str):
    res = await db.execute(select(models.Device).where(models.Device.device_id == device_id))
    return res.scalars().first()

async def get_devices_for_owner(db: AsyncSession, owner_id: int):
    res = await db.execute(select(models.Device).where(models.Device.owner_id == owner_id))
    return res.scalars().all()

async def create_device(db: AsyncSession, data: schemas.DeviceCreate, owner_id: int):
    dev = models.Device(device_id=data.device_id, baby_name=data.baby_name, owner_id=owner_id)
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev

async def ensure_device(db: AsyncSession, device_id: str):
    """Crea il device se non esiste (telemetria puo' arrivare prima della
    registrazione manuale). Resta senza owner finche' un caregiver lo rivendica."""
    dev = await get_device(db, device_id)
    if dev is None:
        dev = models.Device(device_id=device_id)
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
    return dev


# --- Reading ---
async def save_reading(db: AsyncSession, r: dict):
    reading = models.Reading(
        device_id=r["device_id"],
        bpm=r.get("bpm"),
        temperature=r.get("temperature"),
        sensor_contact=r.get("sensor_contact"),
        source=r.get("source"),
    )
    db.add(reading)
    await db.commit()
    await db.refresh(reading)
    return reading

async def get_recent_readings(db: AsyncSession, device_id: str, limit: int = 120):
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(limit)
    )
    return list(reversed(res.scalars().all()))

async def get_latest_reading(db: AsyncSession, device_id: str):
    res = await db.execute(
        select(models.Reading)
        .where(models.Reading.device_id == device_id)
        .order_by(desc(models.Reading.ts))
        .limit(1)
    )
    return res.scalars().first()


# --- Alert ---
async def save_alert(db: AsyncSession, device_id: str, a: dict):
    alert = models.Alert(device_id=device_id, kind=a["kind"], severity=a["severity"],
                         message=a["message"], value=a.get("value"))
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert

async def get_recent_alerts(db: AsyncSession, device_id: str, limit: int = 50):
    res = await db.execute(
        select(models.Alert)
        .where(models.Alert.device_id == device_id)
        .order_by(desc(models.Alert.ts))
        .limit(limit)
    )
    return res.scalars().all()
