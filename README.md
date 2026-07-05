<div align="center">

# 🫁 Alvea

### Wearable da caviglia per il monitoraggio dell'asma pediatrico

Acquisizione continua di **frequenza respiratoria** (EDR da ECG), **battito cardiaco**,
**temperatura cutanea** (termistore NTC) e **livello di batteria**, con rilevamento
dell'aderenza degli elettrodi, alert clinici in tempo reale, app mobile per il paziente
e dashboard per il medico.

![Status](https://img.shields.io/badge/status-didattico-blue)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-realtime-009688?logo=fastapi&logoColor=white)
![React Native](https://img.shields.io/badge/React%20Native-Expo%20SDK%2054-61DAFB?logo=expo&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-660066?logo=eclipsemosquitto&logoColor=white)
![InfluxDB](https://img.shields.io/badge/InfluxDB-timeseries-22ADF6?logo=influxdb&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-dashboard-F46800?logo=grafana&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

> [!WARNING]
> **Dispositivo didattico, non medico.** Realizzato per *Academy Medical Wearable
> Devices*. Non utilizzare per decisioni sanitarie reali. Vedi [`docs/SICUREZZA.md`](docs/SICUREZZA.md).

---

## ✨ In breve

L'**ESP32** acquisisce i parametri da un **ECG (AD8232)** — dal quale ricava sia il
**battito** (algoritmo Pan-Tompkins) sia il **respiro** tramite **EDR** (*ECG-Derived
Respiration*, filtro IIR sugli intervalli RR) — da un **termistore NTC** per la
temperatura cutanea e da un **partitore resistivo** per la batteria (*oppure* da un
simulatore HIL), e li invia **a 1 Hz**. Il canale è **bidirezionale**: il dispositivo
riceve dal backend la configurazione del medico (es. frequenza di campionamento,
associazione paziente). Simulatore e hardware reale condividono **lo stesso payload
JSON**, così passare dall'uno all'altro non cambia nulla a valle.

| | |
|---|---|
| 🔴 **Alert clinici** | Tachipnea/bradipnea (respiro), tachicardia/bradicardia (BPM), febbre/ipotermia (temp. cutanea) |
| 👤 **Ruoli (RBAC)** | Paziente/Caregiver (vede solo i propri dati) · Medico (vede tutti, configura le soglie, consulta l'audit) |
| 📈 **Serie temporali** | InfluxDB + Grafana: ultimo valore, andamento, medie/min/max |
| 📱 **App mobile** | Real-time via WebSocket, storico, statistiche, **notifiche** push/locali |
| 🔐 **Sicurezza** | JWT + bcrypt, isolamento dei dati per ruolo, **audit log** delle operazioni |

## 🗺️ Architettura

```mermaid
flowchart LR
    FW["ESP32<br/>sim o reale"] -- "MQTT alvea/devices/{ID}/telemetry" --> MQ[(Mosquitto)]
    MQ -- "alvea/devices/{ID}/commands" --> FW
    FW -. "BLE (alternativo, test locale)" .-> APP[App mobile]
    MQ --> NR[Node-RED] --> IDB[(InfluxDB)] --> GF[Grafana · Medico]
    MQ --> BE[Backend FastAPI] --> SQL[(SQLite)]
    BE -- "WebSocket / SSE / REST" --> APP[App mobile · Paziente]
```

### 🔬 Pipeline di acquisizione (sensori → metriche)

```mermaid
flowchart LR
    ECG["ECG AD8232<br/>250 Hz · GPIO34"] --> PT["Pan-Tompkins<br/>(Ring Buffer statico)"] --> RR(["Intervalli RR"])
    RR --> BPM([BPM])
    RR --> EDR["EDR · IIR passa-basso<br/>(Aritmia Sinusale Respiratoria)"] --> FR([Freq. respiratoria])
    NTC["Termistore NTC<br/>ADC · GPIO35"] --> LIN["Linearizzazione"] --> T([Temp. cutanea])
    BAT["Partitore resistivo<br/>ADC · GPIO36"] --> PCT([Batteria %])
    BPM --> PAY["Payload JSON · 1 Hz"]
    FR --> PAY
    T --> PAY
    PCT --> PAY
```

### 🔁 Flusso telemetria e alert

```mermaid
sequenceDiagram
    participant FW as ESP32
    participant MQ as Mosquitto
    participant BE as Backend FastAPI
    participant APP as App (Paziente)
    FW->>MQ: telemetry (1 Hz)
    MQ->>BE: ingest
    BE->>BE: salva lettura + valuta soglie (per-device)
    BE-->>APP: WebSocket (reading + alert)
    BE-->>APP: push notification (alert critico)
```

## 📦 Payload canonico

```json
{
  "device_id": "ALVEA_04",
  "patient_id": "p_0007",
  "timestamp": 1733740000.0,
  "bpm": 95.0,
  "skin_temperature": 32.5,
  "respiration_rate": 22.0,
  "battery_pct": 84.5,
  "sensor_contact": true,
  "device_status": "SYSTEM_OK",
  "source": "production_firmware"
}
```

## 🩺 Scenari clinici (simulatore)

| Scenario | Effetto | Alert atteso |
|---|---|---|
| `nominal` | Bambino a riposo | nessuno |
| `asthma_attack` | respiro ↑ (tachipnea), battito ↑ | **critico** tachipnea + tachicardia |
| `hardware_fault` | Sensore staccato | **tecnico** (nessun falso positivo) |

## ✅ Conformità ai requisiti (Academy Medical Wearable Devices)

| # | Requisito | Stato | Dove |
|---|---|:--:|---|
| 1 | Acquisizione dati dal wearable (MQTT) | ✅ | `firmware/`, `scripts/publish_test.py` |
| 2 | Backend real-time + soglie configurabili | ✅ | `backend/` (REST, WebSocket, SSE) |
| 3 | App mobile (real-time, storico, notifiche) | ✅ | `mobile/` |
| 4 | Ruoli e permessi (Paziente / Medico) | ✅ | `backend/app/auth.py`, `main.py` |
| 5 | Database serie temporali | ✅ | InfluxDB + Grafana |
| 6 | Dashboard medico Grafana | ✅ | `docker-stack/grafana/` |
| 7 | Gestione alert (paziente, parametro, gravità…) | ✅ | `backend/app/alerts.py` |
| 8 | Configurazione del medico (soglie, paziente-device) | ✅ | `PUT /devices/{id}/thresholds`, `/commands` |
| 9 | Scheda paziente / anamnesi | ✅ | `GET/PUT /devices/{id}/patient` |
| 10 | Sicurezza, privacy e tracciamento (audit) | ✅ | JWT, RBAC, `AuditLog` |
| 11 | Documentazione architettura e API | ✅ | `docs/` |

## 🚀 Avvio rapido (stack server)

Richiede **Docker** e **Docker Compose**.

```bash
cd docker-stack
cp .env.example .env        # opzionale: già pronto per uso locale
docker compose up -d
```

| Servizio | URL | Credenziali |
|---|---|---|
| 📊 Grafana (dashboard medico) | http://localhost:3000 | `admin` / `admin` |
| 🔧 Node-RED (motore regole) | http://localhost:1880 | — |
| 🗄️ InfluxDB (serie temporali) | http://localhost:8086 | `admin` / `alvea123` |
| ⚡ Backend API (Swagger) | http://localhost:8000/docs | — |
| 📡 MQTT Broker | `localhost:1883` | anonimo |

> Dashboard Grafana e flow Node-RED sono **provisionati automaticamente**.

## 🧪 Prova senza hardware

```bash
pip install paho-mqtt
python scripts/publish_test.py --host localhost                       # dati nominali
python scripts/publish_test.py --host localhost --scenario asthma_attack   # allarme asma
python scripts/publish_test.py --host localhost --scenario hardware_fault  # sensore staccato
```

I grafici storici e gli alert si popolano in tempo reale su Grafana e sull'app.

## 🔌 Firmware ESP32 (MicroPython)

1. Copia `firmware/secrets_example.py` in `firmware/secrets.py` e inserisci SSID/password Wi-Fi.
2. In `firmware/config.py` imposta `MQTT_BROKER` con l'IP del PC che ospita lo stack.
3. Copia su scheda i file di `firmware/` e rinomina l'entrypoint scelto in `main.py`:

| Scenario | Entrypoint |
|---|---|
| Simulatore Test-Rig via MQTT | `main_sim_mqtt.py` |
| Hardware reale via MQTT (prod) | `main_real_mqtt.py` |
| Simulatore Test-Rig via BLE | `main_sim_ble.py` |
| Hardware reale via BLE | `main_real_ble.py` |

**Cablaggio sensori reali:** ECG (AD8232) `OUTPUT→GPIO34, LO+→GPIO32, LO-→GPIO33` ·
termistore NTC `partitore→GPIO35 (ADC)` · batteria `partitore→GPIO36 (ADC)`.

> Il **BPM** è calcolato con **Pan-Tompkins** sull'ECG; la **frequenza respiratoria**
> è ricavata dagli *stessi* intervalli RR via **EDR** (filtro IIR sull'Aritmia Sinusale
> Respiratoria). La **temperatura** usa il termistore **NTC** linearizzato. Il BLE è una
> modalità di test locale alternativa al Wi-Fi/MQTT.

## 📱 App mobile (React Native / Expo)

```bash
cd mobile && npm install && npx expo start
```

Imposta `API_URL` in `mobile/src/config.js` con l'IP del PC. Con backend reale
(`DEMO_MODE = false`) registra prima il device del caregiver (`POST /devices`) e poi
effettua il login. Dettagli e notifiche: vedi [`mobile/README.md`](mobile/README.md).

## 📁 Struttura del repository

```text
Alvea/
├── firmware/        # MicroPython ESP32: Pan-Tompkins ECG, EDR respiro, NTC, batteria, MQTT async
├── backend/         # FastAPI: RBAC (Medico/Paziente), REST, WebSocket/SSE, soglie, alert, audit, push
├── docker-stack/    # Mosquitto + Node-RED + InfluxDB + Grafana + backend
├── mobile/          # App React Native / Expo (real-time, notifiche, storico)
├── scripts/         # publish_test.py: simulatore HIL della periferica
└── docs/            # Requisiti, use case, E-R, sequence, architettura, sicurezza
```

## 📚 Documentazione

- [Relazione tecnica (PDF)](docs/RELAZIONE.pdf)
- [Analisi dei requisiti](docs/01-analisi-requisiti.md) · [Casi d'uso](docs/02-use-case.md) · [Schema E-R](docs/03-er-schema.md)
- [Diagrammi di sequenza](docs/04-sequence.md) · [Classi e attività](docs/06-classi-attivita.md) · [Architettura e API](docs/05-architettura.md) · [Sicurezza](docs/SICUREZZA.md)
- [Immagini UML per il report](docs/diagrammi/) — PNG pronti da inserire

## 📄 Licenza

Distribuito con licenza **MIT** (vedi [`LICENSE`](LICENSE)). Progetto didattico accademico.
