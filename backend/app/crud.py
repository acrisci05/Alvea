# crud.py - Operazioni sul database (Create, Read, Update, Delete).
#
# Questo file contiene tutte le funzioni che leggono e scrivono sul DB.
# Gli endpoint in main.py non toccano mai il DB direttamente: delegano
# sempre a queste funzioni. Questo separa la logica HTTP dalla logica dati.
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, func

from . import models, schemas, auth, config

# CAREGIVER
async def get_caregiver_by_username(db: AsyncSession, username: str):
    """Cerca un caregiver per username. Usata al login e nella verifica JWT."""
    res = await db.execute(
        select(models.Caregiver).where(models.Caregiver.username == username)
    )
    return res.scalars().first()

async def create_caregiver(db: AsyncSession, data: schemas.CaregiverCreate):
    """Crea un nuovo account caregiver. La password viene hashata con bcrypt;
    il ruolo (caregiver/medico) arriva dallo schema, con default "caregiver".
    """
    user = models.Caregiver(
        username=data.username,
        hashed_password=auth.hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# DEVICE
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

async def get_all_devices(db: AsyncSession):
    """Restituisce tutti i device del sistema.
    Usata dal ruolo medico, che ha visione su tutti i pazienti (RBAC).
    """
    res = await db.execute(select(models.Device))
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
    manualmente il device nell'app. In quel caso viene creato senza owner;
    il caregiver lo rivendicherà in seguito tramite POST /devices.
    """
    dev = await get_device(db, device_id)
    if dev is None:
        dev = models.Device(device_id=device_id)
        db.add(dev)
        await db.commit()
        await db.refresh(dev)
    return dev


async def claim_device_for_patient(db: AsyncSession, device_id: str, owner_id: int,
                                   patient_id: str, baby_name: str | None = None):
    """Associa il dispositivo al caregiver e gli assegna un patient_id.

    Usata dall'auto-assegnazione alla registrazione (POST /register): crea il
    device se non esiste ancora (la telemetria potrebbe non essere mai
    arrivata), imposta owner_id e patient_id, e aggiorna il nome del bambino
    se fornito. In questo prototipo a singola cavigliera l'ultimo caregiver
    registrato diventa proprietario del dispositivo predefinito.
    """
    dev = await get_device(db, device_id)
    if dev is None:
        dev = models.Device(device_id=device_id)
        db.add(dev)
    dev.owner_id = owner_id
    dev.patient_id = patient_id
    if baby_name:
        dev.baby_name = baby_name
    await db.commit()
    await db.refresh(dev)
    return dev


# READING
async def save_reading(db: AsyncSession, r: dict):
    """Salva una singola lettura di telemetria nel DB.

    Il dizionario 'r' viene da ReadingIn.model_dump() in mqtt_ingest.py
    e contiene tutti i parametri vitali inviati dal firmware.

    Il timestamp Unix del firmware (campo 'timestamp', float) viene convertito
    in datetime UTC. Se il firmware non lo manda, si usa l'ora corrente del server.
    Questo garantisce che il campo 'ts' nel DB rifletta sempre il momento reale
    di acquisizione del dato, non quello di arrivo al backend.
    """
    ts_unix = r.get("timestamp")
    if ts_unix:
        ts = datetime.fromtimestamp(ts_unix, tz=timezone.utc).replace(tzinfo=None)
    else:
        ts = datetime.utcnow()

    reading = models.Reading(
        device_id        = r["device_id"],
        patient_id       = r.get("patient_id"),       # può essere None se non assegnato
        ts               = ts,                       
        bpm              = r.get("bpm"),
        skin_temperature = r.get("skin_temperature"),  
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


# STATISTICHE (avg, min, max)
# Parametri vitali su cui ha senso calcolare statistiche
STAT_FIELDS = {
    "bpm":              models.Reading.bpm,
    "respiration_rate": models.Reading.respiration_rate,
    "skin_temperature": models.Reading.skin_temperature,
    "battery_pct":      models.Reading.battery_pct,
}

async def get_stats(db: AsyncSession, device_id: str, hours: int = 24) -> dict:
    """Calcola media, minimo e massimo di ogni parametro vitale nell'ultimo
    intervallo temporale specificato (default: ultime 24 ore).

    Usata da GET /devices/{id}/stats per mostrare nell'app i valori aggregati
    del giorno: "Frequenza respiratoria media 22, min 14, max 38".

    Parametri
    ----------
    device_id : str
        Identificativo del device (es. "ALVEA_04").
    hours : int
        Finestra temporale in ore da adesso a ritroso (default 24).

    Ritorna
    -------
    dict
        Per ogni parametro vitale: avg, min, max e il numero di letture
        usate per il calcolo (count). Valori None se non ci sono letture
        nel periodo.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    stats = {}

    for field_name, column in STAT_FIELDS.items():
        res = await db.execute(
            select(
                func.avg(column).label("avg"),   # media
                func.min(column).label("min"),   # minimo
                func.max(column).label("max"),   # massimo
                func.count(column).label("count") # numero letture valide
            )
            .where(models.Reading.device_id == device_id)
            .where(models.Reading.ts >= since)   # filtra per finestra temporale
            .where(column.isnot(None))           # esclude i valori None (es. battery_pct guasto)
        )
        row = res.first()
        stats[field_name] = {
            "avg":   round(row.avg, 2) if row.avg is not None else None,
            "min":   round(row.min, 2) if row.min is not None else None,
            "max":   round(row.max, 2) if row.max is not None else None,
            "count": row.count,
        }

    return {"device_id": device_id, "hours": hours, "stats": stats}


# ALERT
async def save_alert(db: AsyncSession, device_id: str, a: dict):
    """Salva un allarme generato da alerts.evaluate() nel DB.

    Chiamata da mqtt_ingest.py per ogni alert prodotto da una lettura.
    """
    alert = models.Alert(
        device_id = device_id,
        parameter = a.get("parameter"),  # es. "respiration_rate", "bpm", "contact"
        kind      = a["kind"],           # es. "resp_high", "bpm_low", "contact_lost"
        severity  = a["severity"],       # "warning" | "critical" | "technical"
        message   = a["message"],
        value     = a.get("value"),      # valore numerico che ha scatenato l'allarme
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


# SOGLIE PER-DEVICE (configurabili dal medico)
_THRESHOLD_FIELDS = (
    "resp_warn_low", "resp_warn_high", "resp_crit_low", "resp_crit_high",
    "bpm_warn_low", "bpm_warn_high", "bpm_crit_low", "bpm_crit_high",
    "temp_warn_low", "temp_warn_high", "temp_crit_low", "temp_crit_high",
)

async def get_threshold_row(db: AsyncSession, device_id: str):
    """Restituisce la riga DeviceThreshold del device, o None se assente."""
    res = await db.execute(
        select(models.DeviceThreshold).where(models.DeviceThreshold.device_id == device_id)
    )
    return res.scalars().first()

async def get_thresholds(db: AsyncSession, device_id: str) -> dict:
    """Soglie effettive per un device: configurazione dedicata se presente,
    altrimenti i default di config.
    """
    row = await get_threshold_row(db, device_id)
    if row is None:
        return dict(config.DEFAULT_THRESHOLDS)
    return {f: getattr(row, f) for f in _THRESHOLD_FIELDS}

async def upsert_thresholds(db: AsyncSession, device_id: str, data: dict, username: str):
    """Crea o aggiorna le soglie del device e registra l'autore della modifica."""
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

# SCHEDA PAZIENTE / ANAMNESI
async def get_patient_record(db: AsyncSession, device_id: str):
    """Restituisce la scheda paziente del device, o None se non presente."""
    res = await db.execute(
        select(models.PatientRecord).where(models.PatientRecord.device_id == device_id)
    )
    return res.scalars().first()

async def upsert_patient_record(db: AsyncSession, device_id: str, data: dict, username: str):
    """Crea o aggiorna la scheda paziente; aggiorna solo i campi forniti."""
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


# AUDIT LOG
async def write_audit(db: AsyncSession, action: str, username: str | None = None,
                      role: str | None = None, resource: str | None = None,
                      detail: str | None = None, ip: str | None = None):
    """Registra (append-only) un'operazione rilevante nel log di audit."""
    entry = models.AuditLog(action=action, username=username, role=role,
                            resource=resource, detail=detail, ip=ip)
    db.add(entry)
    await db.commit()
    return entry

async def get_audit_logs(db: AsyncSession, limit: int = 100, device_id: str | None = None):
    """Restituisce le ultime voci dell'audit log (le più recenti per prime),
    eventualmente filtrate per device. Consultabile solo dal medico.
    """
    q = select(models.AuditLog)
    if device_id:
        q = q.where(models.AuditLog.resource == device_id)
    q = q.order_by(desc(models.AuditLog.ts)).limit(limit)
    res = await db.execute(q)
    return res.scalars().all()


# PUSH TOKEN
async def register_push_token(db: AsyncSession, token: str, owner_id: int,
                              device_id: str | None = None):
    """Registra (o aggiorna) un Expo push token associandolo al proprietario.

    Se il token esiste già, ne aggiorna proprietario e device: lo stesso
    telefono può cambiare account o device monitorato.
    """
    existing = await db.get(models.PushToken, token)
    if existing:
        existing.owner_id = owner_id
        existing.device_id = device_id
    else:
        db.add(models.PushToken(token=token, owner_id=owner_id, device_id=device_id))
    await db.commit()

async def get_push_tokens_for_owner(db: AsyncSession, owner_id: int):
    """Restituisce la lista dei push token registrati da un proprietario."""
    res = await db.execute(
        select(models.PushToken.token).where(models.PushToken.owner_id == owner_id)
    )
    return [row[0] for row in res.all()]
