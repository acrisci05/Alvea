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
    """Singola lettura di telemetria (1 Hz)."""

    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)

    # device_id è sia chiave esterna (collega a devices.device_id)
    # sia indicizzata per velocizzare le query "dammi tutte le letture di questo device"
    device_id = Column(String, ForeignKey("devices.device_id"), index=True)

    # Timestamp di quando la lettura è stata salvata nel DB.
    # default=datetime.utcnow: se non viene fornito, usa l'ora corrente in UTC.
    ts = Column(DateTime, default=datetime.utcnow, index=True)

    # Frequenza respiratoria in atti/min. nullable=True perché può arrivare
    # None se il sensore PPG non ha ancora prodotto una stima valida.
    resp_rate = Column(Float, nullable=True)

    # Battito cardiaco in BPM
    bpm = Column(Float)

    # Temperatura cutanea in °C
    temperature = Column(Float)

    # Flag di contatto: True = fascia a contatto, False = fascia staccata
    sensor_contact = Column(Boolean)

    # Sorgente del dato: "sim" (simulatore) o "ad8232" (sensore ECG reale)
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