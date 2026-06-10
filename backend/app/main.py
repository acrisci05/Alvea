# main.py - Applicazione FastAPI di PulseGuard-Baby.
#
# Espone:
#   - Auth caregiver (register / login JWT)
#   - CRUD device
#   - Storico letture e alert (REST)
#   - Ingest telemetria da MQTT (task in background, vedi mqtt_ingest.py)
#   - Realtime: WebSocket (/ws/live) e SSE (/sse/live) verso app/dashboard
import asyncio
import json
from contextlib import asynccontextmanager

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
    # Crea le tabelle e avvia il listener MQTT in background
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    mqtt_task = asyncio.create_task(listen_to_mqtt())
    yield
    mqtt_task.cancel()


app = FastAPI(title="PulseGuard-Baby API", version="1.0.0", lifespan=lifespan)

# CORS: l'app mobile (Expo) e la dashboard web devono poter chiamare l'API
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
    return {"service": "PulseGuard-Baby API", "status": "ok"}


# ===================== AUTH =====================
@app.post("/register", response_model=schemas.CaregiverResponse)
async def register(data: schemas.CaregiverCreate, db: AsyncSession = Depends(get_db)):
    if await crud.get_caregiver_by_username(db, data.username):
        raise HTTPException(400, "Username gia' registrato")
    return await crud.create_caregiver(db, data)


@app.post("/login", response_model=schemas.Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await crud.get_caregiver_by_username(db, form.username)
    if not user or not auth.verify_password(form.password, user.hashed_password):
        raise HTTPException(400, "Credenziali errate")
    return schemas.Token(access_token=auth.create_access_token({"sub": user.username}))


# ===================== DEVICE =====================
@app.post("/devices", response_model=schemas.DeviceResponse)
async def create_device(data: schemas.DeviceCreate, db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    existing = await crud.get_device(db, data.device_id)
    if existing and existing.owner_id:
        raise HTTPException(400, "Device gia' associato")
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
    return await crud.get_devices_for_owner(db, user.id)


# ===================== LETTURE / ALERT =====================
@app.get("/devices/{device_id}/readings", response_model=list[schemas.ReadingResponse])
async def device_readings(device_id: str, limit: int = 120,
                          db: AsyncSession = Depends(get_db),
                          user: models.Caregiver = Depends(get_current_user)):
    return await crud.get_recent_readings(db, device_id, limit)


@app.get("/devices/{device_id}/latest", response_model=schemas.ReadingResponse)
async def device_latest(device_id: str, db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    r = await crud.get_latest_reading(db, device_id)
    if not r:
        raise HTTPException(404, "Nessuna lettura per questo device")
    return r


@app.get("/devices/{device_id}/alerts", response_model=list[schemas.AlertResponse])
async def device_alerts(device_id: str, limit: int = 50,
                        db: AsyncSession = Depends(get_db),
                        user: models.Caregiver = Depends(get_current_user)):
    return await crud.get_recent_alerts(db, device_id, limit)


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
