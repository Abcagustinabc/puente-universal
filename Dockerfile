# Usamos una imagen oficial de Playwright para Python que ya trae todo lo necesario
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Comando para arrancar la app (Render usa el puerto 10000 por defecto)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "10000"]