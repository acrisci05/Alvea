# App mobile Alvea (React Native / Expo)

App per il **caregiver**: monitoraggio in tempo reale dei parametri del
bambino (frequenza respiratoria via EDR, battito, temperatura cutanea,
batteria), storico, statistiche e **notifiche** sugli allarmi. Comunica con
il backend FastAPI via REST + WebSocket.

## Avvio

```bash
cd mobile
npm install
npx expo start
```

Apri poi il progetto con l'app **Expo Go** (QR code) oppure con un emulatore
iOS/Android.

## Configurazione (`src/config.js`)

- **`API_URL`** — indirizzo del backend sulla rete locale
  (es. `http://192.168.1.50:8000`). È l'unico valore da cambiare per puntare
  l'app al PC giusto: da qui derivano sia l'URL REST sia quello WebSocket
  (`getWsUrl`).
- **`DEMO_MODE`** — `true` (default) fa girare l'app con **dati simulati**,
  senza contattare il backend; impostare `false` per usare il server reale.

Con backend reale (`DEMO_MODE = false`) registra prima il device del
caregiver (`POST /devices`) e poi effettua il login.

Il dettaglio del collegamento con il backend (login/JWT, REST, WebSocket,
riconnessione) è in [`COLLEGAMENTO_BACKEND.md`](COLLEGAMENTO_BACKEND.md).

## Notifiche

Gestite in `src/Notifications.js`:

- **Notifiche locali** — mostrate quando l'app è in primo piano al ricevere
  un allarme (banner + centro notifiche). Attive sempre, anche in `DEMO_MODE`.
- **Notifiche push** (anche ad app chiusa/in background) — all'avvio l'app
  genera un **Expo Push Token** e lo registra sul backend
  (`POST /register-token`); il backend lo usa per avvisare il caregiver di un
  allarme critico tramite il servizio Expo Push. Richiedono un **dispositivo
  fisico** e un `projectId` EAS in `app.json` (`extra.eas.projectId`); in
  assenza restano attive le sole notifiche locali.

Le gravità degli allarmi (`WARNING` / `CRITICAL` / `INFO`) vengono
normalizzate e mostrate come *Attenzione* / *Critico* / *Risolto*.

## Struttura

```text
mobile/
├── App.js                 # sessione, splash, routing Login/Monitor
├── index.js               # entrypoint Expo
└── src/
    ├── config.js          # API_URL, DEMO_MODE, chiavi SecureStore
    ├── api.js             # chiamate REST + dati di demo
    ├── LoginScreen.js     # login / registrazione
    ├── MonitorScreen.js   # monitor real-time, storico, allarmi, profilo
    ├── Notifications.js    # notifiche locali + push Expo
    └── style.js           # temi e stili
```
