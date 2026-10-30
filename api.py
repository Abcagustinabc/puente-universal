import os
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="El Puente Universal", description="Sistema Todo-en-Uno")

# Modelos para recibir datos desde la web
class PeticionScraping(BaseModel):
    url: str

class PeticionSQL(BaseModel):
    consulta: str

# ==========================================
# MÓDULO 1: EXCEL DINÁMICO (Subir archivo)
# ==========================================
@app.post("/excel/leer")
async def leer_excel(archivo: UploadFile = File(...)):
    try:
        # Leemos el archivo directamente desde la memoria (sin guardarlo en el disco duro)
        df = pd.read_excel(archivo.file)
        
        # Convertimos los datos a JSON (limitamos a 10 filas para no saturar la pantalla)
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
# MÓDULO 2: BASE DE DATOS DINÁMICA (Consultas SQL)
# ==========================================
def get_db():
    return sqlite3.connect("empresa.db")

@app.post("/db/consultar")
def consultar_db(peticion: PeticionSQL):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Creamos una tabla de prueba si no existe para que el usuario tenga qué consultar
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT)")
        cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (1, 'Admin'), (2, 'Juan')")
        conn.commit()

        # Ejecutamos la consulta que el usuario escribió
        cursor.execute(peticion.consulta)
        
        # Si la consulta es un SELECT, devolvemos los datos
        if peticion.consulta.strip().upper().startswith("SELECT"):
            columnas = [desc[0] for desc in cursor.description]
            filas = cursor.fetchall()
            resultados = [dict(zip(columnas, fila)) for fila in filas]
            conn.close()
            return {"status": "éxito", "resultados": resultados}
        else:
            # Si es INSERT, UPDATE o DELETE
            conn.commit()
            conn.close()
            return {"status": "éxito", "mensaje": "Comando ejecutado correctamente (sin resultados que mostrar)."}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en SQL: {str(e)}")

# ==========================================
# MÓDULO 3: ESPÍA DE PRECIOS DINÁMICO (URLs)
# ==========================================
@app.post("/web/scraping")
def espiar_precio(peticion: PeticionScraping):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        respuesta = requests.get(peticion.url, headers=headers, timeout=10)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        titulo = soup.title.string if soup.title else "Sin título"
        return {"status": "éxito", "url": peticion.url, "titulo_extraido": titulo.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en scraping: {str(e)}")

# ==========================================
# MÓDULO 4: RPA
# ==========================================
@app.post("/pc/automatizar")
def automatizar_pc():
    try:
        import pyautogui
        pyautogui.moveTo(500, 500, duration=1)
        pyautogui.write('Hola socio.', interval=0.05)
        return {"status": "éxito", "mensaje": "El bot controló el teclado."}
    except ImportError:
        raise HTTPException(status_code=501, detail="RPA no disponible en la nube (solo local).")

# ==========================================
# RUTA PRINCIPAL
# ==========================================
@app.get("/")
def raiz():
    return FileResponse("index_puente.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)