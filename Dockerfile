FROM python:3.11-slim

# Instalar dependencias del sistema que necesita Chromium
RUN apt-get update && \
    apt-get install -y wget gnupg curl libnss3 libatk-bridge2.0-0 libxkbcommon0 libgtk-3-0 libasound2 libgbm1 && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Instalar el navegador de Playwright DENTRO de la imagen
RUN playwright install chromium

# Copiar el resto del código
COPY . .

# Comando de inicio
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "10000"]