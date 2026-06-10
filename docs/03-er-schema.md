# Fase 3 — Schema Entità-Relazione

Modello dati persistente del backend (vedi `backend/app/models.py`).

```mermaid
erDiagram
    CAREGIVER ||--o{ DEVICE : possiede
    DEVICE   ||--o{ READING : genera
    DEVICE   ||--o{ ALERT   : produce

    CAREGIVER {
        int    id PK
        string username "univoco"
        string hashed_password "bcrypt"
    }
    DEVICE {
        int    id PK
        string device_id "univoco, es. PULSEGUARD_BABY_04"
        string baby_name
        int    owner_id FK "-> CAREGIVER.id"
    }
    READING {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        datetime ts
        float    bpm
        float    temperature
        bool     sensor_contact
        string   source "sim | ad8232"
    }
    ALERT {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        datetime ts
        string   kind "bpm_high | temp_low | contact_lost | ..."
        string   severity "warning | critical | technical"
        string   message
        float    value
    }
```

## Note di progettazione
- **Cardinalità:** un Caregiver ha 0..N Device; un Device ha 0..N Reading e
  0..N Alert. Un Device può esistere *senza* owner (la telemetria può arrivare
  prima dell'associazione manuale: vedi `crud.ensure_device`).
- **Serie temporali:** le `READING` ad alta frequenza vivono anche su InfluxDB
  (misura `vitals`) per la dashboard Grafana; il DB relazionale conserva lo
  storico per l'app e gli allarmi.
