# push.py - Invio notifiche push tramite il servizio Expo Push.
#
# Riceve una lista di Expo push token e inoltra il messaggio all'endpoint
# pubblico di Expo (https://exp.host/--/api/v2/push/send). Best-effort: ogni
# errore viene loggato ma non interrompe la pipeline di ingest.
import httpx

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push(tokens, title: str, body: str, data: dict | None = None):
    if not tokens:
        return
    messages = [{
        "to": t,
        "sound": "default",
        "title": title,
        "body": body,
        "data": data or {},
    } for t in tokens]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(EXPO_PUSH_URL, json=messages,
                              headers={"Content-Type": "application/json"})
    except Exception as e:
        print("[push] invio notifica fallito:", e)
