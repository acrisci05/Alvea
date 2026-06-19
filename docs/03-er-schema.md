# Fase 3 — Schema Entità-Relazione

Modello dati persistente del backend (vedi `backend/app/models.py`).

```mermaid
erDiagram
    USER ||--o{ PATIENT : "supervisiona (se Medico) / assiste (se Caregiver)"
    PATIENT ||--o| MEDICAL_RECORD : "possiede (Anamnesi)"
    PATIENT ||--o| DEVICE : "indossa"
    DEVICE  ||--o{ READING : "genera"
    DEVICE  ||--o{ ALERT   : "produce"

    USER {
        int    id PK
        string username "univoco"
        string hashed_password "bcrypt"
        string role "medico | paziente"
    }
    PATIENT {
        int    id PK
        string full_name
        int    caregiver_id FK "-> USER.id (opzionale)"
        int    doctor_id FK "-> USER.id"
    }
    MEDICAL_RECORD {
        int    id PK
        int    patient_id FK "-> PATIENT.id"
        string pathologies "es. Asma allergico"
        string medications "es. Salbutamolo"
        string allergies
        string clinical_notes
    }
    DEVICE {
        int    id PK
        string device_id "univoco, es. ALVEA_ASTHMA_ANKLE_01"
        int    patient_id FK "-> PATIENT.id"
        int    publish_period_s "frequenza invio (Configurabile)"
    }
    READING {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        datetime ts
        float    bpm
        float    skin_temperature
        float    spo2
        float    respiration_rate
        bool     sensor_contact
        string   device_status "es. SYSTEM_OK, ERR_PPG_NO_CONTACT"
        string   source "sim-pc-script | production_firmware"
    }
    ALERT {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        datetime ts
        string   parameter "spo2 | resp_rate | bpm | temp | hardware"
        string   severity "warning | critical | technical"
        string   description "es. Ipossia rilevata (SpO2 < 92%)"
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
