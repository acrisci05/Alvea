# Fase 2 — Analisi dei Requisiti

Progetto **Alvea** — dispositivo indossabile da caviglia per il monitoraggio dell'asma pediatrico (SpO2, frequenza respiratoria, battito cardiaco e temperatura cutanea).

> Formato `RQ-XX` come da Incontro 03. Tipo: **F** funzionale / **NF** non
> funzionale. Priorità: intero in `[0,5]` (0 = massima).

## Requisiti funzionali

| ID | Descrizione | T | Categoria | P |
|----|-------------|---|-----------|---|
| RQ-01 | Acquisire SpO2 e frequenza respiratoria (Filtro IIR) da sensore PPG MAX30102 | F | Sensing | 0 |
| RQ-02 | Acquisire battito cardiaco (ECG AD8232) e temperatura cutanea (DS18B20) | F | Sensing | 1 |
| RQ-03 | Rilevare l'aderenza del dispositivo (PPG IR threshold e ECG leads-off) | F | Sensing | 1 |
| RQ-04 | Pubblicare la telemetria a 1 Hz su topic MQTT `alvea/devices/{ID}/telemetry` | F | Telemetry | 0 |
| RQ-05 | Payload JSON: `{device_id, timestamp, bpm, skin_temperature, spo2, respiration_rate, sensor_contact, device_status}` | F | Telemetry | 0 |
| RQ-06 | Trasmissione BLE alternativa verso l'app mobile (NOTIFY) | F | Telemetry | 3 |
| RQ-07 | Ricevere comandi MQTT (es. frequenza invio) per configurazione remota dal Medico | F | Control | 0 |
| RQ-08 | Valutare soglie cliniche (ipossia, tachipnea) e generare alert per asma | F | Processing | 0 |
| RQ-09 | Persistere le serie temporali cliniche su InfluxDB | F | Storage | 1 |
| RQ-10 | Gestire le schede paziente e le logiche anagrafiche su DB relazionale | F | Storage | 2 |
| RQ-11 | Visualizzare metriche e alert in tempo reale su dashboard Grafana per il Medico | F | Dashboard | 1 |
| RQ-12 | Autenticazione RBAC (Ruoli separati: Paziente vs Medico) con token JWT | F | Auth | 0 |
| RQ-13 | Monitor in tempo reale e alert sull'app mobile del Paziente (WebSocket/SSE) | F | App | 1 |
| RQ-14 | Associare univocamente un device hardware a un paziente specifico | F | App | 2 |
| RQ-15 | Segnalare stati anomali (`device_status`) sopprimendo falsi allarmi fisiologici | F | Alerting | 1 |

## Requisiti non funzionali

| ID | Descrizione | T | Categoria | P |
|----|-------------|---|-----------|---|
| RQ-16 | Esecuzione asincrona non bloccante (ECG 250 Hz, PPG 50 Hz, RingBuffer statico) | NF | Performance | 0 |
| RQ-17 | Latenza end-to-end telemetria → dashboard < 2 s | NF | Performance | 1 |
| RQ-18 | Macchina a stati per riconnessione automatica in background (Wi-Fi/MQTT) | NF | Reliability | 0 |
| RQ-19 | Sicurezza API, hashing password e isolamento dei dati per utente (Privacy) | NF | Security | 0 |
| RQ-20 | Credenziali Wi-Fi e token fuori dal repository (`secrets.py` e `.env`) | NF | Security | 1 |
| RQ-21 | Stack cloud/server riproducibile con un solo comando (Docker Compose) | NF | Portability | 0 |
| RQ-22 | Dispositivo **didattico**, non medico; alimentazione solo a bassa tensione | NF | Safety | 0 |
| RQ-23 | Simulatore (HIL test) e hardware reale con **lo stesso schema** di payload | NF | Maintainability | 1 |

> Ogni requisito va validato dall'Esperto Disciplinare e dal Tutor: senza
> validazione esplicita, non esiste.
