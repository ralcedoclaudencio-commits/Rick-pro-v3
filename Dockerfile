FROM python:3.11-slim

# Instalar ffmpeg (necesario para convertir a MP3)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend.py .

# Carpeta de descargas
RUN mkdir -p downloads

EXPOSE 5000

CMD gunicorn backend:app --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 300
