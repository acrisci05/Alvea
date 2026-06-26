# push.py - Invio notifiche push tramite il servizio Expo Push.
#
# Riceve una lista di Expo push token (registrati dall'app via
# POST /register-token) e inoltra il messaggio all'endpoint pubblico di Expo.
# Serve a notificare il caregiver di un alert critico anche quando l'app è in
# background o chiusa, cosa che le sole notifiche locali non possono fare.
#
# Best-effort: ogni errore viene loggato ma NON interrompe la pipeline di
# ingest della telemetria (il dato e l'alert sono comunque già salvati sul DB).
import httpx

# Endpoint pubblico del servizio di push di Expo.
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


async def send_push(tokens, title: str, body: str, data: dict | None = None):
    """Invia una notifica push a tutti i token Expo passati.

    Parametri
    ----------
    tokens : list[str]
        Lista di Expo push token destinatari (es. "ExponentPushToken[...]").
    title, body : str
        Titolo e corpo della notifica mostrata sul telefono.
    data : dict | None
        Dati extra (es. device_id) che l'app riceve insieme alla notifica.
    """
    if not tokens:
        return
    # Un messaggio per ciascun token, nel formato atteso da Expo.
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
        # Non bloccante: se Expo non è raggiungibile, l'alert resta comunque
        # visibile nell'app via WebSocket e nello storico REST.
        print("[push] invio notifica fallito:", e)
