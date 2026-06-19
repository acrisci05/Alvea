# App mobile — Alvea (React Native / Expo)

App di esempio che mostra la telemetria **in tempo reale** via WebSocket dal
backend FastAPI, con login JWT.

## Avvio
```bash
cd mobile
npm install
npx expo start
```
Apri con l'app **Expo Go** sul telefono (stessa rete del PC).

## Configurazione
Modifica `src/config.js` e imposta `API_URL` con l'**IP del tuo PC** (non
`localhost`): es. `http://192.168.1.50:8000`. Il WebSocket viene derivato
automaticamente (`ws://.../ws/live`).

## Flusso
1. **Login/Registrazione** → ottiene un token JWT dal backend.
2. **Monitor** → si connette a `/ws/live` e aggiorna BPM, temperatura e stato
   fascia ad ogni messaggio; mostra gli allarmi. Polling REST di riserva ogni 3s.

> Nota: questa app usa il percorso **MQTT → backend → WebSocket**. Il percorso
> **BLE diretto** (firmware `main_*_ble.py`) è alternativo e richiede una
> libreria BLE (es. `react-native-ble-plx`), non inclusa in questo skeleton.
