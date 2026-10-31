import os
import sqlite3
import pandas as pd
import requests
import random
import math
import numpy as np
import re
import json
import asyncio
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
from google import genai
from playwright.sync_api import sync_playwright

# ==========================================
# CONFIGURACIÓN DE IA Y BÚSQUEDA
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "clave_no_configurada")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "clave_no_configurada")
client_ia = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="Puente Universal - Cazador Universal")

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
# A. EXCEL PRO
# ==========================================
@app.post("/excel/analizar")
async def analizar_excel_pro(
    archivo: UploadFile = File(...), 
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        df = pd.read_excel(archivo.file)
        perfil = {"total_filas": len(df), "total_columnas": len(df.columns), "valores_nulos": int(df.isnull().sum().sum())}
        num_df = df.select_dtypes(include=['number'])
        correlaciones = num_df.corr().round(2).to_dict() if len(num_df.columns) > 1 else {}
        return {"status": "éxito", "perfil": perfil, "correlaciones": correlaciones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ==========================================
# B. EL CAZADOR UNIVERSAL (Serper + Playwright + Gemini)
# ==========================================
class PeticionCazador(BaseModel):
    busqueda: str

def buscar_con_serper(query):
    """Busca en Google usando la API de Serper (resultados limpios y sin bloqueos)."""
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query + " comprar"})
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)
        data = response.json()
        enlaces = []
        for item in data.get("organic", []):
            link = item.get("link")
            if link and not any(x in link for x in ["youtube", "facebook", "instagram"]):
                enlaces.append(link)
            if len(enlaces) >= 3:
                break
        return enlaces
    except Exception as e:
        return []

def extraer_datos_con_ia(html, objetivo):
    prompt = f"""
    Eres un experto en análisis de datos. Del siguiente HTML extrae la información del producto.
    Busco: {objetivo}
    
    Devuelve SOLO un JSON con este formato exacto:
    {{"producto": "nombre", "precio": 0.0, "moneda": "MXN", "vendedor": "nombre", "link": "url"}}
    
    Si no encuentras precio, devuelve precio 0.
    
    HTML: {html[:20000]}
    """
    try:
        response = client_ia.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        texto = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(texto)
    except Exception:
        return None

@app.post("/web/cazador")
def ejecutar_cazador(
    peticion: PeticionCazador,
    usuario_actual: UsuarioDB = Depends(obtener_usuario_actual)
):
    try:
        # 1. Buscar con Serper (Google)
        enlaces = buscar_con_serper(peticion.busqueda)
        if not enlaces:
            return {"status": "error", "mensaje": "No se encontraron tiendas. Verifica tu API Key de Serper."}
        
        resultados = []
        
        # 2. Usar Playwright para abrir cada tienda
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            for link in enlaces:
                try:
                    page.goto(link, timeout=20000)
                    page.wait_for_timeout(3000)
                    html = page.content()
                    
                    datos = extraer_datos_con_ia(html, peticion.busqueda)
                    if datos and datos.get('precio', 0) > 0:
                        datos['tienda_url'] = link
                        resultados.append(datos)
                except Exception:
                    continue
            
            browser.close()
        
        # 3. Ordenar por precio
        resultados.sort(key=lambda x: x.get('precio', float('inf')))
        
        if not resultados:
            return {"status": "error", "mensaje": "La IA no pudo extraer precios válidos de las tiendas."}
        
        mejor = resultados[0]
        return {
            "status": "éxito",
            "pedido": peticion.busqueda,
            "mejor_oferta": mejor,
            "todas_las_ofertas": resultados,
            "mensaje": f"El mejor precio para '{peticion.busqueda}' es ${mejor['precio']} {mejor['moneda']} en {mejor.get('vendedor', 'tienda')}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el cazador: {str(e)}")

# ==========================================
# C. IA PREDICTIVA
# ==========================================
class RedNeuronalProfunda:
    def __init__(self, capas):
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
            deltas = [error * self.derivada_sigmoide(activaciones[-1])]
            for i in range(len(self.pesos) - 2, -1, -1):
                delta = np.dot(deltas[0], self.pesos[i+1].T) * self.derivada_sigmoide(activaciones[i+1])
                deltas.insert(0, delta)
            for i in range(len(self.pesos)):
                self.pesos[i] += np.dot(activaciones[i].T, deltas[i]) * lr
                self.sesgos[i] += np.sum(deltas[i], axis=0, keepdims=True) * lr

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
            
        return {"status": "éxito", "decision": decision, "probabilidad": round(prob, 4)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)