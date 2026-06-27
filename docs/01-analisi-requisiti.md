# Fase 2 — Analisi dei Requisiti

Progetto **Alvea** — dispositivo indossabile da caviglia per il monitoraggio dell'asma pediatrico (frequenza respiratoria via EDR, battito cardiaco, temperatura cutanea), con rilevamento dell'aderenza del sensore.

> Formato `RQ-XX` come da Incontro 03. Tipo: **F** funzionale / **NF** non
> funzionale. Priorità: intero in `[0,5]` (0 = massima). Stato: **IMPL**
> implementato nel repository sorgente, **PLAN** progettato ma non ancora
> realizzato (vedi anche `docs/RELAZIONE.tex`, Sezione "Stato di
> Implementazione").

## Requisiti funzionali

| ID | Descrizione | T | Categoria | P | Stato |
|----|-------------|---|-----------|---|-------|
| RQ-01 | Acquisire battito cardiaco e stimare la frequenza respiratoria da un solo sensore ECG (AD8232), via tecnica EDR (ECG-Derived Respiration) | F | Sensing | 0 | IMPL |
| RQ-02 | Acquisire temperatura cutanea (termistore NTC analogico) | F | Sensing | 1 | IMPL |
| RQ-03 | Rilevare l'aderenza del dispositivo (pin leads-off dell'AD8232) | F | Sensing | 1 | IMPL |
| RQ-04 | Pubblicare la telemetria a 1 Hz su topic MQTT `alvea/devices/{ID}/telemetry` | F | Telemetry | 0 | IMPL |
| RQ-05 | Payload JSON: `{device_id, patient_id, timestamp, bpm, skin_temperature, respiration_rate, battery_pct, sensor_contact, device_status, source}` | F | Telemetry | 0 | IMPL |
| RQ-06 | Trasmissione BLE alternativa verso un eventuale ricevitore (NOTIFY) | F | Telemetry | 3 | IMPL (firmware); nessun consumer nell'app mobile attuale |
| RQ-07 | Ricevere comandi MQTT (es. frequenza invio, associazione paziente) per configurazione remota | F | Control | 0 | IMPL |
| RQ-08 | Valutare soglie cliniche e generare alert per asma (tachipnea) | F | Processing | 0 | IMPL |
| RQ-09 | Persistere le serie temporali cliniche su InfluxDB (via Node-RED) | F | Storage | 1 | IMPL |
| RQ-10 | Gestire le schede paziente e le logiche anagrafiche su DB relazionale | F | Storage | 2 | IMPL — entità `PatientRecord` (anagrafica + patologie/farmaci/allergie), endpoint `GET/PUT /devices/{id}/patient` |
| RQ-11 | Visualizzare metriche e alert in tempo reale su dashboard Grafana | F | Dashboard | 1 | IMPL |
| RQ-12 | Autenticazione con token JWT e isolamento dati per account (RBAC) | F | Auth | 0 | IMPL — RBAC multi-ruolo Medico/Paziente (`role`), ownership via `authorized_device`, audit log |
| RQ-13 | Monitor in tempo reale e alert sull'app mobile (WebSocket/SSE) | F | App | 1 | IMPL |
| RQ-14 | Associare un device hardware a un paziente specifico (tramite comando MQTT/BLE) | F | App | 2 | IMPL |
| RQ-15 | Segnalare stati anomali (`device_status`) sopprimendo falsi allarmi fisiologici | F | Alerting | 1 | IMPL |

## Requisiti non funzionali

| ID | Descrizione | T | Categoria | P | Stato |
|----|-------------|---|-----------|---|-------|
| RQ-16 | Esecuzione asincrona non bloccante (ECG 250 Hz, RingBuffer statico) | NF | Performance | 0 | IMPL |
| RQ-17 | Latenza end-to-end telemetria → dashboard < 2 s | NF | Performance | 1 | IMPL |
| RQ-18 | Macchina a stati per riconnessione automatica in background (Wi-Fi/MQTT) | NF | Reliability | 0 | IMPL |
| RQ-19 | Sicurezza API, hashing password e isolamento dei dati per utente (Privacy) | NF | Security | 0 | IMPL |
| RQ-20 | Credenziali Wi-Fi e token fuori dal repository (`secrets.py` e `.env`) | NF | Security | 1 | IMPL — vedi `firmware/secrets_example.py` (template) e `.gitignore` |
| RQ-21 | Stack cloud/server riproducibile con un solo comando (Docker Compose) | NF | Portability | 0 | IMPL |
| RQ-22 | Dispositivo **didattico**, non medico; alimentazione solo a bassa tensione | NF | Safety | 0 | IMPL |
| RQ-23 | Simulatore (HIL test) e hardware reale con **lo stesso schema** di payload | NF | Maintainability | 1 | IMPL |

> Ogni requisito va validato dall'Esperto Disciplinare e dal Tutor: senza
> validazione esplicita, non esiste.

## Nota sull'architettura sensoristica

L'implementazione realizzata adotta un **solo sensore biomedicale**, l'ECG
(AD8232): da esso si derivano sia il BPM sia, tramite la tecnica EDR
(ECG-Derived Respiration su Aritmia Sinusale Respiratoria), la frequenza
respiratoria, mentre la temperatura cutanea è letta da un termistore NTC
analogico separato. Il payload JSON, gli endpoint del backend e l'app
mobile sono coerenti con questa architettura.
