import os
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pyautogui
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="El Puente Universal", description="Sistema Todo-en-Uno")

# ==========================================
# MÓDULO 1: CONECTOR DE ARCHIVOS (Excel / CSV)
# ==========================================
@app.get("/excel/leer")
def leer_excel():
    """Simula leer un programa viejo basado en Excel."""
    try:
        # Creamos un Excel de prueba si no existe
        if not os.path.exists("datos_empresa.xlsx"):
            df = pd.DataFrame({"ID": [1, 2], "Producto": ["Laptop", "Mouse"], "Precio": [1000, 20]})
            df.to_excel("datos_empresa.xlsx", index=False)
        
        df = pd.read_excel("datos_empresa.xlsx")
        return {"status": "éxito", "datos": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MÓDULO 2: CONECTOR DE BASE DE DATOS (SQL)
# ==========================================
def get_db():
    conn = sqlite3.connect("empresa.db")
    return conn

@app.get("/db/usuarios")
def leer_db():
    """Lee usuarios de una base de datos SQL."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT)")
        cursor.execute("INSERT OR IGNORE INTO usuarios (id, nombre) VALUES (1, 'Admin'), (2, 'Juan')")
        conn.commit()
        
        cursor.execute("SELECT * FROM usuarios")
        filas = cursor.fetchall()
        conn.close()
        return {"status": "éxito", "datos": [{"id": f[0], "nombre": f[1]} for f in filas]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MÓDULO 3: CONECTOR WEB (Web Scraping)
# ==========================================
@app.get("/web/scraping")
def hacer_scraping():
    """Extrae el título de una página web (ej. Wikipedia)."""
    try:
        url = "https://es.wikipedia.org/wiki/Python"
        respuesta = requests.get(url, timeout=10)
        soup = BeautifulSoup(respuesta.text, 'html.parser')
        titulo = soup.find('h1').text
        return {"status": "éxito", "titulo_extraido": titulo, "url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# MÓDULO 4: CONECTOR DE ESCRITORIO (RPA)
# ==========================================
@app.post("/pc/automatizar")
def automatizar_pc():
    """
    Mueve el ratón y escribe en tu PC. 
    ¡ADVERTENCIA! Al ejecutarlo, tomará el control de tu ratón por 3 segundos.
    """
    try:
        # En un caso real, aquí abrirías un programa y harías clics
        pyautogui.moveTo(500, 500, duration=1)
        pyautogui.write('Hola socio, soy tu bot.', interval=0.05)
        return {"status": "éxito", "mensaje": "El bot controló el teclado y ratón."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def raiz():
    return FileResponse("index_puente.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)