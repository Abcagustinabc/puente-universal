import os
import sqlite3
import pandas as pd
import requests
import secrets
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

app = FastAPI(title="El Puente Universal Seguro", description="Sistema Todo-en-Uno con Login")

# Configuración de seguridad
security = HTTPBasic()

# ⚠️ AQUÍ DEFINIMOS TU USUARIO Y CONTRASEÑA
USUARIO_VALIDO = "admin"
CONTRASENA_VALIDA = "super_secreto_2026"

# Función que verifica si el usuario puso las credenciales correctas
def verificar_credenciales(credentials: HTTPBasicCredentials = Depends(security)):
    es_usuario_correcto = secrets.compare_digest(credentials.username, USUARIO_VALIDO)
    es_contrasena_correcta = secrets.compare_digest(credentials.password, CONTRASENA_VALIDA)
    if not (es_usuario_correcto and es_contrasena_correcta):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# ==========================================
# RUTA PRINCIPAL (Protegida)
# ==========================================
@app.get("/")
def raiz(username: str = Depends(verificar_credenciales)):
    return FileResponse("index_puente.html")

# ==========================================
# MÓDULO 1: EXCEL DINÁMICO (Protegido)
# ==========================================
@app.post("/excel/leer")
async def leer_excel(
    archivo: UploadFile = File(...), 
    username: str = Depends(verificar_credenciales)
):
    try:
        df = pd.read_excel(archivo.file)
        datos = df.head(10).to_dict(orient="records")
        return {
            "status": "éxito", 
            "nombre_archivo": archivo.filename,
            "total_filas": len(df),
            "primeras_10_filas": datos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error leyendo el Excel: {str(e)}")

# ==========================================
# MÓDULO 2: BASE DE DATOS (Protegido y Seguro)
# ==========================================
def get_db():
    return sqlite3.connect("empresa.db")

class PeticionSQL(BaseModel):
    consulta: str

@app.post("/db/consultar")
def consultar_db(
    peticion: PeticionSQL,
    username: str = Depends(verificar_credenciales)
):
    consulta_limpia = peticion.consulta.strip().upper()
    
    # SEGURIDAD EXTRA: Solo permitimos consultas SELECT (lectura)
    if not consulta_limpia.startswith("SELECT"):
        raise HTTPException(
            status_code=403, 
            detail="Seguridad: Solo se permiten consultas de lectura (SELECT)."
        )
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Tabla de prueba
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT)")
        cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (1, 'Admin'), (2, 'Juan')")
        conn.commit()

        cursor.execute(peticion.consulta)
        columnas = [desc[0] for desc in cursor.description]
        filas = cursor.fetchall()
        resultados = [dict(zip(columnas, fila)) for fila in filas]
        conn.close()
        return {"status": "éxito", "resultados": resultados}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en SQL: {str(e)}")

# ==========================================
# MÓDULO 3: ESPÍA WEB (Protegido)
# ==========================================
class PeticionScraping(BaseModel):
    url: str

@app.post("/web/scraping")
def espiar_precio(
    peticion: PeticionScraping,
    username: str = Depends(verificar_credenciales)
):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        respuesta = requests.get(peticion.url, headers=headers, timeout=10)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        titulo = soup.title.string if soup.title else "Sin título"
        return {"status": "éxito", "url": peticion.url, "titulo_extraido": titulo.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en scraping: {str(e)}")

# ==========================================
# MÓDULO 4: RPA (Protegido)
# ==========================================
@app.post("/pc/automatizar")
def automatizar_pc(username: str = Depends(verificar_credenciales)):
    try:
        import pyautogui
        pyautogui.moveTo(500, 500, duration=1)
        pyautogui.write('Hola socio.', interval=0.05)
        return {"status": "éxito", "mensaje": "El bot controló el teclado."}
    except ImportError:
        raise HTTPException(status_code=501, detail="RPA no disponible en la nube (solo local).")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)