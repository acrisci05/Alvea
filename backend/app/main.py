# main.py - Applicazione FastAPI del backend Alvea.
#
# Espone:
#   - Auth caregiver (register / login JWT)
#   - CRUD device (registrazione, lista)
#   - Storico letture e alert (REST)
#   - Comando verso il firmware (POST /devices/{id}/command)
#   - Ingest telemetria da MQTT (task in background, vedi mqtt_ingest.py)
#   - Realtime: WebSocket (/ws/live) e SSE (/sse/live) verso l'app
import asyncio
import json
from contextlib import asynccontextmanager

import aiomqtt
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
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


app = FastAPI(title="Alvea API", version="1.0.0", lifespan=lifespan)

# CORS: l'app mobile (Expo) e la dashboard web devono poter chiamare l'API
# anche da origin diversi (es. localhost:19006 in sviluppo Expo).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)):
    """Dependency: decodifica il token JWT e restituisce il Caregiver autenticato.

    Usata come dipendenza su tutti gli endpoint che richiedono autenticazione.
    """
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non valido")
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token scaduto o errato")
    user = await crud.get_caregiver_by_username(db, username=username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utente non trovato")
    return user


# ===================== HEALTH =====================

@app.get("/")
def root():
    """Endpoint di health-check: verifica che il container sia attivo."""
    return {"service": "Alvea API", "status": "ok"}


# ===================== AUTH =====================

@app.post("/register", response_model=schemas.CaregiverResponse)
async def register(data: schemas.CaregiverCreate, db: AsyncSession = Depends(get_db)):
    """Registra un nuovo account caregiver.

    Restituisce 400 se lo username è già in uso.
    """
    if await crud.get_caregiver_by_username(db, data.username):
        raise HTTPException(400, "Username già registrato")
    return await crud.create_caregiver(db, data)


@app.post("/login", response_model=schemas.Token)
async def login(form: OAuth2PasswordRequestForm = Depends(),
                db: AsyncSession = Depends(get_db)):
    """Autentica un caregiver e restituisce un token JWT Bearer.

    Il token va incluso nell'header Authorization: Bearer <token>
    in tutte le richieste agli endpoint protetti.
    """
    user = await crud.get_caregiver_by_username(db, form.username)
    if not user or not auth.verify_password(form.password, user.hashed_password):
        raise HTTPException(400, "Credenziali errate")
    return schemas.Token(access_token=auth.create_access_token({"sub": user.username}))


# ===================== DEVICE =====================

@app.post("/devices", response_model=schemas.DeviceResponse)
async def create_device(data: schemas.DeviceCreate,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Associa una cavigliera all'account caregiver autenticato.

    Se il device esiste già nel DB (es. creato automaticamente dall'ingest MQTT)
    ma non ha un owner, lo associa al caregiver corrente.
    """
    existing = await crud.get_device(db, data.device_id)
    if existing and existing.owner_id:
        raise HTTPException(400, "Device già associato a un altro account")
    if existing:
        existing.owner_id = user.id
        existing.baby_name = data.baby_name
        await db.commit()
        await db.refresh(existing)
        return existing
    return await crud.create_device(db, data, user.id)


@app.get("/devices", response_model=list[schemas.DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db),
                       user: models.Caregiver = Depends(get_current_user)):
    """Restituisce tutti i device registrati dal caregiver autenticato."""
    return await crud.get_devices_for_owner(db, user.id)


# ===================== LETTURE / ALERT =====================

@app.get("/devices/{device_id}/readings", response_model=list[schemas.ReadingResponse])
async def device_readings(device_id: str, limit: int = 120,
                          db: AsyncSession = Depends(get_db),
                          user: models.Caregiver = Depends(get_current_user)):
    """Restituisce le ultime `limit` letture del device (default 120, ~2 minuti a 1 Hz).

    Usato dall'app per costruire i grafici storici.
    """
    return await crud.get_recent_readings(db, device_id, limit)


@app.get("/devices/{device_id}/latest", response_model=schemas.ReadingResponse)
async def device_latest(device_id: str,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Restituisce l'ultima lettura disponibile del device.

    Usato dall'app al primo caricamento della schermata di monitoraggio,
    prima che il WebSocket sia connesso.
    """
    r = await crud.get_latest_reading(db, device_id)
    if not r:
        raise HTTPException(404, "Nessuna lettura per questo device")
    return r


@app.get("/devices/{device_id}/stats")
async def device_stats(device_id: str, hours: int = 24,
                       db: AsyncSession = Depends(get_db),
                       user: models.Caregiver = Depends(get_current_user)):
    """Restituisce le statistiche aggregate (media, min, max) dei parametri vitali.

    Il parametro `hours` definisce la finestra temporale da adesso a ritroso
    (default 24 ore). Utile per mostrare nell'app un riepilogo giornaliero
    del tipo "SpO2 media 97%, min 94%, max 99%".

    Esempio di risposta:
    {
      "device_id": "ALVEA_04",
      "hours": 24,
      "stats": {
        "bpm":              {"avg": 98.4, "min": 72.0, "max": 145.0, "count": 86400},
        "spo2":             {"avg": 97.1, "min": 94.0, "max": 99.0,  "count": 86400},
        "respiration_rate": {"avg": 22.3, "min": 14.0, "max": 38.0,  "count": 86400},
        "skin_temperature": {"avg": 36.8, "min": 36.1, "max": 37.9,  "count": 86400},
        "battery_pct":      {"avg": 61.2, "min": 20.0, "max": 84.5,  "count": 86400}
      }
    }
    """
    return await crud.get_stats(db, device_id, hours=hours)


@app.get("/devices/{device_id}/alerts", response_model=list[schemas.AlertResponse])
async def device_alerts(device_id: str, limit: int = 50,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    """Restituisce gli ultimi `limit` allarmi generati per il device."""
    return await crud.get_recent_alerts(db, device_id, limit)


# ===================== COMANDI DEVICE =====================

@app.post("/devices/{device_id}/command", status_code=200)
async def send_device_command(device_id: str,
                               cmd: schemas.DeviceCommand,
                               db: AsyncSession = Depends(get_db),
                               user: models.Caregiver = Depends(get_current_user)):
    """Invia un comando di configurazione alla cavigliera via MQTT.

    Il firmware ascolta il topic alvea/devices/<device_id>/commands e
    aggiorna la propria configurazione senza riavvio (Requisito 8).

    Comandi supportati (da DeviceCommand):
      - publish_period_s: cambia la frequenza di invio dati (es. 2 = ogni 2 secondi)
      - patient_id: associa o disassocia il paziente dal dispositivo

    Restituisce 404 se il device non esiste o non appartiene al caregiver.
    Restituisce 503 se il broker MQTT non è raggiungibile.
    """
    # Verifica che il device esista e appartenga a questo caregiver
    device = await crud.get_device(db, device_id)
    if not device or device.owner_id != user.id:
        raise HTTPException(404, "Device non trovato o non autorizzato")

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

    return {"status": "ok", "device_id": device_id, "command": payload}


# ===================== REALTIME: WEBSOCKET =====================

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    """Canale WebSocket per ricevere la telemetria in tempo reale.

    L'app si connette qui e riceve un evento JSON per ogni lettura pubblicata
    dal firmware, senza dover fare polling REST.
    """
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