# Documento — Il collegamento dell'App con il Backend

**Progetto Alvea — Gruppo 04, A.A. 2025/2026**

Questo documento descrive **come l'app mobile si collega al backend**
(FastAPI) per autenticarsi e ricevere i dati. Vale sia per la versione
completa sia per quella a schermata singola: <u>il collegamento col backend
è identico nelle due versioni.</u> Tutte le funzioni di rete dell'app sono
in `mobile/src/api.js`; la configurazione in `mobile/src/config.js`.

---

## 1. Configurazione: dove si trova il backend

In **`mobile/src/config.js`**:

- **`API_URL`** — l'indirizzo del backend sulla rete locale (es.
  `http://192.168.1.33:8000`). <u>È l'unico valore da cambiare per puntare
  l'app al PC giusto:</u> da qui derivano sia l'URL REST sia quello
  WebSocket.
- **`getWsUrl(token)`** — costruisce l'URL del canale realtime trasformando
  `http` in `ws` e aggiungendo il token: `ws://<server>/ws/live?token=<JWT>`.
- **`DEMO_MODE`** — se `true`, l'app usa dati finti e **non contatta il
  backend**; <u>per usare l'hardware reale deve essere `false`.</u>

Tutte le chiamate REST passano per l'helper **`fetchWithTimeout()`**, che
annulla la richiesta dopo 8 secondi e mostra "Server non raggiungibile"
invece di lasciare l'app bloccata.

---

## 2. Login: ottenere il token (autenticazione)

1. L'app chiama **`loginUser(username, password)`** → `POST /login`.
2. Il backend verifica le credenziali e <u>restituisce un **token JWT**
   (`access_token`), il ruolo e il `device_id` principale dell'utente.</u>
3. L'app salva token e device_id e li usa da quel momento in poi.

<u>Il token JWT è la "chiave" che l'app deve presentare ad ogni richiesta
successiva:</u> senza, il backend risponde `401 Unauthorized`. Ha una
scadenza (60 minuti) ed è firmato dal backend con una chiave segreta, quindi
non può essere falsificato.

---

## 3. Le richieste REST (storico, ultimo dato, allarmi)

Ogni chiamata REST include il token nell'header
`Authorization: Bearer <token>`:

| Funzione app (`api.js`)     | Endpoint backend                       | A cosa serve                          |
|-----------------------------|----------------------------------------|---------------------------------------|
| `fetchLatestReading()`      | `GET /devices/{id}/latest`             | ultimo valore (usato dal fallback)    |
| `fetchSensorHistory()`      | `GET /devices/{id}/history`            | storico letture (grafici/elenco)      |
| `fetchAlertHistory()`       | `GET /devices/{id}/alerts`             | storico allarmi                       |

<u>Prima di rispondere, il backend verifica che l'utente sia autorizzato a
vedere quel dispositivo</u> (un caregiver vede solo i propri device, un
medico tutti): è il controllo `authorized_device()` lato server, che
garantisce che un paziente non acceda mai ai dati di un altro.

---

## 4. Il canale in tempo reale (WebSocket)

Questo è il collegamento più importante per il monitoraggio dal vivo:

1. L'app apre una `WebSocket` verso **`getWsUrl(token)`**
   (`/ws/live?token=<JWT>`).
2. Il backend (endpoint `ws_live`) <u>valida il token prima di accettare la
   connessione</u>: se non è valido, la rifiuta (codice 403).
3. Da quel momento, **ogni volta che il dispositivo pubblica una nuova
   lettura**, il backend la inoltra a tutti i client connessi; l'app la
   riceve in `ws.onmessage` e aggiorna lo schermo.
4. Se la connessione cade, l'app si <u>riconnette da sola con attese
   crescenti (backoff esponenziale)</u> e, nel frattempo, usa il polling
   REST come rete di sicurezza.

---

## 5. Notifiche push (allarmi anche con app chiusa)

All'avvio, l'app registra sul backend il proprio token di notifica push
(**`registerPushToken()`** → `POST /register-token`). <u>Questo permette al
backend di avvisare il genitore di un allarme critico anche quando l'app è
in background o chiusa</u> — cosa che il solo WebSocket (attivo solo ad app
aperta) non potrebbe fare.

---

## 6. Riepilogo del flusso

```
config.js (API_URL, getWsUrl, DEMO_MODE)
        │
loginUser() ─────────────▶ POST /login ─────────▶ token JWT + device_id
        │
        ├─ fetchSensorHistory()/fetchAlertHistory() ─▶ GET /history, /alerts
        ├─ fetchLatestReading() (fallback) ──────────▶ GET /latest
        └─ WebSocket getWsUrl(token) ────────────────▶ /ws/live  (dati realtime)
```

<u>In una frase: l'app fa login per ottenere un token, lo usa per aprire un
canale WebSocket e per ogni richiesta REST, e riceve così i dati del
paziente in tempo reale e su richiesta.</u> Cambiare interfaccia (tab o
schermata singola) non tocca nulla di questo flusso.
