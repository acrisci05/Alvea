# Fase 3 — Diagrammi di Sequenza

## 1) Ingest telemetria e propagazione realtime

```mermaid
sequenceDiagram
    autonumber
    participant ESP as ESP32 (Firmware/Sim)
    participant MQ as Mosquitto (MQTT)
    participant NR as Node-RED
    participant DB as InfluxDB
    participant GF as Grafana
    participant BE as Backend FastAPI
    participant SQ as DB Relazionale
    participant APP as App mobile (Paziente)

    loop Frequenza di campionamento (es. 1 Hz)
        ESP->>MQ: publish alvea/devices/{ID}/telemetry (JSON)
        par Percorso Dashboard Medico
            MQ-->>NR: ricezione messaggio
            NR->>NR: calcolo soglie asma (SpO2, Respiro)
            NR->>DB: write line protocol (vitals_asthma)
            GF->>DB: query Flux (refresh 1s)
        and Percorso App Paziente
            MQ-->>BE: messaggio (listener MQTT)
            BE->>BE: valida payload + valuta soglie
            BE->>SQ: salva reading (+ log alert)
            BE-->>APP: WebSocket /ws/live (push)
        end
    end

    alt Anomalia hardware (device_status != SYSTEM_OK)
        NR->>MQ: publish alvea/devices/{ID}/alerts (technical)
        BE-->>APP: push alert "Sensore staccato o guasto"
    end
```

## 2) Autenticazione del caregiver (JWT)

```mermaid
sequenceDiagram
    autonumber
    participant Client as App / Dashboard
    participant BE as Backend FastAPI
    participant SQ as DB Relazionale

    Client->>BE: POST /login (username, password)
    BE->>SQ: SELECT user by username
    SQ-->>BE: record (hashed_password, role)
    BE->>BE: verify_password (bcrypt)
    
    alt credenziali valide
        BE->>BE: create_access_token (JWT con scope/role)
        BE-->>Client: 200 { access_token, role }
        Client->>BE: GET /api/data (Bearer token)
        BE->>BE: check_permissions(role)
        BE-->>Client: dati autorizzati (proprio ID per Paziente, tutti per Medico)
    else credenziali errate
        BE-->>Client: 401 Unauthorized
    end
```

## 3) Configurazione da remoto del Dispositivo

```mermaid
sequenceDiagram
    autonumber
    participant Med as Dashboard Medico
    participant BE as Backend FastAPI
    participant SQ as DB Relazionale
    participant MQ as Mosquitto (MQTT)
    participant ESP as ESP32 (Firmware)

    Med->>BE: POST /devices/{ID}/config { publish_period_s: 5 }
    BE->>BE: Verifica permessi (role == 'medico')
    BE->>SQ: Aggiorna configurazione dispositivo
    BE->>MQ: publish alvea/devices/{ID}/commands (JSON)
    MQ-->>ESP: push su topic sottoscritto
    ESP->>ESP: mqtt_callback elabora payload
    ESP->>ESP: aggiorna current_publish_period
    ESP->>MQ: publish telemetria a nuova frequenza (5s)
```
