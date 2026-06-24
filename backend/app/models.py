# models.py - Modelli ORM. Schema dati persistente di Alvea.
#
# Caregiver 1--N Device 1--N Reading
#                       Device 1--N Alert
#                       Device 1--1 DeviceThreshold   (soglie configurabili dal medico)
#                       Device 1--1 PatientRecord     (scheda paziente / anamnesi)
# AuditLog: registro append-only delle operazioni rilevanti.
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class Caregiver(Base):
    """Account utente dell'app.

    Il campo `role` implementa il controllo accessi basato sui ruoli (RBAC):
      - "caregiver" (default): genitore/operatore, lato *Paziente*; vede ed
        opera SOLO sui propri device.
      - "medico": personale sanitario; vede tutti i pazienti e configura le
        soglie cliniche.
    La tabella conserva il nome storico `caregivers` ma ospita entrambi i ruoli.
    """
    __tablename__ = "caregivers"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="caregiver", server_default="caregiver")
    devices = relationship("Device", back_populates="owner")


class Device(Base):
    """Il dispositivo indossabile (caviglia) associato a un paziente."""
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True, nullable=False)  # es. ALVEA_ASTHMA_ANKLE_01
    baby_name = Column(String, nullable=True)   # nome/etichetta del paziente
    owner_id = Column(Integer, ForeignKey("caregivers.id"))
    owner = relationship("Caregiver", back_populates="devices")
    readings = relationship("Reading", back_populates="device")
    alerts = relationship("Alert", back_populates="device")


class Reading(Base):
    """Singola lettura di telemetria (1 Hz) — parametri per l'asma pediatrico."""
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    bpm = Column(Float)                   # frequenza cardiaca (ECG)
    respiration_rate = Column(Float)      # atti respiratori al minuto (EDR da ECG)
    skin_temperature = Column(Float)      # temperatura cutanea (°C, termistore NTC)
    sensor_contact = Column(Boolean)
    device_status = Column(String, nullable=True)  # "SYSTEM_OK" | "ERR_..."
    source = Column(String, nullable=True)         # "sim-pc-script" | "production_firmware"
    device = relationship("Device", back_populates="readings")


class Alert(Base):
    """Allarme generato dalla valutazione delle soglie.

    Struttura conforme al requisito (Gestione alert - Core): l'allarme contiene
    paziente (device_id), parametro, descrizione (message), livello di gravità
    (severity) e timestamp (ts).
    """
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)  # paziente
    ts = Column(DateTime, default=datetime.utcnow, index=True)               # timestamp
    parameter = Column(String, nullable=True)  # "respiration_rate"|"bpm"|"skin_temperature"|"contact"
    kind = Column(String)          # "resp_high" | "bpm_high" | "bpm_low" | "temp_high" | ...
    severity = Column(String)      # "warning" | "critical" | "technical"
    message = Column(String)       # descrizione leggibile
    value = Column(Float, nullable=True)
    device = relationship("Device", back_populates="alerts")


class DeviceThreshold(Base):
    """Soglie cliniche configurabili per-device (impostate dal medico).

    Se per un device non esiste una riga, la valutazione usa
    config.DEFAULT_THRESHOLDS. Le modifiche sono tracciate in AuditLog.
    """
    __tablename__ = "device_thresholds"
    device_id = Column(String, ForeignKey("devices.device_id"), primary_key=True)
    resp_warn_high = Column(Float, nullable=False)
    resp_crit_high = Column(Float, nullable=False)
    bpm_warn_low = Column(Integer, nullable=False)
    bpm_warn_high = Column(Integer, nullable=False)
    bpm_crit_low = Column(Integer, nullable=False)
    bpm_crit_high = Column(Integer, nullable=False)
    skin_temp_warn_high = Column(Float, nullable=False)
    skin_temp_crit_high = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)


class PatientRecord(Base):
    """Scheda paziente e anamnesi del bambino associato al device.

    Dati anagrafici di base più le informazioni cliniche richieste dal
    requisito (patologie note, farmaci, allergie).
    """
    __tablename__ = "patient_records"
    device_id = Column(String, ForeignKey("devices.device_id"), primary_key=True)
    full_name = Column(String, nullable=True)     # nome del paziente
    birth_date = Column(String, nullable=True)    # data di nascita (ISO yyyy-mm-dd)
    sex = Column(String, nullable=True)           # "M" | "F" | "-"
    weight_kg = Column(Float, nullable=True)
    blood_type = Column(String, nullable=True)
    pathologies = Column(String, nullable=True)   # patologie note
    medications = Column(String, nullable=True)   # farmaci in uso
    allergies = Column(String, nullable=True)     # allergie
    notes = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)


class AuditLog(Base):
    """Registro append-only delle operazioni rilevanti (sicurezza e privacy).

    Traccia chi (username/role) ha fatto cosa (action) su quale risorsa
    (resource) e quando (ts): login, accesso ai dati, modifica delle soglie,
    consultazione/aggiornamento della scheda paziente.
    """
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    ts = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String, nullable=True, index=True)
    role = Column(String, nullable=True)
    action = Column(String, nullable=False)        # es. "login", "read_history"
    resource = Column(String, nullable=True)       # es. device_id interessato
    detail = Column(String, nullable=True)         # dettaglio leggibile
    ip = Column(String, nullable=True)


class PushToken(Base):
    """Expo push token registrato da un'app mobile per ricevere le notifiche.

    Associato al caregiver: gli allarmi critici di un device vengono notificati
    ai token del suo proprietario.
    """
    __tablename__ = "push_tokens"
    token = Column(String, primary_key=True)
    owner_id = Column(Integer, ForeignKey("caregivers.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
