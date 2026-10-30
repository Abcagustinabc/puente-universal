import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="El Puente Inteligente")

# 1. CREAMOS LA CONEXIÓN AL PROGRAMA EXISTENTE (Simulada con SQLite)
def conectar_db():
    # En un caso real, aquí conectarías a SQL Server, Oracle o un archivo de Access
    conn = sqlite3.connect("sistema_viejo.db")
    return conn

# 2. CREAMOS LA TABLA SI NO EXISTE (Simulando el programa viejo)
def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

inicializar_db()

# Modelo para recibir datos desde internet
class ClienteNuevo(BaseModel):
    nombre: str
    email: str

# 3. EL PUENTE: Endpoint para leer datos del programa viejo
@app.get("/clientes")
def obtener_clientes():
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, email FROM clientes")
        filas = cursor.fetchall()
        conn.close()
        
        # Convertimos a formato moderno (JSON)
        clientes = [{"id": f[0], "nombre": f[1], "email": f[2]} for f in filas]
        return {"status": "éxito", "datos": clientes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando al programa: {str(e)}")

# 4. EL PUENTE: Endpoint para escribir datos en el programa viejo
@app.post("/clientes")
def agregar_cliente(cliente: ClienteNuevo):
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clientes (nombre, email) VALUES (?, ?)", (cliente.nombre, cliente.email))
        conn.commit()
        conn.close()
        return {"status": "éxito", "mensaje": f"Cliente {cliente.nombre} guardado en el sistema viejo"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error escribiendo en el programa: {str(e)}")

# Endpoint de prueba
@app.get("/")
def raiz():
    return {"mensaje": "El Puente Inteligente está vivo. Ve a /docs"}