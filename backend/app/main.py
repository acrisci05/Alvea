# main.py - Applicazione FastAPI del backend Alvea.
#
# Espone:
#   - Auth con ruoli RBAC (register / login JWT; ruoli caregiver e medico)
#   - CRUD device con controllo di proprietà (ogni utente vede solo i propri)
#   - Storico letture e alert (REST)
#   - Statistiche aggregate (avg/min/max)
#   - Soglie cliniche configurabili dal medico
#   - Scheda paziente / anamnesi
#   - Audit log delle operazioni rilevanti (sicurezza e privacy)
#   - Comando verso il firmware (POST /devices/{id}/commands)
#   - Registrazione push token (POST /register-token)
#   - Ingest telemetria da MQTT (task in background, vedi mqtt_ingest.py)
#   - Realtime: WebSocket (/ws/live) e SSE (/sse/live) verso l'app
import asyncio
import json
from contextlib import asynccontextmanager

import aiomqtt
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
    """Avvia il DB e il listener MQTT all'avvio del container;
    cancella il task MQTT allo spegnimento."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mqtt_task = asyncio.create_task(listen_to_mqtt())
    yield
    mqtt_task.cancel()


app = FastAPI(title="Alvea API", version="1.1.0", lifespan=lifespan)

# CORS: l'app mobile (Expo) e la dashboard web devono poter chiamare l'API
# anche da origin diversi (es. localhost:19006 in sviluppo Expo).
# Con origine "*" la specifica CORS vieta allow_credentials=True: lo
# disattiviamo in quel caso (l'auth usa comunque l'header Bearer, non i cookie).
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
    """Dependency: decodifica il token JWT e restituisce il Caregiver autenticato.

    Usata come dipendenza su tutti gli endpoint che richiedono autenticazione.
    Solleva 401 se il token è assente, scaduto, manomesso o riferito a un
    utente inesistente.
    """
    cred_exc = HTTPException(status.HTTP_401_UNAUTHORIZED,
                            "Token non valido o scaduto",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = auth.decode_token(token)
    except jwt.PyJWTError:
        # Cattura SOLO gli errori JWT (scadenza/firma), non maschera altri bug.
        raise cred_exc
    username = payload.get("sub")
    if not username:
        raise cred_exc
    user = await crud.get_caregiver_by_username(db, username=username)
    if user is None:
        raise cred_exc
    return user


def require_medico(user: models.Caregiver = Depends(get_current_user)) -> models.Caregiver:
    """Dependency per gli endpoint riservati al ruolo medico (RBAC).
    Solleva 403 se l'utente autenticato non è un medico.
    """
    if user.role != auth.ROLE_MEDICO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Operazione riservata al medico")
    return user


async def authorized_device(device_id: str, db: AsyncSession,
                            user: models.Caregiver) -> models.Device:
    """Restituisce il device solo se l'utente è autorizzato a vederlo.

    - medico: accesso a qualsiasi device (visione su tutti i pazienti);
    - caregiver: solo i device di cui è proprietario.
    Solleva 404 se il device non esiste, 403 se non è di competenza.
    Centralizza qui il controllo di proprietà (data isolation) richiesto dal
    Punto 4: "ogni utente visualizza esclusivamente i propri dati".
    """
    device = await crud.get_device(db, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device non trovato")
    if user.role != auth.ROLE_MEDICO and device.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Accesso negato: device non di tua competenza")
    return device


def _client_ip(request: Request):
    """IP del client per l'audit log (può essere None dietro alcuni proxy)."""
    return request.client.host if request.client else None


# ===================== HEALTH =====================

@app.get("/")
def root():
    """Endpoint di health-check: verifica che il container sia attivo."""
    return {"service": "Alvea API", "status": "ok"}


# ===================== AUTH =====================

@app.post("/register", response_model=schemas.CaregiverResponse)
async def register(data: schemas.CaregiverCreate, request: Request,
                   db: AsyncSession = Depends(get_db)):
    """Registra un nuovo account (caregiver o, a scopo didattico, medico).

    Restituisce 400 se lo username è già in uso. Eventuali dati anagrafici del
    paziente inviati dall'app insieme alla registrazione vengono ignorati qui:
    la scheda paziente si gestisce per-device (vedi /devices/{id}/patient).
    """
    if await crud.get_caregiver_by_username(db, data.username):
        raise HTTPException(400, "Username già registrato")
    user = await crud.create_caregiver(db, data)
    await crud.write_audit(db, action="register", username=user.username,
                           role=user.role, ip=_client_ip(request))
    return user


@app.post("/login", response_model=schemas.Token)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    """Autentica un utente e restituisce un token JWT Bearer.

    Oltre al token, restituisce il ruolo e il device_id principale dell'utente,
    come si aspetta l'app (loginUser → { access_token, device_id, role }).
    Il token va incluso nell'header Authorization: Bearer <token> in tutte le
    richieste agli endpoint protetti.
    """
    user = await crud.get_caregiver_by_username(db, form.username)
    if not user or not auth.verify_password(form.password, user.hashed_password):
        await crud.write_audit(db, action="login_failed", username=form.username,
                               ip=_client_ip(request))
        raise HTTPException(400, "Credenziali errate")

    # Device principale da mostrare nell'app: il primo device del caregiver;
    # per un medico (che non possiede device propri) ripieghiamo sul primo
    # device presente nel sistema, così l'app ha comunque qualcosa da aprire.
    devices = await crud.get_devices_for_owner(db, user.id)
    if not devices and user.role == auth.ROLE_MEDICO:
        devices = await crud.get_all_devices(db)
    device_id = devices[0].device_id if devices else None

    await crud.write_audit(db, action="login", username=user.username,
                           role=user.role, ip=_client_ip(request))
    token = auth.create_access_token({"sub": user.username, "role": user.role})
    return schemas.Token(access_token=token, role=user.role, device_id=device_id)


@app.get("/me", response_model=schemas.CaregiverResponse)
async def me(user: models.Caregiver = Depends(get_current_user)):
    """Restituisce i dati dell'utente autenticato (id, username, ruolo)."""
    return user


# ===================== DEVICE =====================

@app.post("/devices", response_model=schemas.DeviceResponse)
async def create_device(data: schemas.DeviceCreate, request: Request,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Associa una cavigliera all'account autenticato.

    Se il device esiste già nel DB (es. creato automaticamente dall'ingest MQTT)
    ma non ha un owner, lo associa all'utente corrente.
    """
    existing = await crud.get_device(db, data.device_id)
    if existing and existing.owner_id:
        raise HTTPException(400, "Device già associato a un altro account")
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
    """Restituisce i device dell'utente.
    Il medico vede tutti i pazienti; il caregiver solo i propri device (RBAC).
    """
    if user.role == auth.ROLE_MEDICO:
        return await crud.get_all_devices(db)
    return await crud.get_devices_for_owner(db, user.id)


# ===================== LETTURE / ALERT =====================

# L'app chiama GET /devices/{id}/history; manteniamo anche /readings come
# alias storico. Stesso handler per entrambe le rotte.
@app.get("/devices/{device_id}/history", response_model=list[schemas.ReadingResponse])
@app.get("/devices/{device_id}/readings", response_model=list[schemas.ReadingResponse])
async def device_readings(device_id: str, request: Request, limit: int = 120,
                          db: AsyncSession = Depends(get_db),
                          user: models.Caregiver = Depends(get_current_user)):
    """Restituisce le ultime `limit` letture del device (default 120, ~2 minuti a 1 Hz).
    Usato dall'app per costruire i grafici storici. Richiede l'autorizzazione
    sul device e viene tracciato nell'audit log.
    """
    await authorized_device(device_id, db, user)
    await crud.write_audit(db, action="read_history", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return await crud.get_recent_readings(db, device_id, limit)


@app.get("/devices/{device_id}/latest", response_model=schemas.ReadingResponse)
async def device_latest(device_id: str,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Restituisce l'ultima lettura disponibile del device.

    Endpoint ad alta frequenza (polling live prima del WebSocket): autorizzato
    ma non tracciato in audit per non intasare il log.
    """
    await authorized_device(device_id, db, user)
    r = await crud.get_latest_reading(db, device_id)
    if not r:
        raise HTTPException(404, "Nessuna lettura per questo device")
    return r


@app.get("/devices/{device_id}/stats")
async def device_stats(device_id: str, hours: int = 24,
                       db: AsyncSession = Depends(get_db),
                       user: models.Caregiver = Depends(get_current_user)):
    """Statistiche aggregate (media, min, max) dei parametri vitali del device.
    `hours` definisce la finestra temporale a ritroso (default 24 ore).
    """
    await authorized_device(device_id, db, user)
    return await crud.get_stats(db, device_id, hours=hours)


@app.get("/devices/{device_id}/alerts", response_model=list[schemas.AlertResponse])
async def device_alerts(device_id: str, request: Request, limit: int = 50,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Restituisce gli ultimi `limit` allarmi generati per il device."""
    await authorized_device(device_id, db, user)
    await crud.write_audit(db, action="read_alerts", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return await crud.get_recent_alerts(db, device_id, limit)


# ===================== SOGLIE CLINICHE (config. dal medico) =====================

@app.get("/devices/{device_id}/thresholds", response_model=schemas.ThresholdResponse)
async def get_device_thresholds(device_id: str, db: AsyncSession = Depends(get_db),
                                user: models.Caregiver = Depends(get_current_user)):
    """Restituisce le soglie cliniche effettive del device (configurate dal
    medico se presenti, altrimenti i default globali)."""
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
    """Imposta le soglie cliniche del device. Riservato al medico (RBAC); la
    modifica viene tracciata nell'audit log con il dettaglio dei nuovi valori."""
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
    """Restituisce la scheda paziente associata al device (Punto 9)."""
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
    """Crea o aggiorna la scheda paziente del device (aggiorna solo i campi forniti)."""
    await authorized_device(device_id, db, user)
    record = await crud.upsert_patient_record(
        db, device_id, data.model_dump(exclude_unset=True), user.username)
    await crud.write_audit(db, action="update_patient_record", username=user.username,
                           role=user.role, resource=device_id, ip=_client_ip(request))
    return record


# ===================== COMANDI DEVICE =====================

# L'app chiama POST /devices/{id}/commands (plurale, come il topic MQTT
# .../commands); manteniamo /command come alias storico.
@app.post("/devices/{device_id}/commands", status_code=200)
@app.post("/devices/{device_id}/command", status_code=200)
async def send_device_command(device_id: str,
                               cmd: schemas.DeviceCommand,
                               request: Request,
                               db: AsyncSession = Depends(get_db),
                               user: models.Caregiver = Depends(get_current_user)):
    """Invia un comando di configurazione alla cavigliera via MQTT.

    Il firmware ascolta il topic alvea/devices/<device_id>/commands e
    aggiorna la propria configurazione senza riavvio (Punto 8).

    Comandi supportati (DeviceCommand):
      - publish_period_s: frequenza di invio dati (es. 2 = ogni 2 secondi)
      - patient_id: associa o disassocia il paziente dal dispositivo

    Restituisce 404/403 se il device non esiste o non è di competenza,
    503 se il broker MQTT non è raggiungibile.
    """
    await authorized_device(device_id, db, user)

    # Costruisce il topic di destinazione per questo specifico device
    topic = config.TOPIC_CMD_TEMPLATE.format(device_id=device_id)

    # Filtra i campi None: invia solo i parametri esplicitamente impostati
    payload = {k: v for k, v in cmd.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(400, "Nessun parametro di comando specificato")

    # Pubblica il comando sul broker MQTT (connessione one-shot)
    try:
        async with aiomqtt.Client(config.MQTT_HOST, config.MQTT_PORT) as client:
            await client.publish(topic, json.dumps(payload))
    except Exception as e:
        raise HTTPException(503, f"Broker MQTT non raggiungibile: {e}")

    await crud.write_audit(db, action="send_command", username=user.username,
                           role=user.role, resource=device_id,
                           detail=json.dumps(payload), ip=_client_ip(request))
    return {"status": "ok", "device_id": device_id, "command": payload}


# ===================== NOTIFICHE PUSH =====================

@app.post("/register-token")
async def register_push_token(data: schemas.PushTokenIn,
                              db: AsyncSession = Depends(get_db),
                              user: models.Caregiver = Depends(get_current_user)):
    """Registra l'Expo push token dell'app, associandolo all'utente autenticato.
    Il backend lo userà per inviare una notifica sugli alert critici del device.
    Rotta allineata a quanto chiama l'app (PUSH_API_URL/register-token)."""
    await crud.register_push_token(db, data.token, user.id, data.device_id)
    return {"message": "Token registrato"}


# ===================== AUDIT LOG (solo medico) =====================

@app.get("/audit", response_model=list[schemas.AuditLogResponse])
async def list_audit(limit: int = 100, device_id: str | None = None,
                     db: AsyncSession = Depends(get_db),
                     user: models.Caregiver = Depends(require_medico)):
    """Consultazione del registro di audit. Riservato al medico (RBAC)."""
    return await crud.get_audit_logs(db, limit=limit, device_id=device_id)


# ===================== REALTIME: WEBSOCKET =====================

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket, token: str | None = None):
    """Canale WebSocket per ricevere la telemetria in tempo reale.

    L'app si connette con /ws/live?token=<JWT> (vedi getWsUrl in config.js).
    Se viene fornito un token lo validiamo e rifiutiamo la connessione se non è
    valido; se assente accettiamo comunque (es. dashboard interne sulla LAN).
    """
    if token is not None:
        try:
            auth.decode_token(token)
        except jwt.PyJWTError:
            await ws.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    await manager.connect(ws)
    try:
        while True:
            # Manteniamo aperto il canale; i messaggi dal client sono ignorati.
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ===================== REALTIME: SSE =====================

@app.get("/sse/live")
async def sse_live():
    """Stream Server-Sent Events: alternativa al WebSocket per client che non
    supportano WebSocket (es. alcune versioni del browser su HTTP/2).
    """
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
