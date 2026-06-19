# Fase 2 — Analisi dei Requisiti

Progetto **Alvea** — fascia indossabile per il monitoraggio del
battito cardiaco e della temperatura di un neonato.

> Formato `RQ-XX` come da Incontro 03. Tipo: **F** funzionale / **NF** non
> funzionale. Priorità: intero in `[0,5]` (0 = massima).

## Requisiti funzionali

| ID | Descrizione | T | Categoria | P |
|----|-------------|---|-----------|---|
| RQ-01 | Acquisire il battito (BPM) da sensore ECG AD8232 | F | Sensing | 0 |
| RQ-02 | Acquisire la temperatura corporea | F | Sensing | 1 |
| RQ-03 | Rilevare l'aderenza della fascia (leads-off) | F | Sensing | 1 |
| RQ-04 | Pubblicare la telemetria a 1 Hz su MQTT `alvea/data` | F | Telemetry | 0 |
| RQ-05 | Payload JSON `{device_id, timestamp, bpm, temperature, sensor_contact}` | F | Telemetry | 0 |
| RQ-06 | Trasmissione BLE alternativa verso l'app mobile | F | Telemetry | 3 |
| RQ-07 | Valutare soglie cliniche e generare allarmi (warning/critical) | F | Processing | 0 |
| RQ-08 | Sopprimere gli allarmi fisiologici a fascia staccata (debounce) | F | Processing | 1 |
| RQ-09 | Persistere le serie temporali su InfluxDB | F | Storage | 1 |
| RQ-10 | Persistere letture e allarmi su DB relazionale (backend) | F | Storage | 2 |
| RQ-11 | Visualizzare BPM/temperatura in tempo reale su Grafana | F | Dashboard | 1 |
| RQ-12 | Registrazione e login del caregiver con token JWT | F | Auth | 1 |
| RQ-13 | Monitor in tempo reale sull'app mobile (WebSocket) | F | App | 1 |
| RQ-14 | Associare un device a un caregiver | F | App | 2 |
| RQ-15 | Ripubblicare gli allarmi su `alvea/alerts` | F | Alerting | 3 |

## Requisiti non funzionali

| ID | Descrizione | T | Categoria | P |
|----|-------------|---|-----------|---|
| RQ-16 | Campionamento ECG a 250 Hz uniforme (busy-wait) | NF | Performance | 0 |
| RQ-17 | Latenza end-to-end telemetria → dashboard < 2 s | NF | Performance | 1 |
| RQ-18 | Riconnessione automatica Wi-Fi e MQTT | NF | Reliability | 1 |
| RQ-19 | Hashing password (bcrypt) e JWT con scadenza | NF | Security | 0 |
| RQ-20 | Credenziali Wi-Fi fuori dal repository (`secrets.py`) | NF | Security | 1 |
| RQ-21 | Stack riproducibile con un solo comando (Docker Compose) | NF | Portability | 0 |
| RQ-22 | Dispositivo **didattico**, non medico; alimentazione solo USB/powerbank | NF | Safety | 0 |
| RQ-23 | Simulatore e sensore reale con **lo stesso schema** di payload | NF | Maintainability | 2 |

> Ogni requisito va validato dall'Esperto Disciplinare e dal Tutor: senza
> validazione esplicita, non esiste.
