# main.py - Applicazione FastAPI di Alvea.
#
# Espone:
#   - Auth caregiver (register / login JWT)
#   - CRUD device
#   - Storico letture e alert (REST)
#   - Ingest telemetria da MQTT (task in background, vedi mqtt_ingest.py)
#   - Realtime: WebSocket (/ws/live) e SSE (/sse/live) verso app/dashboard

import asyncio
import json
from contextlib import asynccontextmanager  # per definire il lifespan dell'app

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware       # per permettere chiamate cross-origin
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm  # per il login JWT
from fastapi.responses import StreamingResponse          # per lo stream SSE
from sqlalchemy.ext.asyncio import AsyncSession
import jwt                                               # per decodificare il token JWT

from . import models, schemas, auth, crud, config
from .database import engine, get_db, Base
from .mqtt_ingest import listen_to_mqtt   # task in background che ascolta MQTT
from .realtime import manager, sse_queue  # ConnectionManager e coda SSE


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Il lifespan gestisce cosa succede all'avvio e allo spegnimento dell'app.
    # Tutto prima del "yield" viene eseguito all'avvio, tutto dopo allo spegnimento.

    # AVVIO: crea le tabelle nel DB se non esistono ancora.
    # "run_sync" esegue un'operazione sincrona (create_all) in modo asincrono.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # AVVIO: lancia il listener MQTT come task in background.
    # "create_task" avvia listen_to_mqtt() in parallelo senza bloccare FastAPI.
    mqtt_task = asyncio.create_task(listen_to_mqtt())

    # Qui FastAPI serve le richieste normalmente
    yield

    # SPEGNIMENTO: cancella il task MQTT in modo pulito.
    # listen_to_mqtt() cattura CancelledError e termina senza errori.
    mqtt_task.cancel()


# Crea l'applicazione FastAPI con titolo, versione e il lifespan definito sopra
app = FastAPI(title="Alvea API", version="1.0.0", lifespan=lifespan)

# CORS (Cross-Origin Resource Sharing): permette all'app mobile (Expo)
# e alla dashboard web di chiamare le API anche da domini/porte diversi.
# allow_origins=["*"] accetta richieste da qualsiasi origine (ok per prototipo,
# in produzione si limiterebbe ai domini specifici).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dice a FastAPI dove trovare il token JWT nelle richieste:
# lo cerca nell'header "Authorization: Bearer <token>".
# "tokenUrl=login" indica quale endpoint usare per ottenere il token (per /docs).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)):
    # Funzione di dipendenza: viene iniettata automaticamente in ogni endpoint
    # protetto che la dichiara con "Depends(get_current_user)".
    # Verifica che il token JWT sia valido e restituisce l'utente corrispondente.
    try:
        # Decodifica il token usando la chiave segreta e l'algoritmo configurati.
        # Se il token è scaduto o manomesso, jwt.decode lancia un'eccezione.
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])

        # "sub" (subject) è il campo standard JWT che contiene l'username
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token non valido")
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token scaduto o errato")

    # Cerca l'utente nel DB: se è stato eliminato dopo l'emissione del token, nega l'accesso
    user = await crud.get_caregiver_by_username(db, username=username)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utente non trovato")
    return user


# ===================== HEALTH =====================

@app.get("/")
def root():
    # Endpoint di controllo: serve a verificare che il backend sia attivo.
    # Usato da Docker o da sistemi di monitoraggio per sapere se il servizio risponde.
    return {"service": "Alvea API", "status": "ok"}


# ===================== AUTH =====================

@app.post("/register", response_model=schemas.CaregiverResponse)
async def register(data: schemas.CaregiverCreate, db: AsyncSession = Depends(get_db)):
    # Registra un nuovo account caregiver.
    # FastAPI valida automaticamente il body con CaregiverCreate (username + password).
    # Se lo username esiste già, risponde con errore 400.
    if await crud.get_caregiver_by_username(db, data.username):
        raise HTTPException(400, "Username gia' registrato")
    return await crud.create_caregiver(db, data)


@app.post("/login", response_model=schemas.Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Autentica un caregiver e restituisce un token JWT.
    # OAuth2PasswordRequestForm legge username e password dal body in formato form
    # (non JSON): è lo standard OAuth2 per il login.
    user = await crud.get_caregiver_by_username(db, form.username)
    if not user or not auth.verify_password(form.password, user.hashed_password):
        raise HTTPException(400, "Credenziali errate")
    # Crea il token con lo username come "subject" e lo restituisce
    return schemas.Token(access_token=auth.create_access_token({"sub": user.username}))


# ===================== DEVICE =====================

@app.post("/devices", response_model=schemas.DeviceResponse)
async def create_device(data: schemas.DeviceCreate, db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    # Associa una cavigliera all'account del caregiver autenticato.
    # Gestisce due casi:
    # 1) il device non esiste → lo crea e lo associa al caregiver
    # 2) il device esiste ma senza owner (la telemetria è arrivata prima) → lo rivendica
    # 3) il device esiste già con un owner → errore 400
    existing = await crud.get_device(db, data.device_id)
    if existing and existing.owner_id:
        raise HTTPException(400, "Device gia' associato")
    if existing:
        # Rivendica il device orfano: imposta owner e baby_name
        existing.owner_id = user.id
        existing.baby_name = data.baby_name
        await db.commit()
        await db.refresh(existing)
        return existing
    return await crud.create_device(db, data, user.id)


@app.get("/devices", response_model=list[schemas.DeviceResponse])
async def list_devices(db: AsyncSession = Depends(get_db),
                       user: models.Caregiver = Depends(get_current_user)):
    # Restituisce tutte le cavigliere del caregiver autenticato.
    # Grazie a get_current_user, ogni utente vede solo i propri device.
    return await crud.get_devices_for_owner(db, user.id)


# ===================== LETTURE / ALERT =====================

@app.get("/devices/{device_id}/readings", response_model=list[schemas.ReadingResponse])
async def device_readings(device_id: str, limit: int = 120,
                          db: AsyncSession = Depends(get_db),
                          user: models.Caregiver = Depends(get_current_user)):
    # Restituisce lo storico delle ultime N letture di un device.
    # "limit" è un query parameter opzionale (es. /readings?limit=60).
    # Default 120 = 2 minuti di dati a 1 Hz.
    return await crud.get_recent_readings(db, device_id, limit)


@app.get("/devices/{device_id}/latest", response_model=schemas.ReadingResponse)
async def device_latest(device_id: str, db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    # Restituisce solo l'ultima lettura disponibile per un device.
    # Usata dall'app mobile per mostrare i valori correnti al primo caricamento,
    # prima che il WebSocket inizi a ricevere dati.
    r = await crud.get_latest_reading(db, device_id)
    if not r:
        raise HTTPException(404, "Nessuna lettura per questo device")
    return r


@app.get("/devices/{device_id}/alerts", response_model=list[schemas.AlertResponse])
async def device_alerts(device_id: str, limit: int = 50,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    # Restituisce lo storico degli ultimi N alert generati per un device.
    # Default 50 alert.
    return await crud.get_recent_alerts(db, device_id, limit)


# ===================== REALTIME: WEBSOCKET =====================

@app.websocket("/ws/live")
async def ws_live(ws: WebSocket):
    # Endpoint WebSocket: l'app mobile si connette qui per ricevere i dati in tempo reale.
    # Quando arriva una nuova lettura dall'ESP32, mqtt_ingest.py chiama publish_event()
    # che fa broadcast a tutti i WebSocket connessi, incluso questo.

    # Aggiunge il client alla lista e accetta la connessione
    await manager.connect(ws)
    try:
        while True:
            # Aspetta messaggi dal client (es. ping per tenere viva la connessione).
            # In questo progetto il client non manda dati, quindi li ignoriamo.
            # Il loop serve solo a tenere aperta la connessione.
            await ws.receive_text()
    except WebSocketDisconnect:
        # Il client ha chiuso la connessione: lo rimuove dalla lista
        manager.disconnect(ws)


# ===================== REALTIME: SSE =====================

@app.get("/sse/live")
async def sse_live():
    # Endpoint SSE (Server-Sent Events): alternativa al WebSocket per client
    # che preferiscono una connessione unidirezionale più semplice (es. dashboard web).
    # Il formato SSE è uno standard HTTP: ogni evento è "event: tipo\ndata: json\n\n"

    async def event_generator():
        # Generator asincrono: produce eventi all'infinito finché il client è connesso.
        while True:
            # Aspetta il prossimo evento dalla coda (messo lì da publish_event())
            event = await sse_queue.get()

            # Formato SSE standard: due righe separate da \n, blocco terminato da \n\n
            yield "event: reading\n"
            yield f"data: {json.dumps(event, default=str)}\n\n"

    # StreamingResponse mantiene aperta la connessione HTTP e manda i dati man mano.
    # "text/event-stream" è il Content-Type standard per SSE.
    # Cache-Control e Connection sono header necessari per far funzionare SSE correttamente.
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )