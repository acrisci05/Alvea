# database.py - Engine e sessione asincrona SQLAlchemy.
# Questo file è il "ponte" tra il codice Python e il database.
# Si occupa di creare la connessione (engine), gestire le sessioni e fornire la classe base da cui ereditano tutti i modelli.

# Importa gli strumenti asincroni di SQLAlchemy:
# - create_async_engine: crea la connessione al DB in modalità asincrona
# - async_sessionmaker: fabbrica di sessioni asincrone
# - AsyncSession: tipo di una singola sessione asincrona
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# declarative_base: classe base da cui ereditano tutti i modelli (Caregiver, Device, ecc.)
# Tiene traccia di tutte le tabelle definite nei modelli.
from sqlalchemy.orm import declarative_base

# Importa l'URL di connessione al DB definito in config.py
from .config import DATABASE_URL

# Crea il motore di connessione al database.
# È l'oggetto principale che gestisce il pool di connessioni.
engine = create_async_engine(DATABASE_URL, echo=False)

# Crea la fabbrica di sessioni: ogni volta che serve parlare col DB, si chiede a questa fabbrica una sessione nuova.
# - bind=engine: usa il motore creato sopra
# - class_=AsyncSession: le sessioni prodotte sono asincrone
# - expire_on_commit=False: dopo un commit gli oggetti restano utilizzabili
#   senza dover fare un'altra query al DB per rileggere i dati
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Classe base per tutti i modelli ORM del progetto.
# Ogni modello (Caregiver, Device, Reading, Alert) eredita da Base, così SQLAlchemy sa quali tabelle creare nel DB.
Base = declarative_base()

async def get_db():
    # Funzione "dependency" di FastAPI: viene iniettata automaticamente
    # negli endpoint che dichiarano "db: AsyncSession = Depends(get_db)".
    # Apre una sessione, la passa all'endpoint, poi la chiude quando finisce.
    async with AsyncSessionLocal() as session:
        try:
            # "yield" invece di "return": FastAPI esegue il codice dell'endpoint
            # qui nel mezzo, poi torna qui per eseguire il finally.
            yield session
        finally:
            # La sessione viene sempre chiusa, anche se l'endpoint va in errore.
            # Questo evita connessioni al DB rimaste aperte (memory/connection leak).
            await session.close()
