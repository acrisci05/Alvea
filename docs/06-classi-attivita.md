# Fase 3 — Diagramma delle Classi e Diagramma di Attività

Questi due diagrammi completano la vista di progettazione (modello 4+1) del
backend Alvea, insieme al Diagramma dei Casi d'Uso (`02-use-case.md`), allo
Schema E-R (`03-er-schema.md`) e ai Diagrammi di Sequenza (`04-sequence.md`).

- Il **Diagramma delle Classi** descrive la *struttura del codice* (vista
  logica): le entità del dominio e i servizi che le elaborano.
- Il **Diagramma di Attività** descrive il *flusso* della valutazione delle
  soglie cliniche e della generazione degli alert (logica di business).

---

## 1) Diagramma delle Classi (vista logica del backend)

Le classi in alto sono le entità del dominio persistite tramite l'ORM
SQLAlchemy (`backend/app/models.py`); quelle marcate `<<service>>` sono i moduli
applicativi che le elaborano (autenticazione, valutazione degli alert, realtime).
Lo schema evidenzia la parte relativa a **sicurezza, autorizzazioni e logica
degli alert**: `Auth` (JWT + bcrypt + ruoli), `AlertEvaluator` (soglie cliniche)
e il `ConnectionManager` che applica l'isolamento dei dati sul canale realtime.

```mermaid
classDiagram
    direction LR

    class Caregiver {
        +int id
        +str username
        +str hashed_password
        +str role
    }
    class Device {
        +str device_id
        +str baby_name
        +str patient_id
        +int owner_id
    }
    class Reading {
        +datetime ts
        +float bpm
        +float respiration_rate
        +float skin_temperature
        +float battery_pct
        +bool sensor_contact
    }
    class Alert {
        +datetime ts
        +str parameter
        +str kind
        +str severity
        +str message
        +float value
    }
    class DeviceThreshold {
        +float resp_warn_low
        +float resp_crit_high
        +int bpm_crit_high
        +float temp_crit_high
        +str updated_by
    }
    class PatientRecord {
        +str full_name
        +str birth_date
        +str pathologies
        +str medications
        +str allergies
    }
    class AuditLog {
        +datetime ts
        +str username
        +str role
        +str action
        +str resource
        +str ip
    }
    class PushToken {
        +str token
        +int owner_id
        +str device_id
    }

    class Auth {
        <<service>>
        +hash_password(pw) str
        +verify_password(pw, hash) bool
        +create_access_token(data) str
        +decode_token(token) dict
    }
    class AlertEvaluator {
        <<service>>
        +evaluate(reading, thresholds) list
    }
    class ConnectionManager {
        <<service>>
        +connect(ws, scope)
        +disconnect(ws)
        +broadcast(message)
    }

    Caregiver "1" --> "0..*" Device : possiede
    Caregiver "1" --> "0..*" PushToken : registra
    Device "1" --> "0..*" Reading : genera
    Device "1" --> "0..*" Alert : produce
    Device "1" --> "0..1" DeviceThreshold : ha soglie
    Device "1" --> "0..1" PatientRecord : ha scheda

    Auth ..> Caregiver : autentica / autorizza
    AlertEvaluator ..> Reading : valuta
    AlertEvaluator ..> DeviceThreshold : usa soglie
    AlertEvaluator ..> Alert : produce
    ConnectionManager ..> Reading : inoltra (isolamento per ruolo)
```

> Nota: `AuditLog` è un registro append-only alimentato dalle operazioni
> rilevanti (login, letture, modifica soglie, scheda paziente); non ha relazioni
> di chiave esterna con le altre entità perché traccia eventi, non stato.

---

## 2) Diagramma di Attività — valutazione soglie e generazione alert

Modella il percorso di una singola lettura di telemetria dalla ricezione MQTT
fino al broadcast in tempo reale, con la **regola anti-panico**: se il sensore
non è a contatto si emette solo un alert *tecnico* e si sospende la valutazione
fisiologica, evitando falsi allarmi (`backend/app/alerts.py`,
`backend/app/mqtt_ingest.py`).

```mermaid
flowchart TD
    A([Inizio: messaggio MQTT di telemetria]) --> B[Valida payload JSON con Pydantic]
    B --> C{Payload valido?}
    C -- No --> Z1([Fine: messaggio scartato])
    C -- Sì --> D[Salva la lettura su database]
    D --> E{Sensore a contatto?}
    E -- No --> F[Genera solo alert TECNICO<br/>fascia staccata]
    E -- Sì --> G[Valuta soglia frequenza respiratoria]
    G --> H[Valuta soglia frequenza cardiaca]
    H --> I[Valuta soglia temperatura cutanea]
    F --> K[Salva gli alert generati]
    I --> K
    K --> L{Almeno un alert critico?}
    L -- Sì --> M[Invia notifica push al proprietario del device]
    L -- No --> N[Broadcast realtime ai soli client autorizzati]
    M --> N
    N --> Z([Fine])
```

> Le soglie applicate sono quelle configurate dal medico per il device
> (`DeviceThreshold`) oppure, in loro assenza, i default di
> `config.DEFAULT_THRESHOLDS`. Ogni alert riporta paziente, parametro,
> descrizione, gravità e timestamp (Gestione alert - Core).
