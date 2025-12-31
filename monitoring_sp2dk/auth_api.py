from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select

# ==============================
# JWT CONFIG
# ==============================
SECRET_KEY = "SP2DK_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ==============================
# DATABASE CONFIG (PostgreSQL)
# ==============================
DATABASE_URL = "postgresql://sp2dkuser:passwordku@localhost:5432/sp2dkdb"

# ==============================
# PASSWORD HASHER
# ==============================
# gunakan pbkdf2 (tidak error di Windows)
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI()

# ==============================
# SQLAlchemy setup
# ==============================
engine = create_engine(DATABASE_URL)
meta = MetaData()

users = Table(
    "fastapi_users",
    meta,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True),
    Column("password", String)
)

meta.create_all(engine)

# ==============================
# Utilities
# ==============================
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def hash_password(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ==============================
# REGISTER USER
# ==============================
@app.post("/register")
def register(username: str, password: str):
    with engine.connect() as conn:
        hashed_pw = hash_password(password)
        conn.execute(users.insert().values(username=username, password=hashed_pw))
        conn.commit()

    return {"message": "user created"}

# ==============================
# LOGIN USER
# ==============================
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with engine.connect() as conn:
        result = conn.execute(
            select(users).where(users.c.username == form_data.username)
        ).first()

    if not result:
        raise HTTPException(status_code=400, detail="User not found")

    if not verify_password(form_data.password, result.password):
        raise HTTPException(status_code=400, detail="Wrong password")

    token = create_access_token({"sub": result.username})

    return {"access_token": token, "token_type": "bearer"}

# ==============================
# PROFILE ENDPOINT
# ==============================
@app.get("/me")
def me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalid")

    return {"username": username}
