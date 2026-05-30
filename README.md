# 🚀 RICK PRO V3 - CLOUD EDITION

Backend universal adaptado para funcionar en cualquier plataforma:
PC, servidor, Railway, Render, VPS, etc.

---

## 📁 Archivos incluidos

| Archivo | Para qué sirve |
|---|---|
| `backend.py` | El servidor principal (adaptado para la nube) |
| `requirements.txt` | Dependencias de Python |
| `Procfile` | Para Railway y Render |
| `nixpacks.toml` | Configuración de Railway (incluye ffmpeg) |
| `Dockerfile` | Para cualquier servidor con Docker |
| `runtime.txt` | Versión de Python |

---

## 🌐 OPCIÓN 1 — Railway (GRATIS, recomendado)

1. Crea cuenta en https://railway.app
2. Click en **"New Project" → "Deploy from GitHub"**
   - O arrastra la carpeta directamente
3. Railway detecta `nixpacks.toml` y configura todo solo
4. Te da una URL tipo: `https://tu-app.railway.app`
5. **Apunta esa URL en el `index.html`** (ver abajo)

---

## 🌐 OPCIÓN 2 — Render (GRATIS)

1. Crea cuenta en https://render.com
2. **New → Web Service → Upload files** (sube esta carpeta)
3. En "Start Command" pon:
   ```
   gunicorn backend:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300
   ```
4. En "Environment" agrega: `PYTHON_VERSION = 3.11.0`
5. **¡Importante!** Render necesita ffmpeg. En "Build Command":
   ```
   apt-get install -y ffmpeg && pip install -r requirements.txt
   ```

---

## 🖥️ OPCIÓN 3 — PC local (para pruebas)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Correr el servidor
python backend.py
```
El backend queda en: `http://localhost:5000`

---

## 🔗 Conectar el frontend (index.html) a la nube

Una vez que tengas tu URL de Railway o Render, busca en `index.html`
todas las líneas que digan `http://localhost:5000` y cámbialas por
tu URL. Por ejemplo:

```
ANTES:  fetch('http://localhost:5000/download', ...)
DESPUÉS: fetch('https://tu-app.railway.app/download', ...)
```

Puedes usar Ctrl+H en VS Code para reemplazar todas de golpe.

---

## ⚠️ Notas importantes

- Los archivos descargados se guardan en la carpeta `downloads/`
  dentro del servidor. En plataformas gratuitas (Railway/Render)
  **los archivos se borran al reiniciar**. Para guardar permanente
  necesitas un VPS o agregar almacenamiento externo (S3, etc).
- ffmpeg es necesario para convertir a MP3.
- La clave de acceso actual es: `rick`

---

## 🔑 Cambiar la clave de acceso

Abre `index.html` y busca:
```javascript
function claveCorrecta(v){ return v.trim().toLowerCase()==='rick'; }
```
Cambia `rick` por la clave que quieras.
