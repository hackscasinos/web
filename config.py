# Configuración del Bot de Aviator
# =================================

# Configuración de Telegram
TELEGRAM_TOKEN = '8431342525:AAFbd6xmqc1ta8qh8PJwTLqlICX21DpwGjg'
TELEGRAM_CHAT_ID = '-1002502684363'

# Configuración de la API
API_URL = 'https://statszones.com:3000/api/rounds/bookmaker/1?limit=100'
API_HEADERS = {
    "Origin": "https://software.grupoaviatorcolombia.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
}

# Parámetros de trading
TRADING_CONFIG = {
    'gales': 1,           # Número máximo de Gales
    'alvo': 1.5,          # Multiplicador objetivo para cobrar
    'prediction_threshold': 3.0,  # Umbral para activar predicciones
    'prediction_window': 10,      # Ventana de tiempo en segundos para predicciones
    'prediction_offset': 130,     # Offset en segundos para predicciones (2min 10s)
}

# Configuración de logging
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'aviator_bot.log'
}

# Configuración de intervalos
TIMING_CONFIG = {
    'base_sleep': 1,              # Tiempo base entre requests
    'error_sleep_multiplier': 5,  # Multiplicador de tiempo en caso de errores
    'max_error_sleep': 30,        # Tiempo máximo de espera por errores
    'consecutive_error_threshold': 5  # Umbral de errores consecutivos
}

# Configuración de resumen
SUMMARY_CONFIG = {
    'entries_per_summary': 20,    # Número de entradas antes de enviar resumen
    'include_api_stats': True     # Incluir estadísticas de API en resumen
}
