# main.py - Applicazione FastAPI di Alvea.
#
# Espone:
#   - Auth con ruoli (register / login JWT; ruoli caregiver e medico)
#   - CRUD device con controllo di proprietà (ogni utente vede solo i propri)
#   - Storico letture e alert (REST)
#   - Soglie cliniche configurabili dal medico
#   - Scheda paziente / anamnesi
#   - Audit log delle operazioni rilevanti (sicurezza e privacy)
#   - Ingest telemetria da MQTT (task in background, vedi mqtt_ingest.py)
#   - Realtime: WebSocket (/ws/live) e SSE (/sse/live) verso app/dashboard
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import (FastAPI, Depends, HTTPException, status, Request,
                     WebSocket, WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from . import models, schemas, auth, crud, config
from .database import engine, get_db, Base
from .mqtt_ingest import listen_to_mqtt
from .realtime import manager, sse_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crea le tabelle e avvia il listener MQTT in background
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mqtt_task = asyncio.create_task(listen_to_mqtt())
    yield
    mqtt_task.cancel()


app = FastAPI(title="Alvea API", version="1.1.0", lifespan=lifespan)

# CORS: l'app mobile (Expo) e la dashboard web devono poter chiamare l'API.
# Le origini sono configurabili (config.CORS_ORIGINS). Con "*" disabilitiamo
# allow_credentials: la coppia wildcard + credenziali è vietata dalla spec CORS
# e l'autenticazione viaggia comunque nell'header Authorization (Bearer).
_wildcard = "*" in config.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ===================== AUTENTICAZIONE / AUTORIZZAZIONE =====================
async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)) -> models.Caregiver:
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Token non valido o scaduto",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except jwt.PyJWTError:
        raise cred_exc
    username = payload.get("sub")
    if not username:
        raise cred_exc
    user = await crud.get_caregiver_by_username(db, username=username)
    if user is None:
        raise cred_exc
    return user


def require_medico(user: models.Caregiver = Depends(get_current_user)) -> models.Caregiver:
    """Dipendenza per gli endpoint riservati al ruolo medico."""
    if user.role != auth.ROLE_MEDICO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operazione riservata al medico")
    return user


async def authorized_device(device_id: str, db: AsyncSession,
                            user: models.Caregiver) -> models.Device:
    """Restituisce il device se l'utente è autorizzato a vederlo.

    - medico: accesso a tutti i device.
    - caregiver: solo i device di cui è proprietario.
    Solleva 404 se il device non esiste, 403 se non di competenza.
    """
    device = await crud.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device non trovato")
    if user.role != auth.ROLE_MEDICO and device.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Accesso negato: device non di tua competenza")
    return device


def _client_ip(request: Request):
    return request.client.host if request.client else None


# ===================== HEALTH =====================
@app.get("/")
def root():
    return {"service": "Alvea API", "status": "ok"}


# ===================== AUTH =====================
@app.post("/register", response_model=schemas.CaregiverResponse)
async def register(data: schemas.CaregiverCreate, request: Request,
                   db: AsyncSession = Depends(get_db)):
    if await crud.get_caregiver_by_username(db, data.username):
        raise HTTPException(400, "Username gia' registrato")
    user = await crud.create_caregiver(db, data)
    await crud.write_audit(db, action="register", username=user.username,
                           role=user.role, ip=_client_ip(request))
    return user


@app.post("/login", response_model=schemas.Token)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    user = await crud.get_caregiver_by_username(db, form.username)
    if not user or not auth.verify_password(form.password, user.hashed_password):
        await crud.write_audit(db, action="login_failed", username=form.username,
                               ip=_client_ip(request))
        raise HTTPException(400, "Credenziali errate")
    await crud.write_audit(db, action="login", username=user.username,
                           role=user.role, ip=_client_ip(request))
    token = auth.create_access_token({"sub": user.username, "role": user.role})
    return schemas.Token(access_token=token)


@app.get("/me", response_model=schemas.CaregiverResponse)
async def me(user: models.Caregiver = Depends(get_current_user)):
    return user


# ===================== DEVICE =====================
@app.post("/devices", response_model=schemas.DeviceResponse)
async def create_device(data: schemas.DeviceCreate, request: Request,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    existing = await crud.get_device(db, data.device_id)
    if existing and existing.owner_id:
        raise HTTPException(400, "Device gia' associato")
    if existing:
        existing.owner_id = user.id
        existing.baby_name = data.baby_name
        await db.commit()
        await db.refresh(existing)
        device = existing
    else:
        device = await crud.create_device(db, data, user.id)
    await crud.write_audit(db, action="claim_device", username=user.username,
                           role=user.role, resource=device.device_id,
                           ip=_client_ip(request))
    return device


@app.get("/devices", response_model=list[schemas.DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db),
                       user: models.Caregiver = Depends(get_current_user)):
    # Il medico vede tutti i pazienti; il caregiver solo i propri device.
    if user.role == auth.ROLE_MEDICO:
        return await crud.get_all_devices(db)
    return await crud.get_devices_for_owner(db, user.id)


# ===================== LETTURE / ALERT =====================
@app.get("/devices/{device_id}/readings", response_model=list[schemas.ReadingResponse])
async def device_readings(device_id: str, request: Request, limit: int = 120,
                          db: AsyncSession = Depends(get_db),
                          user: models.Caregiver = Depends(get_current_user)):
    await authorized_device(device_id, db, user)
    await crud.write_audit(db, action="read_history", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return await crud.get_recent_readings(db, device_id, limit)


@app.get("/devices/{device_id}/latest", response_model=schemas.ReadingResponse)
async def device_latest(device_id: str, db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    # Endpoint ad alta frequenza (polling live): autorizzato ma non auditato.
    await authorized_device(device_id, db, user)
    r = await crud.get_latest_reading(db, device_id)
    if not r:
        raise HTTPException(404, "Nessuna lettura per questo device")
    return r


@app.get("/devices/{device_id}/alerts", response_model=list[schemas.AlertResponse])
async def device_alerts(device_id: str, request: Request, limit: int = 50,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    await authorized_device(device_id, db, user)
    await crud.write_audit(db, action="read_alerts", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return await crud.get_recent_alerts(db, device_id, limit)


# ===================== SOGLIE CLINICHE (config. dal medico) =====================
@app.get("/devices/{device_id}/thresholds", response_model=schemas.ThresholdResponse)
async def get_device_thresholds(device_id: str, db: AsyncSession = Depends(get_db),
                                user: models.Caregiver = Depends(get_current_user)):
    await authorized_device(device_id, db, user)
    th = await crud.get_thresholds(db, device_id)
    row = await crud.get_threshold_row(db, device_id)
    return schemas.ThresholdResponse(
        device_id=device_id,
        updated_at=row.updated_at if row else None,
        updated_by=row.updated_by if row else None,
        **th,
    )


@app.put("/devices/{device_id}/thresholds", response_model=schemas.ThresholdResponse)
async def set_device_thresholds(device_id: str, data: schemas.ThresholdConfig,
                                request: Request, db: AsyncSession = Depends(get_db),
                                user: models.Caregiver = Depends(require_medico)):
    # Solo il medico può modificare le soglie; l'operazione viene auditata.
    await authorized_device(device_id, db, user)
    row = await crud.upsert_thresholds(db, device_id, data.model_dump(), user.username)
    await crud.write_audit(db, action="update_thresholds", username=user.username,
                           role=user.role, resource=device_id,
                           detail=json.dumps(data.model_dump()), ip=_client_ip(request))
    return schemas.ThresholdResponse.model_validate(row)


# ===================== SCHEDA PAZIENTE / ANAMNESI =====================
@app.get("/devices/{device_id}/patient", response_model=schemas.PatientRecordResponse)
async def get_patient(device_id: str, request: Request,
                      db: AsyncSession = Depends(get_db),
                      user: models.Caregiver = Depends(get_current_user)):
    await authorized_device(device_id, db, user)
    record = await crud.get_patient_record(db, device_id)
    if record is None:
        raise HTTPException(404, "Scheda paziente non presente")
    await crud.write_audit(db, action="read_patient_record", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return record


@app.put("/devices/{device_id}/patient", response_model=schemas.PatientRecordResponse)
async def update_patient(device_id: str, data: schemas.PatientRecordUpdate,
                         request: Request, db: AsyncSession = Depends(get_db),
                         user: models.Caregiver = Depends(get_current_user)):
    await authorized_device(device_id, db, user)
    record = await crud.upsert_patient_record(
        db, device_id, data.model_dump(exclude_unset=True), user.username)
    await crud.write_audit(db, action="update_patient_record", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return record


# ===================== AUDIT LOG (solo medico) =====================
@app.get("/audit", response_model=list[schemas.AuditLogResponse])
async def list_audit(limit: int = 100, device_id: str | None = None,
                     db: AsyncSession = Depends(get_db),
                     user: models.Caregiver = Depends(require_medico)):
    return await crud.get_audit_logs(db, limit=limit, device_id=device_id)


# ===================== REALTIME: WEBSOCKET =====================
@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            # Teniamo aperto il canale; ignoriamo eventuali messaggi dal client.
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ===================== REALTIME: SSE =====================
@app.get("/sse/live")
async def sse_live():
    async def event_generator():
        while True:
            event = await sse_queue.get()
            yield "event: reading\n"
            yield f"data: {json.dumps(event, default=str)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
