"""test_ws.py - Testa il WebSocket del backend Alvea.

Il canale /ws/live ora richiede un token JWT valido (isolamento dei dati per
ruolo): senza token la connessione viene rifiutata. Lo script ottiene il token
in uno di questi modi (in ordine di priorità):
  1. argomento da riga di comando:   python test_ws.py <TOKEN>
  2. variabile d'ambiente:           ALVEA_TOKEN=<TOKEN> python test_ws.py
  3. login automatico con le credenziali ALVEA_USER / ALVEA_PASS
     (default: demo/demo) sull'endpoint /login del backend.
"""
import subprocess, sys, os, json, urllib.parse, urllib.request

try:
    import websockets
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
    import websockets

import asyncio

HTTP_URL = os.environ.get("ALVEA_HTTP_URL", "http://localhost:8000")
WS_URL = HTTP_URL.replace("http", "ws") + "/ws/live"


def get_token() -> str:
    """Recupera il token JWT da argomento, variabile d'ambiente o login."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    if os.environ.get("ALVEA_TOKEN"):
        return os.environ["ALVEA_TOKEN"]
    # Login automatico (OAuth2 password flow: form url-encoded)
    user = os.environ.get("ALVEA_USER", "demo")
    pwd = os.environ.get("ALVEA_PASS", "demo")
    data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(f"{HTTP_URL}/login", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["access_token"]


async def listen():
    token = get_token()
    uri = f"{WS_URL}?token={token}"
    print(f"Connessione a {WS_URL} (con token) ...")
    async with websockets.connect(uri) as ws:
        print("Connesso! In attesa di dati dal firmware...\n")
        async for message in ws:
            data = json.loads(message)
            print(f"RICEVUTO: bpm={data.get('bpm')} resp={data.get('respiration_rate')} temp={data.get('skin_temperature')}")


asyncio.run(listen())
