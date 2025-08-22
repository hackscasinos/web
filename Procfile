# Procfile para DESA BOTS
# Define los procesos que se ejecutarán en producción

# Proceso web principal (Flask)
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --worker-class gevent --timeout 120 --keep-alive 2

# Proceso WebSocket (ruleta.py)
websocket: python ruleta.py

# Proceso de construcción de CSS (opcional, para desarrollo)
# build: npm run build:css

# Comando de inicio alternativo para desarrollo
# dev: python app.py
