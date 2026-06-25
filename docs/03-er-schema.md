# Fase 3 — Schema Entità-Relazione

Modello dati persistente del backend, allineato a `backend/app/models.py`.

```mermaid
erDiagram
    CAREGIVER ||--o{ DEVICE : "registra/rivendica"
    DEVICE    ||--o{ READING : "genera"
    DEVICE    ||--o{ ALERT   : "produce"

    CAREGIVER {
        int    id PK
        string username "univoco"
        string hashed_password "bcrypt"
    }
    DEVICE {
        int    id PK
        string device_id "univoco, es. ALVEA_04"
        string baby_name "opzionale"
        int    owner_id FK "-> CAREGIVER.id (opzionale: puo' arrivare telemetria prima della registrazione)"
    }
    READING {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        string   patient_id "stringa libera, opzionale: nessuna entita' Paziente dedicata"
        datetime ts
        float    bpm
        float    skin_temperature
        float    respiration_rate "EDR, derivata dall'ECG"
        float    battery_pct "nullable se ADC guasto"
        bool     sensor_contact
        string   device_status "es. SYSTEM_OK, ERR_ECG_LEADS_OFF"
        string   source "production_firmware | sim_test_rig | sim-pc-script"
    }
    ALERT {
        int      id PK
        string   device_id FK "-> DEVICE.device_id"
        datetime ts
        string   kind "resp_high | resp_low | bpm_high | bpm_low | temp_high | temp_low | contact_lost | battery | ecg_leads_off | skin_temperature"
        string   severity "warning | critical | technical"
        string   message
        float    value "nullable per gli alert tecnici senza valore numerico singolo"
    }
```

## Note di progettazione
- **Cardinalità:** un Caregiver ha 0..N Device; un Device ha 0..N Reading e
  0..N Alert. Un Device può esistere *senza* owner (la telemetria può arrivare
  prima dell'associazione manuale: vedi `crud.ensure_device`).
- **Nessun campo SpO2:** il dispositivo ha un solo sensore biomedicale,
  l'ECG (AD8232). BPM e frequenza respiratoria (via EDR) derivano da quello;
  la temperatura cutanea da un termistore NTC analogico separato.
- **Nessuna entità Paziente/Anamnesi dedicata (PLAN):** `patient_id` è oggi
  una semplice stringa opzionale su `Reading`, non una chiave esterna verso
  una tabella `PATIENT`. Una scheda anamnestica strutturata (patologie,
  farmaci, allergie) è un'evoluzione progettata ma non implementata — vedi
  `docs/RELAZIONE.tex`, Sezione "Stato di Implementazione".
- **Nessun campo `role`:** `CAREGIVER` non distingue Medico da Paziente: è
  un unico tipo di account con isolamento dei dati per `owner_id`.
- **Serie temporali:** le `READING` ad alta frequenza vivono anche su InfluxDB
  (misura `vitals`, bucket `vitals`) per la dashboard Grafana, scritte dal
  flow Node-RED; il DB relazionale conserva lo storico per l'app e gli allarmi.
