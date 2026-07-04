# realtime.py - Gestione connessioni realtime verso client (app/dashboard web).
#
# Espone un ConnectionManager per WebSocket (push verso l'app) e un insieme di
# abbonati per i Server-Sent Events. In entrambi i casi ogni connessione porta
# con sé l'ambito di visibilità dell'utente autenticato, così il broadcast
# rispetta l'isolamento dei dati (RBAC):
#   - caregiver (genitore): riceve SOLO la telemetria dei propri device;
#   - medico: riceve la telemetria di tutti i device (visione clinica completa).
# L'ambito è rappresentato come:
#   - set[str]  -> insieme dei device_id visibili (caregiver);
#   - None      -> nessun filtro, vede tutti i device (medico).

import asyncio
import json
from typing import Optional, Set
from fastapi import WebSocket  # tipo della connessione WebSocket di FastAPI


def _can_see(scope: Optional[Set[str]], device_id) -> bool:
    """Decide se una connessione con l'ambito `scope` può ricevere un evento
    relativo a `device_id`.
    - scope None  -> medico: vede tutto;
    - scope set   -> caregiver: solo i device di cui è proprietario.
    """
    if scope is None:
        return True
    return device_id in scope


class ConnectionManager:
    # Gestisce tutte le connessioni WebSocket attive.
    # Ogni volta che un client (es. app mobile) apre una connessione WebSocket,
    # viene aggiunto alla mappa insieme al suo ambito di visibilità. Quando si
    # disconnette, viene rimosso.

    def __init__(self):
        # Mappa "connessione -> ambito di visibilità".
        # L'ambito è l'insieme dei device_id visibili al client (None = medico,
        # vede tutti). Serve al broadcast per non inviare a un genitore la
        # telemetria di un device che non è il suo (isolamento dei dati).
        self.active: dict[WebSocket, Optional[Set[str]]] = {}

    async def connect(self, ws: WebSocket, scope: Optional[Set[str]]):
        # Accetta la connessione WebSocket e registra il client con il suo ambito.
        # "await ws.accept()" completa l'handshake: senza questo il client
        # non riceve nulla e la connessione viene rifiutata.
        await ws.accept()
        self.active[ws] = scope

    def disconnect(self, ws: WebSocket):
        # Rimuove il client dalla mappa quando si disconnette.
        # pop con default None non solleva errori se il client non è presente
        # (doppia disconnessione, ecc.).
        self.active.pop(ws, None)

    async def broadcast(self, message: dict):
        # Invia un messaggio JSON ai client WebSocket connessi AUTORIZZATI a
        # vederlo. Viene chiamata da publish_event() a ogni nuova lettura/alert.

        device_id = message.get("device_id")

        # Serializza il dizionario in stringa JSON una sola volta per tutti i client.
        # default=str converte tipi non serializzabili (es. datetime) in stringa.
        text = json.dumps(message, default=str)

        # Lista dei client "morti" (connessione caduta senza disconnessione pulita)
        dead = []

        # list(...) crea una copia: iteriamo in sicurezza anche se la mappa
        # viene modificata (disconnessioni) durante il ciclo.
        for ws, scope in list(self.active.items()):
            # Isolamento dei dati: salta i client che non possono vedere questo device
            if not _can_see(scope, device_id):
                continue
            try:
                # Invia il messaggio al client
                await ws.send_text(text)
            except Exception:
                # Se l'invio fallisce (client disconnesso senza avvisare),
                # lo segna come "morto" invece di rimuoverlo subito
                # (non si modifica la mappa mentre la si sta iterando).
                dead.append(ws)

        # Rimuove i client morti dalla mappa dopo aver finito il ciclo
        for ws in dead:
            self.disconnect(ws)


class SseSubscriber:
    """Singolo abbonato agli Server-Sent Events.

    SSE (Server-Sent Events) è un'alternativa al WebSocket: connessione
    unidirezionale dal server al client, più semplice ma sufficiente per
    inviare dati in tempo reale a una dashboard web. A differenza del WebSocket
    ogni abbonato ha la PROPRIA coda: così un evento raggiunge tutti i client
    (con l'unica coda condivisa sarebbe stato consumato da uno solo di essi) e
    può essere filtrato per ambito, come per il WebSocket.
    """

    def __init__(self, scope: Optional[Set[str]]):
        self.queue: "asyncio.Queue[dict]" = asyncio.Queue()
        self.scope = scope  # None = medico (tutti), set = caregiver (i propri)


# Insieme degli abbonati SSE attivi. Ogni endpoint /sse/live registra il proprio
# abbonato all'apertura e lo rimuove alla chiusura dello stream.
_sse_subscribers: "set[SseSubscriber]" = set()


def sse_subscribe(scope: Optional[Set[str]]) -> SseSubscriber:
    """Registra un nuovo abbonato SSE con il suo ambito di visibilità."""
    sub = SseSubscriber(scope)
    _sse_subscribers.add(sub)
    return sub


def sse_unsubscribe(sub: SseSubscriber):
    """Rimuove un abbonato SSE (a stream chiuso)."""
    _sse_subscribers.discard(sub)


# Istanza globale del ConnectionManager (una sola per tutta l'applicazione).
manager = ConnectionManager()


async def publish_event(message: dict):
    # Punto di ingresso unico per inviare un evento in tempo reale ai client.
    # Viene chiamata da mqtt_ingest.py ogni volta che arriva una nuova lettura
    # (o un alert). Con una sola chiamata raggiunge sia i client WebSocket sia
    # quelli SSE, applicando in entrambi i casi il filtro di isolamento dei dati.

    # Invia ai client WebSocket connessi (filtrati per ambito nel broadcast).
    await manager.broadcast(message)

    device_id = message.get("device_id")

    # Fan-out verso gli abbonati SSE, saltando quelli non autorizzati a vedere
    # questo device. Ogni abbonato ha una coda propria: put_nowait non blocca;
    # se la coda fosse piena (QueueFull) l'evento viene scartato per quel client.
    for sub in list(_sse_subscribers):
        if not _can_see(sub.scope, device_id):
            continue
        try:
            sub.queue.put_nowait(message)
        except asyncio.QueueFull:
            pass
