# auth.py - Hashing password (bcrypt) e token JWT (pattern del corso).
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt

from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# --- Ruoli applicativi (RBAC) --------------------------------------------
#   caregiver -> genitore/operatore: lato "Paziente", vede solo i propri device
#   medico    -> personale sanitario: vede tutti i pazienti e configura le soglie
ROLE_CAREGIVER = "caregiver"
ROLE_MEDICO = "medico"
VALID_ROLES = {ROLE_CAREGIVER, ROLE_MEDICO}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
