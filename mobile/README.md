# Alvea — App mobile (Expo / React Native)

App mobile caregiver + vista medico per l'ecosistema **Alvea**, coerente con
quanto descritto nella Relazione Tecnica del progetto (Gruppo 04, Academy
Medical Wearable Devices A.A. 2025/2026) e con il firmware in `firmware/`.

> Prototipo didattico. Non è un dispositivo medico certificato. Soglie e
> classificazioni hanno finalità esclusivamente accademiche.

## Sviluppo in VS Code

Il progetto include una cartella `.vscode/` pronta all'uso:

- **`extensions.json`** — estensioni consigliate (ESLint, Prettier, React
  Native Tools, Expo Tools, snippet React, Path Intellisense). VS Code
  proporrà di installarle automaticamente all'apertura della cartella.
- **`settings.json`** — format-on-save con Prettier, esclusione di
  `node_modules`/`.expo`/`dist` dalla ricerca.
- **`tasks.json`** — task `expo-start-web` e `expo-start` lanciabili da
  `Terminal → Run Task…` senza scrivere comandi a mano.
- **`launch.json`** — configurazione di debug che avvia Expo Web e apre
  Chrome agganciato al debugger di VS Code (breakpoint nel codice React).
- **`jsconfig.json`** — abilita l'alias `@/*` verso `src/*` per import più
  brevi (es. `import { colors } from '@/theme/tokens'`), oltre
  all'IntelliSense su `allowJs`/JSX.

`npm install` installa anche `eslint`, `eslint-config-expo` e `prettier`
come devDependencies, richiamati dalla configurazione sopra.

## Avvio rapido

```bash
npm install
npx expo start
```

Si apre Expo Dev Tools: scegli `w` per il web, oppure scansiona il QR code
con l'app **Expo Go** (iOS/Android) per testarla su un dispositivo fisico
sulla stessa rete Wi-Fi.

### Supporto Expo Web

Il progetto include già `react-dom`, `react-native-web` e
`@expo/metro-runtime` tra le dipendenze: sono richiesti da Expo SDK 51 per
il target web e, se assenti, causano un errore runtime generico ("Minified
React error #130") nel browser con schermata bianca o rossa. Bastano
`npm install` e poi `w` da Expo Dev Tools — non serve altro.

Se in futuro aggiungi pacchetti nativi che non hanno un equivalente web
(alcuni moduli Bluetooth/NFC, ad esempio), lo stesso tipo di errore può
ripresentarsi: prima di indagare nel codice, verifica che il pacchetto
dichiari supporto `"web"` nel suo `package.json`/`expo-module.config.json`.

## Accesso alla demo

All'avvio compare la schermata di login/registrazione.

- **Login rapido**: `caregiver@alvea.demo` / `demo1234`
- **Registrazione**: crea un account caregiver indicando nome del bambino e
  fascia d'età (Prescolare 1–5 anni / Scolare 6–12 anni, secondo la Tabella 3
  della Relazione).
- **Accesso come Medico**: link dedicato sotto al form di login, per provare
  la vista multi-paziente (lista pazienti, soglie, configurazione device,
  scheda anamnestica).

## Modalità dati: simulata vs backend reale

Per default l'app gira in **modalità simulata**: nessuna infrastruttura
richiesta. La logica di generazione telemetria e alert in
`src/services/simulator.js` replica fedelmente:

- `firmware/sensor_sim.py` — range fisiologici e scarica della batteria;
- `firmware/alerts.py` — `AlertManager.check_fault` / `check_battery`, con lo
  stesso meccanismo "5 letture consecutive prima dell'alert" e l'alert di
  risoluzione (`INFO`) quando la condizione cessa;
- principio anti-panico (Relazione, Sez. 5.4): quando `sensor_contact` è
  `false`, i parametri clinici vengono azzerati nel payload, senza generare
  falsi allarmi di distress.

Le soglie di warning/critico applicate sono quelle **effettivamente
implementate** (Relazione, Sez. 5.2), non la matrice per età "di design"
della Tabella 3 (che resta mostrata solo come riferimento informativo nella
schermata Caregiver e nella registrazione).

### Passare a un backend reale

Per collegare l'app al backend FastAPI + broker MQTT reali (stack Docker
descritto nella Relazione, Sez. 3):

1. Apri `src/config.js`.
2. Imposta `DATA_SOURCE_MODE = 'backend'`.
3. Aggiorna `BACKEND_BASE_URL` con l'indirizzo del backend sulla rete
   domestica (es. `http://192.168.1.50:8000`).

Il client REST/WebSocket è già pronto in `src/services/api.js`, con gli
endpoint della Tabella 2 della Relazione (`/register`, `/login`, `/devices`,
`/devices/{id}/latest`, `/devices/{id}/readings`, `/devices/{id}/alerts`,
`/ws/live`). `src/services/dataSource.js` smista automaticamente le chiamate
verso il simulatore o il backend in base al flag, senza che le schermate
debbano saperlo.

## Struttura del progetto

```
alvea-app/
├── App.js
├── app.json
├── package.json
├── babel.config.js
├── jsconfig.json
├── .eslintrc.js
├── .prettierrc
├── .gitignore
├── .vscode/
│   ├── settings.json
│   ├── extensions.json
│   ├── tasks.json
│   └── launch.json
└── src/
    ├── config.js                  soglie cliniche, costanti, endpoint
    ├── theme/tokens.js             palette (tema chiaro), font, design system
    ├── services/
    │   ├── simulator.js           replica sensor_sim.py + alerts.py
    │   ├── api.js                 client REST/WS per backend FastAPI reale
    │   └── dataSource.js          smista simulatore vs backend
    ├── context/
    │   ├── AuthContext.js         login/registrazione, sessione, ruoli
    │   └── TelemetryContext.js    stato pazienti/device, loop telemetria
    ├── navigation/
    │   └── RootNavigator.js       stack auth + tab caregiver / stack medico
    ├── components/
    │   ├── VitalCard.js
    │   ├── StatusPill.js
    │   ├── AlertItem.js
    │   ├── AgeBandSelector.js
    │   └── VitalsChart.js         andamento FR/BPM con bande di soglia (SVG)
    └── screens/
        ├── LoginScreen.js
        ├── RegisterScreen.js
        ├── CaregiverHomeScreen.js
        ├── AlertsScreen.js
        ├── HistoryScreen.js
        ├── MedicoPatientListScreen.js
        └── MedicoPatientDetailScreen.js
```

## Coerenza con la Relazione Tecnica

| Funzionalità app                          | Riferimento Relazione         | Stato qui |
|--------------------------------------------|--------------------------------|-----------|
| Login/registrazione caregiver              | Tabella 2 (`/register`, `/login`) | Implementato (simulato + pronto per backend reale) |
| Selezione fascia d'età alla registrazione  | Sez. 1.2, Tabella 3            | Implementato (informativo; soglie restano statiche, Sez. 5.2) |
| Telemetria realtime caregiver              | Sez. 4.1, `/ws/live`            | Implementato (simulato + pronto per WS reale) |
| Storico letture                            | `/devices/{id}/readings`       | Implementato |
| Allerte a 3 severità                       | Sez. 5.3, `alerts.py`          | Implementato |
| Vista Medico multi-paziente                | Sez. 4.1                       | Implementato |
| Configurazione device (frequenza, patient) | `commands` topic, Sez. 8 requisiti | Implementato (simulato + pronto per comando reale) |
| Scheda anamnestica                         | Sez. 4.2 (progettato)          | Implementato come mockup dimostrativo |
| RBAC Medico/Caregiver                      | Sez. 4.1                       | Implementato a livello di navigazione |

## Note tecniche

- **Tema chiaro**: la palette in `src/theme/tokens.js` usa superfici chiare
  (carta avorio `#FAF8F3`, card bianche `#FFFFFF`, testo grafite `#1A2433`),
  con la stessa logica clinica della demo originale — verde/ambra/rosso per
  gli stati, blu polvere/malva per i dati neutri nel grafico — ma toni più
  scuri e saturi dei precedenti per restare leggibili su sfondo chiaro. Le
  vecchie chiavi (`navy`, `ivory`, `textDim`, ecc.) sono mantenute come alias
  retro-compatibili che puntano ai nuovi valori, così ogni schermata eredita
  il tema chiaro senza bisogno di modifiche puntuali.
- Font: l'app è pensata per **Fraunces**, **Inter** e **IBM Plex Mono**
  (stessa identità visiva della demo web). Se non vengono caricati via
  `expo-font`/Google Fonts, l'interfaccia ricade automaticamente sul font di
  sistema senza rompersi.
- Persistenza sessione/account: `@react-native-async-storage/async-storage`.
- Grafico andamento: `react-native-svg`, bande di soglia disegnate secondo
  `THRESHOLDS.fr` in `src/config.js`.
