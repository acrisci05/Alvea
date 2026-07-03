# auth.py - Hashing password (bcrypt), token JWT e ruoli (RBAC).

# datetime: per calcolare la data di scadenza del token
# timedelta: per esprimere "tra 60 minuti" in modo leggibile
from datetime import datetime, timedelta

# CryptContext è la libreria che gestisce l'hashing delle password con bcrypt.
# bcrypt è un algoritmo progettato appositamente per le password
from passlib.context import CryptContext

# Libreria per creare e decodificare token JWT (JSON Web Token).
import jwt

# Importa le costanti di configurazione da config.py:
# SECRET_KEY → chiave segreta usata per firmare i token (da tenere privata)
# ALGORITHM  → algoritmo "HS256", usato per la firma
# ACCESS_TOKEN_EXPIRE_MINUTES → durata del token in minuti (default 60)
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# --- Ruoli (RBAC, Role-Based Access Control) ------------------------------
# Il sistema distingue due ruoli:
#   - "caregiver": il genitore/operatore lato Paziente. Vede e gestisce SOLO
#                  i propri device.
#   - "medico":    il personale sanitario. Vede TUTTI i pazienti, configura le
#                  soglie cliniche e consulta l'audit log.
# Sono stringhe salvate nel campo Caregiver.role e incluse nel token
# JWT, così il backend può applicare i controlli di autorizzazione.
ROLE_CAREGIVER = "caregiver"
ROLE_MEDICO = "medico"
VALID_ROLES = {ROLE_CAREGIVER, ROLE_MEDICO}

# Crea il contesto per la gestione delle password.
# "schemes=["bcrypt"]" dice di usare bcrypt come algoritmo di hashing.
# "deprecated="auto"" fa sì che vecchi hash vengano aggiornati automaticamente.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    # Trasforma la password in chiaro, che non viene MAI salvata nel database, in un hash bcrypt
    # L'hash è diverso ogni volta anche con la stessa password (salt casuale).
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # Confronta la password inserita dall'utente al login con l'hash salvato nel DB.
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    # Crea un token JWT da restituire all'utente dopo il login.
    to_encode = data.copy()

    # Calcola il momento esatto in cui il token scadrà: l'ora attuale in UTC + 60 minuti = scadenza.
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Aggiunge il campo "exp" (expiration) al payload del token.
    # La libreria jwt lo legge automaticamente e rifiuta token scaduti.
    to_encode.update({"exp": expire})

    # Codifica e firma il token con la chiave segreta.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decodifica e verifica un token JWT, restituendo il payload.
    Solleva jwt.PyJWTError (o sottoclassi, es. ExpiredSignatureError) se il
    token è scaduto, manomesso o firmato con un'altra chiave.
    """
    
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
