# models.py - Modelli ORM. Schema dati persistente di Alvea.
#
# ORM (Object Relational Mapper) significa che ogni classe Python qui
# corrisponde a una tabella nel database. SQLAlchemy traduce automaticamente
# le operazioni sugli oggetti Python in query SQL.
#
# La struttura delle relazioni è:
# Caregiver 1 ---> N Device 1 ---> N Reading
#                            1 ---> N Alert

from datetime import datetime

# Importa i tipi di colonna disponibili in SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey

# relationship: definisce le relazioni tra tabelle (chiavi esterne a livello Python)
from sqlalchemy.orm import relationship

# Base: classe base comune da cui ereditano tutti i modelli (definita in database.py)
from .database import Base


class Caregiver(Base):
    """Genitore/operatore che usa l'app."""

    # Nome della tabella nel database
    __tablename__ = "caregivers"

    # Chiave primaria: numero intero auto-incrementale, indicizzato automaticamente
    id = Column(Integer, primary_key=True, index=True)

    # Username univoco: unique=True impedisce duplicati, index=True velocizza le ricerche
    username = Column(String, unique=True, index=True, nullable=False)

    # Password hashata con bcrypt: nullable=False significa che è obbligatoria
    hashed_password = Column(String, nullable=False)

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
    device_status, source.
    """

    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)

    # device_id è sia chiave esterna (collega a devices.device_id)
    # sia indicizzata per velocizzare le query "dammi tutte le letture di questo device"
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)

    # Paziente assegnato al device al momento della lettura (può essere None
    # se il caregiver/medico non ha ancora associato un paziente).
    patient_id = Column(String, nullable=True)

    # Timestamp di quando la lettura è stata salvata nel DB.
    # default=datetime.utcnow: se non viene fornito, usa l'ora corrente in UTC.
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    # Frequenza respiratoria in atti/min (EDR). nullable=True perché può
    # arrivare 0/None se il contatto ECG non è presente.
    respiration_rate = Column(Float, nullable=True)

    # Battito cardiaco in BPM
    bpm = Column(Float, nullable=True)

    # Temperatura cutanea in °C (nome allineato al firmware)
    skin_temperature = Column(Float, nullable=True)

    # Saturazione di ossigeno in % (SpO2)
    spo2 = Column(Float, nullable=True)

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
    """Allarme generato dalla valutazione delle soglie."""

    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    device_id = Column(String, ForeignKey("devices.device_id"), index=True)

    # Timestamp di quando l'alert è stato generato
    ts = Column(DateTime, default=datetime.utcnow, index=True)

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