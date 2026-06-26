# models.py - Modelli ORM. Schema dati persistente di Alvea.
#
# ORM (Object Relational Mapper) significa che ogni classe Python qui
# corrisponde a una tabella nel database. SQLAlchemy traduce automaticamente
# le operazioni sugli oggetti Python in query SQL.
#
# La struttura delle relazioni è:
# Caregiver 1 ---> N Device 1 ---> N Reading
#                            1 ---> N Alert
#                            1 ---> 1 DeviceThreshold  (soglie configurabili dal medico)
#                            1 ---> 1 PatientRecord    (scheda paziente / anamnesi)
# AuditLog: registro append-only delle operazioni rilevanti (sicurezza/privacy).
# PushToken: token Expo per le notifiche push verso l'app.

from datetime import datetime

# Importa i tipi di colonna disponibili in SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey

# relationship: definisce le relazioni tra tabelle (chiavi esterne a livello Python)
from sqlalchemy.orm import relationship

# Base: classe base comune da cui ereditano tutti i modelli (definita in database.py)
from .database import Base


class Caregiver(Base):
    """Account utente dell'app (genitore/operatore oppure medico).

    Il campo `role` implementa il controllo accessi basato sui ruoli (RBAC):
      - "caregiver" (default): lato Paziente, vede solo i propri device;
      - "medico": vede tutti i pazienti e configura le soglie cliniche.
    La tabella conserva il nome storico "caregivers" ma ospita entrambi i ruoli.
    """

    # Nome della tabella nel database
    __tablename__ = "caregivers"

    # Chiave primaria: numero intero auto-incrementale, indicizzato automaticamente
    id = Column(Integer, primary_key=True, index=True)

    # Username univoco: unique=True impedisce duplicati, index=True velocizza le ricerche
    username = Column(String, unique=True, index=True, nullable=False)

    # Password hashata con bcrypt: nullable=False significa che è obbligatoria
    hashed_password = Column(String, nullable=False)

    # Ruolo RBAC dell'utente ("caregiver" oppure "medico"). server_default
    # garantisce un valore anche per le righe già esistenti quando la colonna
    # viene aggiunta a un DB pre-esistente.
    role = Column(String, nullable=False, default="caregiver", server_default="caregiver")

    # Relazione verso Device: un caregiver può avere N device.
    # "back_populates" collega le due relazioni tra loro in modo bidirezionale:
    # da caregiver.devices arrivi ai device, da device.owner arrivi al caregiver.
    devices = relationship("Device", back_populates="owner")


class Device(Base):
    """La fascia indossabile associata a un bambino."""

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)

    # Identificativo univoco della cavigliera (es. "ALVEA_04").
    # Viene impostato nel firmware dell'ESP32 e non cambia mai.
    device_id = Column(String, unique=True, index=True, nullable=False)

    # Nome del bambino associato alla cavigliera (opzionale)
    baby_name = Column(String, nullable=True)

    # Chiave esterna verso caregivers.id: collega il device al suo proprietario.
    # Può essere None se il device ha inviato dati prima che il caregiver lo registrasse.
    owner_id = Column(Integer, ForeignKey("caregivers.id"))

    # Relazione verso Caregiver (lato "molti" → "uno")
    owner = relationship("Caregiver", back_populates="devices")

    # Relazione verso Reading: un device ha N letture
    readings = relationship("Reading", back_populates="device")

    # Relazione verso Alert: un device ha N alert
    alerts = relationship("Alert", back_populates="device")


class Reading(Base):
    """Singola lettura di telemetria (1 Hz).

    Campi allineati al payload reale pubblicato dal firmware su
    alvea/devices/<device_id>/telemetry (vedi main_real_mqtt.py /
    main_sim_mqtt.py / sensor_sim.py): device_id, patient_id, timestamp,
    bpm, skin_temperature, respiration_rate, battery_pct, sensor_contact,
    device_status, source. Il dispositivo non ha sensore SpO2, quindi non
    esiste un campo di saturazione.
    """

    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)

    # device_id è sia chiave esterna (collega a devices.device_id)
    # sia indicizzata per velocizzare le query "dammi tutte le letture di questo device"
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)

    # Paziente assegnato al device al momento della lettura (può essere None
    # se il caregiver/medico non ha ancora associato un paziente).
    patient_id = Column(String, nullable=True)

    # Timestamp di quando la lettura è stata acquisita (timestamp del firmware,
    # se presente; altrimenti l'ora del server). index=True per le query storiche.
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    # Frequenza respiratoria in atti/min (EDR, derivata dall'ECG). nullable=True
    # perché può arrivare 0/None se il contatto ECG non è presente.
    respiration_rate = Column(Float, nullable=True)

    # Battito cardiaco in BPM (Pan-Tompkins sull'ECG)
    bpm = Column(Float, nullable=True)

    # Temperatura cutanea in °C (termistore NTC; nome allineato al firmware)
    skin_temperature = Column(Float, nullable=True)

    # Percentuale di batteria residua. nullable=True perché può essere None
    # se l'ADC della batteria è guasto.
    battery_pct = Column(Float, nullable=True)

    # Flag di contatto: True = fascia a contatto, False = fascia staccata
    sensor_contact = Column(Boolean)

    # Stato diagnostico testuale del device (es. "SYSTEM_OK",
    # "ERR_ECG_LEADS_OFF", "WARN_NETWORK_DISCONNECTED", ecc.)
    device_status = Column(String, nullable=True)

    # Sorgente del dato: "production_firmware" oppure "sim_test_rig"
    source = Column(String, nullable=True)

    # Relazione verso Device (lato "molti" → "uno")
    device = relationship("Device", back_populates="readings")


class Alert(Base):
    """Allarme generato dalla valutazione delle soglie.

    Struttura conforme al requisito (Punto 7, gestione alert): contiene il
    paziente (device_id), il parametro interessato, la descrizione (message),
    il livello di gravità (severity) e il timestamp (ts).
    """

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(String, ForeignKey("devices.device_id"), index=True)

    # Timestamp di quando l'alert è stato generato
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    # Parametro clinico interessato: "respiration_rate" | "bpm" |
    # "skin_temperature" | "contact" (allarme tecnico fascia staccata).
    parameter = Column(String, nullable=True)

    # Tipo di anomalia rilevata:
    # "bpm_low", "bpm_high", "resp_low", "resp_high", "temp_low", "temp_high", "contact_lost"
    kind = Column(String)

    # Livello di gravità: "warning" (attenzione), "critical" (urgente), "technical" (fascia staccata)
    severity = Column(String)

    # Messaggio leggibile dall'utente (es. "Bradicardia critica: 55 BPM")
    message = Column(String)

    # Valore numerico che ha scatenato l'alert (es. 55.0 per un BPM basso).
    # nullable=True perché per gli alert tecnici (fascia staccata) non c'è un valore numerico.
    value = Column(Float, nullable=True)

    # Relazione verso Device (lato "molti" → "uno")
    device = relationship("Device", back_populates="alerts")


class DeviceThreshold(Base):
    """Soglie cliniche configurabili per-device (impostate dal medico).

    Se per un device non esiste una riga in questa tabella, la valutazione
    degli alert usa config.DEFAULT_THRESHOLDS. Ogni modifica è tracciata in
    AuditLog (vedi PUT /devices/{id}/thresholds). Una riga per device:
    device_id è chiave primaria.
    """

    __tablename__ = "device_thresholds"

    device_id = Column(String, ForeignKey("devices.device_id"), primary_key=True)

    # Frequenza respiratoria (atti/min)
    resp_warn_low  = Column(Float, nullable=False)
    resp_warn_high = Column(Float, nullable=False)
    resp_crit_low  = Column(Float, nullable=False)
    resp_crit_high = Column(Float, nullable=False)

    # Frequenza cardiaca (BPM)
    bpm_warn_low  = Column(Integer, nullable=False)
    bpm_warn_high = Column(Integer, nullable=False)
    bpm_crit_low  = Column(Integer, nullable=False)
    bpm_crit_high = Column(Integer, nullable=False)

    # Temperatura cutanea (°C)
    temp_warn_low  = Column(Float, nullable=False)
    temp_warn_high = Column(Float, nullable=False)
    temp_crit_low  = Column(Float, nullable=False)
    temp_crit_high = Column(Float, nullable=False)

    # Tracciamento dell'ultima modifica (chi e quando)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)


class PatientRecord(Base):
    """Scheda paziente e anamnesi del bambino associato al device (Punto 9).

    Dati anagrafici di base più le informazioni cliniche richieste dal
    requisito: patologie note, farmaci in uso, allergie. Una riga per device.
    """

    __tablename__ = "patient_records"

    device_id = Column(String, ForeignKey("devices.device_id"), primary_key=True)
    full_name   = Column(String, nullable=True)   # nome del paziente
    birth_date  = Column(String, nullable=True)   # data di nascita (ISO yyyy-mm-dd)
    sex         = Column(String, nullable=True)   # "M" | "F" | "-"
    weight_kg   = Column(Float,  nullable=True)
    blood_type  = Column(String, nullable=True)
    pathologies = Column(String, nullable=True)   # patologie note (es. asma allergico)
    medications = Column(String, nullable=True)   # farmaci in uso (es. salbutamolo)
    allergies   = Column(String, nullable=True)   # allergie
    notes       = Column(String, nullable=True)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by  = Column(String, nullable=True)


class AuditLog(Base):
    """Registro append-only delle operazioni rilevanti (sicurezza e privacy).

    Traccia chi (username/role) ha fatto cosa (action) su quale risorsa
    (resource) e quando (ts): login, accesso ai dati, modifica delle soglie,
    consultazione/aggiornamento della scheda paziente. Non viene mai
    aggiornato o cancellato dall'applicazione (solo inserimenti).
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String, nullable=True, index=True)
    role     = Column(String, nullable=True)
    action   = Column(String, nullable=False)   # es. "login", "read_history"
    resource = Column(String, nullable=True)    # es. device_id interessato
    detail   = Column(String, nullable=True)    # dettaglio leggibile
    ip       = Column(String, nullable=True)    # IP del client


class PushToken(Base):
    """Token Expo registrato da un'app mobile per ricevere le notifiche push.

    Associato al caregiver (owner) e al device monitorato: quando un device
    genera un alert critico, il backend invia una push ai token del suo
    proprietario (vedi push.py e mqtt_ingest.py).
    """

    __tablename__ = "push_tokens"

    token = Column(String, primary_key=True)
    owner_id = Column(Integer, ForeignKey("caregivers.id"), index=True)
    device_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
