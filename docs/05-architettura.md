# Architettura del Sistema

## Vista d'insieme (data flow bidirezionale)

```mermaid
flowchart TD
    subgraph Edge["Edge — ESP32 (Cavigliera Alvea)"]
        S1[Sensore reale: ECG (AD8232) + NTC<br/>o Simulatore HIL]
        FW[Firmware MicroPython<br/>Asincrono]
        S1 --> FW
    end

    FW -- "MQTT (TX 1 Hz)<br/>alvea/devices/{ID}/telemetry" --> MQ[(Mosquitto)]
    MQ -- "MQTT (RX Comandi)<br/>alvea/devices/{ID}/commands" --> FW
    FW -. "BLE NOTIFY (alt., nessun consumer nell'app attuale)" .-> APP[App mobile<br/>Caregiver]

    subgraph Server["Server — Docker Compose"]
        MQ --> NR[Node-RED<br/>motore regole + alert]
        NR --> IDB[(InfluxDB)]
        IDB --> GF[Grafana<br/>dashboard]
        MQ --> BE[Backend FastAPI<br/>auth + ingest + realtime]
        BE --> SQL[(DB Relazionale)]
        BE -- "Configurazioni" --> MQ
    end

    BE -- "WebSocket / SSE" --> APP
    GF --- Browser[Browser]
```

Tre percorsi paralleli, **stesso payload**:
- **Operativo/ Clinico:** ESP32 → MQTT → Node-RED → InfluxDB → Grafana (grafici storici).
- **Applicativo/ Caregiver:** ESP32 → MQTT → Backend → DB Relazionale → WebSocket → App (live + alert).
- **Controllo (Ritorno):** Backend (input dal caregiver, es. frequenza di invio) → MQTT (commands) → ESP32 (aggiornamento configurazioni on-the-fly).
- **Alternativo:** ESP32 → BLE → eventuale ricevitore (collegamento locale; il firmware lo implementa ma l'app mobile attuale non ha alcun client BLE, comunica solo via REST/WebSocket).

## Modello 4+1 (sintesi)

- **Vista logica:** Caregiver (con campo `role`: `caregiver`/`medico`), Device, Reading, Alert, DeviceThreshold, PatientRecord, AuditLog (vedi E-R). L'RBAC Medico/Paziente è **implementato** sia a livello di dati sia di autorizzazione (campo `role`, `authorized_device()`, `require_medico`; isolamento esteso al canale realtime).
- **Vista di processo:** task asincroni sull'Edge (lettura sensori non bloccante 250Hz/50Hz) e sul Server (listener MQTT + endpoint REST/WebSocket concorrenti tramite `asyncio`).
- **Vista di sviluppo:** monorepo a moduli — `firmware/`, `backend/`,
  `docker-stack/`, `mobile/`, `scripts/`, `docs/`.
- **Vista fisica:** ESP32 (edge alla caviglia) ↔ rete Wi-Fi ↔ host Docker (Server) ↔ smartphone/PC. Architettura deployabile in cloud o on-premise.
- **Scenari (+1):** i casi d'uso del documento Fase 3 (Monitoraggio asma, gestione alert, configurazione remota).

## Porte dei servizi

| Servizio | Porta | URL locale |
|----------|-------|------------|
| MQTT (Mosquitto) | 1883 / 9001 | `mqtt://localhost:1883` |
| Node-RED | 1880 | http://localhost:1880 |
| InfluxDB | 8086 | http://localhost:8086 |
| Grafana | 3000 | http://localhost:3000 |
| Backend API | 8000 | http://localhost:8000 |
