import os
import sqlite3
import pandas as pd
import requests
import random
import math
import numpy as np
import re
import nltk
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

# Descargar recursos de NLTK (Procesamiento de Lenguaje Natural clásico)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

app = FastAPI(title="Puente Universal - Agente Autónomo")

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
# A. EXCEL NIVEL DIOS (Análisis Predictivo y NLP)
# ==========================================
@app.post("/excel/analizar")
async def analizar_excel_pro(
    archivo: UploadFile = File(...), 
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        df = pd.read_excel(archivo.file)
        
        # 1. Perfilado de datos (Data Profiling)
        perfil = {
            "total_filas": len(df),
            "total_columnas": len(df.columns),
            "valores_nulos": int(df.isnull().sum().sum()),
            "tipos_datos": {col: str(dtype) for col, dtype in df.dtypes.items()}
        }
        
        # 2. Correlaciones (Qué columnas afectan a otras)
        correlaciones = {}
        num_df = df.select_dtypes(include=['number'])
        if len(num_df.columns) > 1:
            corr_matrix = num_df.corr().round(2).to_dict()
            correlaciones = corr_matrix

        # 3. Detección de Anomalías (Outliers usando Z-Score)
        anomalias = {}
        for col in num_df.columns:
            media = num_df[col].mean()
            std = num_df[col].std()
            if std > 0:
                outliers = df[np.abs((num_df[col] - media) / std) > 3]
                if not outliers.empty:
                    anomalias[col] = len(outliers)
                    
        return {
            "status": "éxito", 
            "perfil": perfil,
            "correlaciones": correlaciones,
            "anomalias_detectadas": anomalias,
            "mensaje": "Análisis avanzado completado con éxito."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ==========================================
# B. SCRAPING NIVEL DIOS (Agente Rastreador Universal)
# ==========================================
class PeticionAgente(BaseModel):
    url: str
    objetivo: str # Ej: "precios", "fechas", "nombres"

@app.post("/web/agente")
def agente_rastreador(
    peticion: PeticionAgente,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        respuesta = requests.get(peticion.url, headers=headers, timeout=15)
        soup = BeautifulSoup(respuesta.text, 'lxml')
        
        # 1. Limpieza profunda (Eliminar scripts, estilos, menús de navegación)
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        texto_limpio = soup.get_text(separator=' ')
        
        # 2. Extracción Inteligente basada en el objetivo
        resultado_extraido = []
        
        if peticion.objetivo.lower() == "precios":
            # Busca patrones como $100, 100 USD, 100€
            patron = r'(\$|€|USD|MXN|EUR)\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)'
            coincidencias = re.findall(patron, texto_limpio)
            for simbolo, numero in coincidencias[:20]: # Top 20
                resultado_extraido.append(f"{simbolo}{numero}")
                
        elif peticion.objetivo.lower() == "fechas":
            # Busca fechas en formatos comunes
            patron = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'
            coincidencias = re.findall(patron, texto_limpio)
            resultado_extraido = list(set(coincidencias))[:20]
            
        elif peticion.objetivo.lower() == "enlaces":
            for a in soup.find_all('a', href=True):
                resultado_extraido.append({"texto": a.text.strip(), "url": a['href']})
                if len(resultado_extraido) >= 20: break
                
        else:
            # Búsqueda por palabra clave en el texto
            palabras = nltk.word_tokenize(texto_limpio.lower())
            contexto = [w for w in palabras if peticion.objetivo.lower() in w]
            resultado_extraido = list(set(contexto))[:20]

        return {
            "status": "éxito", 
            "url_analizada": peticion.url,
            "objetivo": peticion.objetivo,
            "resultados_encontrados": resultado_extraido,
            "mensaje": f"Se analizaron {len(texto_limpio)} caracteres de la página."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el agente: {str(e)}")

# ==========================================
# C. IA NIVEL DIOS (Red Neuronal con Múltiples Capas y Regresión)
# ==========================================
class RedNeuronalProfunda:
    def __init__(self, capas):
        # Inicialización de pesos para múltiples capas (Deep Learning puro)
        self.pesos = []
        self.sesgos = []
        for i in range(len(capas) - 1):
            w = np.random.randn(capas[i], capas[i+1]) * 0.1
            b = np.zeros((1, capas[i+1]))
            self.pesos.append(w)
            self.sesgos.append(b)

    def sigmoide(self, x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    def derivada_sigmoide(self, x):
        return x * (1 - x)

    def forward(self, X):
        activaciones = [X]
        for i in range(len(self.pesos)):
            net = np.dot(activaciones[-1], self.pesos[i]) + self.sesgos[i]
            activaciones.append(self.sigmoide(net))
        return activaciones

    def entrenar(self, X, y, epocas=2000, lr=0.1):
        for _ in range(epocas):
            activaciones = self.forward(X)
            error = y - activaciones[-1]
            
            # Backpropagation para múltiples capas
            deltas = [error * self.derivada_sigmoide(activaciones[-1])]
            for i in range(len(self.pesos) - 2, -1, -1):
                delta = np.dot(deltas[0], self.pesos[i+1].T) * self.derivada_sigmoide(activaciones[i+1])
                deltas.insert(0, delta)
                
            for i in range(len(self.pesos)):
                self.pesos[i] += np.dot(activaciones[i].T, deltas[i]) * lr
                self.sesgos[i] += np.sum(deltas[i], axis=0, keepdims=True) * lr

# Entrenar IA con 3 capas ocultas
red_ia = RedNeuronalProfunda([3, 5, 4, 1])
X_train = np.array([[0.9, 0.1, 0.9], [0.8, 0.2, 0.7], [0.2, 0.8, 0.2], [0.1, 0.9, 0.1]])
y_train = np.array([[1], [1], [0], [0]])
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
        activaciones = red_ia.forward(X)
        prob = float(activaciones[-1][0][0])
        
        if prob > 0.7: decision = "APROBADO (Riesgo Bajo)"
        elif prob < 0.3: decision = "RECHAZADO (Riesgo Alto)"
        else: decision = "REVISIÓN (Riesgo Medio)"
            
        return {
            "status": "éxito", 
            "decision": decision,
            "probabilidad": round(prob, 4)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)