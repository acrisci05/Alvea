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
    participant APP as App mobile (Caregiver)

    loop Frequenza di campionamento (es. 1 Hz)
        ESP->>MQ: publish alvea/devices/{ID}/telemetry (JSON)
        par Percorso Dashboard
            MQ-->>NR: ricezione messaggio
            NR->>NR: calcolo soglie asma (Respiro, BPM, Temp)
            NR->>DB: write line protocol (measurement "vitals")
            GF->>DB: query Flux (refresh periodico)
        and Percorso App Caregiver
            MQ-->>BE: messaggio (listener MQTT)
            BE->>BE: valida payload + valuta soglie
            BE->>SQ: salva reading (+ log alert)
            BE-->>APP: WebSocket /ws/live (push)
        end
    end

    alt Anomalia hardware (device_status != SYSTEM_OK)
        ESP->>MQ: publish alvea/devices/{ID}/alerts (technical/warning/critical)
        MQ-->>BE: messaggio alert
        BE-->>APP: push alert "Sensore staccato o guasto"
    end
```

## 2) Autenticazione del caregiver (JWT)

```mermaid
sequenceDiagram
    autonumber
    participant Client as App mobile
    participant BE as Backend FastAPI
    participant SQ as DB Relazionale

    Client->>BE: POST /login (username, password)
    BE->>SQ: SELECT caregiver by username
    SQ-->>BE: record (hashed_password)
    BE->>BE: verify_password (bcrypt)
    
    alt credenziali valide
        BE->>SQ: SELECT devices WHERE owner_id = caregiver.id
        SQ-->>BE: lista device (puo' essere vuota)
        BE->>BE: create_access_token ({"sub": username})
        BE-->>Client: 200 { access_token, token_type, device_id }
        Client->>BE: GET /devices/{device_id}/latest (Bearer token)
        BE->>BE: get_current_user (decodifica JWT)
        BE-->>Client: ultima lettura del device
    else credenziali errate
        BE-->>Client: 400 Credenziali errate
    end
```

> Nota: `device_id` nella risposta di login è il primo device associato
> al caregiver (None se non ne ha ancora registrato nessuno). Non esiste
> un campo `role`: l'autenticazione odierna ha un solo tipo di account
> (Caregiver), con isolamento dei dati per `owner_id` — vedi
> `docs/03-er-schema.md`.

## 3) Configurazione da remoto del Dispositivo

```mermaid
sequenceDiagram
    autonumber
    participant App as App mobile
    participant BE as Backend FastAPI
    participant MQ as Mosquitto (MQTT)
    participant ESP as ESP32 (Firmware)

    App->>BE: POST /devices/{ID}/command { publish_period_s: 5 }
    BE->>BE: verifica che il device appartenga al caregiver autenticato
    BE->>MQ: publish alvea/devices/{ID}/commands (JSON)
    MQ-->>ESP: push su topic sottoscritto
    ESP->>ESP: mqtt_callback elabora payload
    ESP->>ESP: aggiorna current_publish_period
    ESP->>MQ: publish telemetria alla nuova frequenza (5s)
    BE-->>App: 200 { status: "ok", device_id, command }
```
