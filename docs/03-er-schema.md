# Fase 3 — Schema Entità-Relazione

Modello dati persistente del backend, allineato a `backend/app/models.py`.

```mermaid
erDiagram
    CAREGIVER ||--o{ DEVICE : "registra/rivendica"
    CAREGIVER ||--o{ PUSH_TOKEN : "registra"
    DEVICE    ||--o{ READING : "genera"
    DEVICE    ||--o{ ALERT   : "produce"
    DEVICE    ||--o| DEVICE_THRESHOLD : "ha soglie (config. medico)"
    DEVICE    ||--o| PATIENT_RECORD : "ha scheda paziente"

    CAREGIVER {
        int    id PK
        string username "univoco"
        string hashed_password "bcrypt"
        string role "caregiver | medico (RBAC)"
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
        string   patient_id "stringa libera, opzionale"
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
        string   parameter "respiration_rate | bpm | skin_temperature | contact"
        string   kind "resp_high | resp_low | bpm_high | bpm_low | temp_high | temp_low | contact_lost | battery"
        string   severity "warning | critical | technical"
        string   message
        float    value "nullable per gli alert tecnici senza valore numerico singolo"
    }
    DEVICE_THRESHOLD {
        string device_id PK "-> DEVICE.device_id"
        float  resp_warn_low
        float  resp_warn_high
        float  resp_crit_low
        float  resp_crit_high
        int    bpm_warn_low
        int    bpm_warn_high
        int    bpm_crit_low
        int    bpm_crit_high
        float  temp_warn_low
        float  temp_warn_high
        float  temp_crit_low
        float  temp_crit_high
        string updated_by "medico che ha modificato"
    }
    PATIENT_RECORD {
        string device_id PK "-> DEVICE.device_id"
        string full_name
        string birth_date
        string sex
        float  weight_kg
        string blood_type
        string pathologies "patologie note (es. asma allergico)"
        string medications "farmaci in uso (es. salbutamolo)"
        string allergies
        string notes
    }
    AUDIT_LOG {
        int      id PK
        datetime ts
        string   username
        string   role
        string   action "login | read_history | update_thresholds | ..."
        string   resource "device_id interessato"
        string   detail
        string   ip
    }
    PUSH_TOKEN {
        string token PK "Expo push token"
        int    owner_id FK "-> CAREGIVER.id"
        string device_id "device monitorato"
    }
```

## Note di progettazione
- **Cardinalità:** un Caregiver ha 0..N Device; un Device ha 0..N Reading,
  0..N Alert, 0..1 DeviceThreshold e 0..1 PatientRecord. Un Device può esistere
  *senza* owner (la telemetria può arrivare prima dell'associazione manuale:
  vedi `crud.ensure_device`).
- **Sensoristica:** il dispositivo ha un solo sensore biomedicale,
  l'ECG (AD8232). BPM e frequenza respiratoria (via EDR) derivano da quello;
  la temperatura cutanea da un termistore NTC analogico separato.
- **Ruoli (RBAC):** il campo `CAREGIVER.role` distingue `caregiver` (lato
  Paziente, vede solo i propri device) e `medico` (vede tutti, configura le
  soglie, consulta l'audit log). Il controllo di proprietà è centralizzato in
  `authorized_device()` (vedi `backend/app/main.py`).
- **Soglie configurabili:** `DEVICE_THRESHOLD` conserva le soglie cliniche
  per-device impostate dal medico; in sua assenza si usano i default di
  `config.DEFAULT_THRESHOLDS`.
- **Scheda paziente:** `PATIENT_RECORD` contiene anagrafica e anamnesi
  (patologie, farmaci, allergie) del bambino associato al device.
- **Audit log:** `AUDIT_LOG` è un registro append-only delle operazioni
  rilevanti (sicurezza/privacy), consultabile dal solo medico.
- **Serie temporali:** le `READING` ad alta frequenza vivono anche su InfluxDB
  (misura `vitals`, bucket `vitals`) per la dashboard Grafana, scritte dal
  flow Node-RED; il DB relazionale conserva lo storico per l'app e gli allarmi.
