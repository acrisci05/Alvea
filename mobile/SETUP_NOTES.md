# Note di setup — Dashboard Grafana e Notifiche Push

Questo file documenta la configurazione e le funzionalità aggiuntive
dell'app: dashboard Grafana in-app e push notifications reali. Non
sostituisce `README.md` (generato da Expo Snack), lo affianca.

## 1. Dipendenza da installare

La WebView per la dashboard Grafana richiede `react-native-webview`.
Per garantire la versione compatibile con questo Expo SDK (54), va
installata con il comando Expo dedicato invece di un semplice
`npm install`:

```bash
npx expo install react-native-webview
```

(`package.json` indica già la dipendenza, ma è buona norma far girare
questo comando dopo aver scaricato/clonato il progetto, così Expo
verifica/aggiorna la versione esatta per l'SDK in uso.)

## 2. Dashboard Grafana (`src/GrafanaScreen.js`)

- Configurare `GRAFANA_URL` in `src/config.js` con l'URL reale della
  dashboard del progetto (server Grafana visto nell'incontro
  "Real-Time Ecosystem", porta 3000 di default nel `docker-compose.yml`
  dell'academy).
- Si consiglia la modalità kiosk di Grafana (`?kiosk` in coda all'URL,
  già impostato di default) per nascondere menu/sidebar e mostrare solo
  i pannelli.
- Per filtrare per paziente/device/intervallo (Punto 6 dei requisiti),
  usare le variabili di template della dashboard Grafana stessa
  (es. `&var-device_id=ALVEA_04`) direttamente nell'URL, oppure
  configurarle come variabili modificabili nella dashboard.
- Per la sicurezza (Punto 10, opzionale): creare in Grafana un utente di
  tipo "Viewer" dedicato ai medici (solo lettura), separato dalle
  credenziali admin, e proteggere l'endpoint Grafana con autenticazione
  se esposto fuori dalla rete locale.
- `SHOW_GRAFANA_TAB` in `src/config.js` mostra/nasconde la voce
  "Dashboard" nell'header di `MonitorScreen`. In assenza di un campo
  ruolo restituito dal login, è impostato a `true` per tutti; con un
  backend reale che distingue paziente/medico (Punto 4 dei requisiti) si
  può legare questo flag al ruolo dell'utente autenticato.

## 3. Notifiche push reali (`src/Notifications.js`, `src/api.js`)

Le notifiche **locali** già presenti (`sendAlertNotification`) continuano
a funzionare come prima, quando l'app è aperta e collegata via
WebSocket. Sono state aggiunte le **push reali**, che funzionano anche
con l'app in background o chiusa:

1. Aggiungere un `projectId` EAS in `app.json`, sotto `expo.extra.eas`:
   ```json
   {
     "expo": {
       "extra": {
         "eas": { "projectId": "IL-TUO-PROJECT-ID" }
       }
     }
   }
   ```
   (vedi l'esempio dell'academy in `app_con_notifica/codice_notify/app/app.json`
   per il formato). Senza questo campo, `registerExpoPushTokenOnBackend`
   registra un avviso in console e non genera alcun token: l'app
   continua a funzionare solo con le notifiche locali.
2. Configurare `PUSH_API_URL` in `src/config.js` (di default coincide
   con `API_URL`).
3. Implementare lato backend gli endpoint `/register-token` e l'invio
   delle push: vedi il modulo di esempio in
   `../push_backend_example/main.py`, da integrare nel backend reale
   Node-RED + Python del progetto.
4. In `DEMO_MODE = true` (default), la registrazione del token è
   simulata e non contatta alcun server.

## 4. Configurazione dispositivo dal medico (`src/api.js`, Punto 8 dei requisiti)

Aggiunta la funzione `sendDeviceCommand`, usata dal nuovo pulsante "⚙️"
nell'header di `MonitorScreen` per impostare la frequenza di invio della
telemetria (`publish_period_s`). Il firmware (vedi `main_real_mqtt.py` /
`main_real_ble.py`) accetta questa chiave (e anche `patient_id`, non
ancora esposta in UI) tramite un comando JSON:

- lato MQTT, sul topic `alvea/devices/<device_id>/commands`
  (`config.TOPIC_CMD` nel firmware);
- lato BLE, tramite scrittura sulla characteristic di comando
  (`BLE_CHAR_CMD_UUID`).

L'app non parla MQTT/BLE direttamente: invia una richiesta REST
`POST /devices/{deviceId}/commands` al backend, che dovrà tradurla nel
publish MQTT (o nella scrittura BLE) verso il device specifico.

Come per `SHOW_GRAFANA_TAB`, questo pulsante è oggi visibile a chiunque
sia loggato, perché il login non restituisce ancora un campo `role`
(Punto 4 dei requisiti). Quando il backend distinguerà paziente/medico,
va condizionato allo stesso modo.

## 5. Gestione degli alert del firmware (`alerts.py`)

Il firmware invia alert con `gravita` su tre livelli — `WARNING`,
`CRITICAL`, `INFO` — dove `INFO` indica che una condizione
precedentemente segnalata è rientrata (testo con suffisso
"(RISOLTO)"). La normalizzazione in `MonitorScreen.js`
(`normalizeAlert`) e la notifica locale in `Notifications.js`
(`sendAlertNotification`) preservano questo terzo livello: un alert
risolto è mostrato con etichetta "RISOLTO" e bordo verde, e non
produce una notifica push/locale con titolo "Attenzione"/"EMERGENZA".

## 6. Alert clinici client-side

L'app mostra un solo alert clinico "su soglia", coerente con quello
generato dal firmware (`alerts.py`): la **tachipnea**
(`check_resp_rate`, soglia `config.DEFAULT_ALARM_RESP_MAX = 40`,
gravità `CRITICAL`), in linea con l'uso clinico del dispositivo
(asma pediatrico). Il banner di emergenza scatta al superamento di
questa soglia.

L'app evidenzia inoltre la **batteria scarica** con un banner
dedicato, che corrisponde a un vero alert `WARNING` lato device
(`check_battery`, soglia `config.DEFAULT_ALARM_BATTERY_MIN_PCT = 15`).

Le card di Frequenza Cardiaca, Frequenza Respiratoria e Temperatura
mantengono l'intervallo "nominale" colorato (rosso/verde): è
un'indicazione visiva orientativa per il genitore, non un alert clinico
autonomo — l'unico alert autonomo via soglia resta la tachipnea.

## 7. Soglie di temperatura cutanea

Il sensore reale (`sensor_temp.py`, termistore NTC) e il simulatore
(`config.TEMP_SKIN_SIM_MIN/MAX`) misurano la temperatura **cutanea
sulla caviglia**, fisiologicamente più bassa di quella corporea
centrale: i valori nominali ricadono nell'intervallo 31.0–34.0°C. Le
soglie "nominali" della card Temperatura sono impostate su questo
intervallo (31–34.5–35.5°C), coerenti tra
`mobile/src/MonitorScreen.js` (`TEMP_MIN`/`TEMP_MAX`),
`backend/app/config.py`, il flow Node-RED e la dashboard Grafana. La
card è denominata "Temperatura Cutanea" per non indurre l'aspettativa
di una misura di febbre.

