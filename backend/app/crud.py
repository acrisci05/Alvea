# crud.py - Operazioni sul database (async). Pattern del corso esteso.
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from . import models, schemas, auth, config


# --- Caregiver ---
async def get_caregiver_by_username(db: AsyncSession, username: str):
    res = await db.execute(select(models.Caregiver).where(models.Caregiver.username == username))
    return res.scalars().first()

async def create_caregiver(db: AsyncSession, data: schemas.CaregiverCreate):
    user = models.Caregiver(username=data.username,
                            hashed_password=auth.hash_password(data.password),
                            role=data.role)
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

async def get_all_devices(db: AsyncSession):
    """Tutti i device: usato dal ruolo medico (visione su tutti i pazienti)."""
    res = await db.execute(select(models.Device))
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
        respiration_rate=r.get("respiration_rate"),
        skin_temperature=r.get("skin_temperature"),
        sensor_contact=r.get("sensor_contact"),
        device_status=r.get("device_status"),
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
    alert = models.Alert(device_id=device_id, parameter=a.get("parameter"),
                         kind=a["kind"], severity=a["severity"],
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


# --- Soglie per-device (configurabili dal medico) ---
_THRESHOLD_FIELDS = (
    "resp_warn_high", "resp_crit_high",
    "bpm_warn_low", "bpm_warn_high", "bpm_crit_low", "bpm_crit_high",
    "skin_temp_warn_high", "skin_temp_crit_high",
)

async def get_threshold_row(db: AsyncSession, device_id: str):
    res = await db.execute(
        select(models.DeviceThreshold).where(models.DeviceThreshold.device_id == device_id)
    )
    return res.scalars().first()

async def get_thresholds(db: AsyncSession, device_id: str) -> dict:
    """Soglie effettive per un device: configurazione dedicata se presente,
    altrimenti i default di config. Restituisce sempre tutte le 8 chiavi."""
    row = await get_threshold_row(db, device_id)
    if row is None:
        return dict(config.DEFAULT_THRESHOLDS)
    return {f: getattr(row, f) for f in _THRESHOLD_FIELDS}

async def upsert_thresholds(db: AsyncSession, device_id: str, data: dict, username: str):
    row = await get_threshold_row(db, device_id)
    if row is None:
        row = models.DeviceThreshold(device_id=device_id)
        db.add(row)
    for f in _THRESHOLD_FIELDS:
        setattr(row, f, data[f])
    row.updated_by = username
    await db.commit()
    await db.refresh(row)
    return row


# --- Scheda paziente / anamnesi ---
async def get_patient_record(db: AsyncSession, device_id: str):
    res = await db.execute(
        select(models.PatientRecord).where(models.PatientRecord.device_id == device_id)
    )
    return res.scalars().first()

async def upsert_patient_record(db: AsyncSession, device_id: str, data: dict, username: str):
    row = await get_patient_record(db, device_id)
    if row is None:
        row = models.PatientRecord(device_id=device_id)
        db.add(row)
    for k, v in data.items():
        setattr(row, k, v)
    row.updated_by = username
    await db.commit()
    await db.refresh(row)
    return row


# --- Audit log ---
async def write_audit(db: AsyncSession, action: str, username: str | None = None,
                      role: str | None = None, resource: str | None = None,
                      detail: str | None = None, ip: str | None = None):
    entry = models.AuditLog(action=action, username=username, role=role,
                            resource=resource, detail=detail, ip=ip)
    db.add(entry)
    await db.commit()
    return entry

async def get_audit_logs(db: AsyncSession, limit: int = 100, device_id: str | None = None):
    q = select(models.AuditLog)
    if device_id:
        q = q.where(models.AuditLog.resource == device_id)
    q = q.order_by(desc(models.AuditLog.ts)).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()


# --- Push token ---
async def register_push_token(db: AsyncSession, token: str, owner_id: int):
    existing = await db.get(models.PushToken, token)
    if existing:
        existing.owner_id = owner_id
    else:
        db.add(models.PushToken(token=token, owner_id=owner_id))
    await db.commit()

async def get_push_tokens_for_owner(db: AsyncSession, owner_id: int):
    res = await db.execute(
        select(models.PushToken.token).where(models.PushToken.owner_id == owner_id)
    )
    return [row[0] for row in res.all()]
