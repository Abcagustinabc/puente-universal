import os
import sqlite3
import pandas as pd
import requests
import random
import math
import numpy as np
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

app = FastAPI(title="Puente Universal Enterprise")

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
SECRET_KEY = "super_secreto_2026_enterprise"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
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

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        usuario = db.query(UsuarioDB).filter(UsuarioDB.email == email).first()
        if usuario is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return usuario
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

class UsuarioRegistro(BaseModel):
    email: str
    password: str

@app.post("/registro")
def registrar_usuario(user: UsuarioRegistro, db: Session = Depends(get_db)):
    if db.query(UsuarioDB).filter(UsuarioDB.email == user.email).first():
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")
    nuevo_usuario = UsuarioDB(email=user.email, password_hash=pwd_context.hash(user.password))
    db.add(nuevo_usuario)
    db.commit()
    return {"status": "éxito", "mensaje": "Usuario registrado correctamente."}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    usuario = db.query(UsuarioDB).filter(UsuarioDB.email == form_data.username).first()
    if not usuario or not pwd_context.verify(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode({"sub": usuario.email, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.get("/")
def raiz():
    return FileResponse("index_puente.html")

# ==========================================
# A. EXCEL NIVEL EMPRESA (Análisis completo)
# ==========================================
@app.post("/excel/analizar")
async def analizar_excel(
    archivo: UploadFile = File(...), 
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        df = pd.read_excel(archivo.file)
        
        # Análisis profundo
        filas_totales = len(df)
        columnas = list(df.columns)
        
        # Resumen de columnas numéricas
        resumen = {}
        for col in df.select_dtypes(include=['number']).columns:
            resumen[col] = {
                "suma": float(df[col].sum()),
                "promedio": float(df[col].mean()),
                "maximo": float(df[col].max()),
                "minimo": float(df[col].min())
            }
            
        # Muestra de las primeras 5 filas (para que el usuario vea la data)
        muestra = df.head(5).to_dict(orient="records")
        
        return {
            "status": "éxito", 
            "archivo": archivo.filename,
            "total_filas": filas_totales,
            "columnas_detectadas": columnas,
            "resumen_estadistico": resumen,
            "muestra_datos": muestra
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando Excel: {str(e)}")

# ==========================================
# B. SCRAPING NIVEL EMPRESA (Extraer Enlaces)
# ==========================================
class PeticionScraping(BaseModel):
    url: str

@app.post("/web/scraping")
def espiar_web(
    peticion: PeticionScraping,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        respuesta = requests.get(peticion.url, headers=headers, timeout=10)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        
        # Extraer todos los enlaces (a href)
        enlaces = []
        for a in soup.find_all('a', href=True):
            texto = a.text.strip()
            if texto: # Solo si tiene texto visible
                enlaces.append({"texto": texto, "url": a['href']})
            if len(enlaces) >= 20: # Limitamos a 20 para no saturar
                break
                
        titulo = soup.title.string if soup.title else "Sin título"
        
        return {
            "status": "éxito", 
            "titulo_pagina": titulo.strip(), 
            "total_enlaces_encontrados": len(enlaces),
            "primeros_20_enlaces": enlaces
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en scraping: {str(e)}")

# ==========================================
# C. IA NIVEL EMPRESA (Red Neuronal 3 Variables)
# ==========================================
class RedNeuronal:
    def __init__(self, entradas=3, ocultas=4, salidas=1):
        # Inicializamos matrices con numpy
        self.w1 = np.random.randn(entradas, ocultas) * 0.1
        self.b1 = np.zeros((1, ocultas))
        self.w2 = np.random.randn(ocultas, salidas) * 0.1
        self.b2 = np.zeros((1, salidas))

    def sigmoide(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def derivada_sigmoide(self, x):
        return x * (1 - x)

    def predecir(self, X):
        capa_oculta = self.sigmoide(np.dot(X, self.w1) + self.b1)
        salida = self.sigmoide(np.dot(capa_oculta, self.w2) + self.b2)
        return salida, capa_oculta

    def entrenar(self, X, y, epocas=2000, lr=0.1):
        for _ in range(epocas):
            # Forward
            capa_oculta = self.sigmoide(np.dot(X, self.w1) + self.b1)
            salida = self.sigmoide(np.dot(capa_oculta, self.w2) + self.b2)
            
            # Error
            error_salida = y - salida
            delta_salida = error_salida * self.derivada_sigmoide(salida)
            
            error_oculto = np.dot(delta_salida, self.w2.T)
            delta_oculto = error_oculto * self.derivada_sigmoide(capa_oculta)
            
            # Actualizar
            self.w2 += np.dot(capa_oculta.T, delta_salida) * lr
            self.b2 += np.sum(delta_salida, axis=0, keepdims=True) * lr
            self.w1 += np.dot(X.T, delta_oculto) * lr
            self.b1 += np.sum(delta_oculto, axis=0, keepdims=True) * lr

# Entrenar con 3 variables: [Ingresos, Deuda, Antigüedad Laboral]
red_ia = RedNeuronal(entradas=3, ocultas=4, salidas=1)
X_train = np.array([[0.9, 0.1, 0.9], [0.8, 0.2, 0.7], [0.2, 0.8, 0.2], [0.1, 0.9, 0.1], [0.6, 0.4, 0.5], [0.3, 0.7, 0.3]])
y_train = np.array([[1], [1], [0], [0], [1], [0]])
red_ia.entrenar(X_train, y_train)

class PeticionPrediccion(BaseModel):
    ingresos: float
    deuda: float
    antiguedad: float

@app.post("/ia/predecir")
def predecir_riesgo(
    peticion: PeticionPrediccion,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        X = np.array([[peticion.ingresos, peticion.deuda, peticion.antiguedad]])
        prediccion, _ = red_ia.predecir(X)
        prob = float(prediccion[0][0])
        
        if prob > 0.7: decision = "APROBADO (Riesgo Bajo)"
        elif prob < 0.3: decision = "RECHAZADO (Riesgo Alto)"
        else: decision = "REVISIÓN (Riesgo Medio)"
            
        return {
            "status": "éxito", 
            "decision": decision,
            "probabilidad": round(prob, 4),
            "mensaje": f"La IA calculó un riesgo del {prob*100:.1f}% con 3 variables."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)