# realtime.py - Gestione connessioni realtime verso client (app/dashboard web).
#
# Espone un ConnectionManager per WebSocket (push bidirezionale) e una coda
# broadcast riusabile anche per Server-Sent Events. Pattern derivato dagli
# esempi WebSocket/SSE del corso.

import asyncio
import json
from typing import List
from fastapi import WebSocket  # tipo della connessione WebSocket di FastAPI


class ConnectionManager:
    # Gestisce tutte le connessioni WebSocket attive.
    # Ogni volta che un client (es. app mobile) apre una connessione WebSocket,
    # viene aggiunto alla lista. Quando si disconnette, viene rimosso.

    def __init__(self):
        # Lista di tutte le connessioni WebSocket attualmente aperte.
        # Può essere vuota (nessun client connesso) o contenere più connessioni
        # (es. genitore connesso sia da telefono che da browser).
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        # Accetta la connessione WebSocket e aggiunge il client alla lista.
        # "await ws.accept()" completa l'handshake: senza questo il client
        # non riceve nulla e la connessione viene rifiutata.
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        # Rimuove il client dalla lista quando si disconnette.
        # Il controllo "if ws in self.active" evita errori se il client
        # non fosse in lista per qualche motivo (doppia disconnessione, ecc.).
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        # Invia un messaggio JSON a TUTTI i client WebSocket connessi simultaneamente.
        # Viene chiamata da publish_event() ogni volta che arriva una nuova lettura.

        # Lista dei client "morti" (connessione caduta senza disconnessione pulita)
        dead = []

        # Serializza il dizionario in stringa JSON una sola volta per tutti i client.
        # default=str converte tipi non serializzabili (es. datetime) in stringa.
        text = json.dumps(message, default=str)

        for ws in self.active:
            try:
                # Invia il messaggio al client
                await ws.send_text(text)
            except Exception:
                # Se l'invio fallisce (client disconnesso senza avvisare),
                # lo aggiunge alla lista dei morti invece di rimuoverlo subito
                # (non si modifica una lista mentre la si sta iterando).
                dead.append(ws)

        # Rimuove i client morti dalla lista dopo aver finito il ciclo
        for ws in dead:
            self.disconnect(ws)


# Coda asincrona per il fan-out verso gli stream SSE.
# SSE (Server-Sent Events) è un'alternativa al WebSocket: connessione
# unidirezionale dal server al client, più semplice ma sufficiente per
# mandare dati in tempo reale verso una dashboard web.
# La coda funziona come una "cassetta delle lettere": publish_event() mette
# i messaggi dentro, l'endpoint /sse/live li legge e li manda ai client.
sse_queue: "asyncio.Queue[dict]" = asyncio.Queue()

# Istanza globale del ConnectionManager.
# È una sola per tutta l'applicazione: tutti gli endpoint e i task
# che vogliono mandare dati in real-time usano questo oggetto.
manager = ConnectionManager()


async def publish_event(message: dict):
    # Punto di ingresso unico per mandare un evento in real-time a tutti i client.
    # Viene chiamata da mqtt_ingest.py ogni volta che arriva una nuova lettura.
    # Con una sola chiamata raggiunge sia i client WebSocket che quelli SSE.

    # Manda il messaggio a tutti i client WebSocket connessi
    await manager.broadcast(message)

    try:
        # Mette il messaggio nella coda SSE senza aspettare (put_nowait = non bloccante).
        # L'endpoint /sse/live leggerà il messaggio dalla coda e lo manderà ai client SSE.
        # Se la coda fosse piena (QueueFull), scarta il messaggio silenziosamente:
        # in un sistema real-time a 1 Hz è preferibile perdere un dato piuttosto che bloccarsi.
        sse_queue.put_nowait(message)
    except asyncio.QueueFull:
        pass