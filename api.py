import os
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

app = FastAPI(title="Puente Universal SaaS")

# ==========================================
# CONFIGURACIÓN DE SEGURIDAD Y BASE DE DATOS
# ==========================================
SECRET_KEY = "super_secreto_para_tokens_2026_cambiar_en_produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ⚠️ AQUÍ ESTÁ EL CAMBIO: Usamos pbkdf2_sha256 en lugar de bcrypt
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

class UsuarioDB(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UsuarioRegistro(BaseModel):
    email: str
    password: str

def crear_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credenciales_exception
    except JWTError:
        raise credenciales_exception
    
    usuario = db.query(UsuarioDB).filter(UsuarioDB.email == email).first()
    if usuario is None:
        raise credenciales_exception
    return usuario

# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================
@app.post("/registro")
def registrar_usuario(user: UsuarioRegistro, db: Session = Depends(get_db)):
    usuario_existente = db.query(UsuarioDB).filter(UsuarioDB.email == user.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    
    hashed_pw = pwd_context.hash(user.password)
    nuevo_usuario = UsuarioDB(email=user.email, password_hash=hashed_pw)
    db.add(nuevo_usuario)
    db.commit()
    return {"status": "éxito", "mensaje": "Usuario registrado correctamente."}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(UsuarioDB).filter(UsuarioDB.email == form_data.username).first()
    if not usuario or not pwd_context.verify(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    
    token = crear_token(data={"sub": usuario.email})
    return {"access_token": token, "token_type": "bearer"}

# ==========================================
# RUTA PRINCIPAL
# ==========================================
@app.get("/")
def raiz():
    return FileResponse("index_puente.html")

# ==========================================
# MÓDULOS PROTEGIDOS
# ==========================================
@app.post("/excel/leer")
async def leer_excel(
    archivo: UploadFile = File(...), 
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        df = pd.read_excel(archivo.file)
        return {"status": "éxito", "total_filas": len(df), "primeras_10": df.head(10).to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PeticionSQL(BaseModel):
    consulta: str

@app.post("/db/consultar")
def consultar_db(
    peticion: PeticionSQL,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    if not peticion.consulta.strip().upper().startswith("SELECT"):
        raise HTTPException(status_code=403, detail="Solo se permiten consultas SELECT.")
    try:
        conn = sqlite3.connect("empresa.db")
        cursor = conn.cursor()
        cursor.execute(peticion.consulta)
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        conn.close()
        return {"status": "éxito", "resultados": [dict(zip(columnas, f)) for f in filas]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PeticionScraping(BaseModel):
    url: str

@app.post("/web/scraping")
def espiar_precio(
    peticion: PeticionScraping,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        respuesta = requests.get(peticion.url, headers=headers, timeout=10)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        titulo = soup.title.string if soup.title else "Sin título"
        return {"status": "éxito", "titulo_extraido": titulo.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)