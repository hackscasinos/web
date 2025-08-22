# 🎰 DESA BOTS - Sistema de Señales de Casino

Sistema completo de bots para casinos en línea con señales en tiempo real, análisis de patrones y gestión de usuarios.

## 🚀 Características Principales

### 🎯 Juegos Soportados
- **Aviator**: 1xbet, 1win, 888starz
- **Ruleta**: Mega Roulette, Auto Roulette, Azure Roulette, Ruby Roulette
- **Otros**: Spaceman

### 🔒 Sistema de Seguridad
- Autenticación JWT
- Control de acceso basado en roles
- Verificación de dominio (solo https://hacks.casino/)
- Límite de conexiones WebSocket por usuario
- Logging de seguridad completo

### 📊 Funcionalidades
- Señales en tiempo real via WebSocket
- Dashboard con estadísticas
- Sistema de usuarios y roles
- Análisis de patrones de juego
- Gestión de bots automáticos

## 🛠️ Tecnologías Utilizadas

### Backend
- **Python 3.8+**
- **Flask** - Framework web
- **SQLAlchemy** - ORM para base de datos
- **PostgreSQL** - Base de datos
- **JWT** - Autenticación
- **WebSockets** - Comunicación en tiempo real

### Frontend
- **HTML5/CSS3**
- **TailwindCSS** - Framework CSS
- **JavaScript ES6+**
- **WebSocket API** - Conexión en tiempo real

### Herramientas
- **Node.js** - Gestión de dependencias frontend
- **PostCSS** - Procesamiento CSS
- **Git** - Control de versiones

## 📁 Estructura del Proyecto

```
DESA_BOTS/
├── app.py                 # Aplicación principal Flask
├── config.py             # Configuración del sistema
├── requirements.txt      # Dependencias Python
├── package.json          # Dependencias Node.js
├── tailwind.config.js    # Configuración TailwindCSS
├── templates/            # Plantillas HTML
│   ├── signals_casino.html
│   ├── mega_roulette.html
│   ├── auto_roulette.html
│   ├── roulette_ruby.html
│   ├── roulette_azure.html
│   ├── 1win_aviator.html
│   ├── aviator_signals.html
│   └── ...
├── static/               # Archivos estáticos
│   ├── css/
│   ├── js/
│   └── img/
├── uploads/              # Archivos subidos por usuarios
└── __pycache__/          # Cache de Python (ignorado por Git)
```

## 🚀 Instalación

### Prerrequisitos
- Python 3.8+
- Node.js 14+
- PostgreSQL
- Git

### 1. Clonar el repositorio
```bash
git clone https://github.com/hackscasinos/web.git
cd web
```

### 2. Configurar Python
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Node.js
```bash
# Instalar dependencias
npm install

# Construir CSS con Tailwind
npm run build:css
```

### 4. Configurar base de datos
```bash
# Crear base de datos PostgreSQL
createdb desa_bots

# Configurar variables de entorno en config.py
```

### 5. Ejecutar el sistema
```bash
# Terminal 1: Servidor Flask
python app.py

# Terminal 2: Servidor WebSocket (ruleta.py)
python ruleta.py

# Terminal 3: Construir CSS (desarrollo)
npm run watch:css
```

## 🔧 Configuración

### Variables de Entorno
```python
# config.py
SECRET_KEY = 'tu_clave_secreta_aqui'
DATABASE_URL = 'postgresql://usuario:password@localhost/desa_bots'
JWT_SECRET = 'tu_jwt_secret_aqui'
```

### Dominios Permitidos
```python
# ruleta.py
ALLOWED_ORIGINS = ['https://hacks.casino']
```

## 📡 API Endpoints

### Autenticación
- `POST /api/websocket/auth` - Generar token WebSocket
- `POST /api/websocket/verify` - Verificar token externo
- `GET /api/websocket/status` - Estado de conexión

### Usuarios
- `POST /login` - Iniciar sesión
- `POST /register` - Registro de usuario
- `GET /dashboard` - Panel principal

### Juegos
- `GET /mega-roulette` - Mega Roulette
- `GET /auto-roulette` - Auto Roulette
- `GET /roulette-ruby` - Ruby Roulette
- `GET /roulette-azure` - Azure Roulette
- `GET /1win-aviator` - 1win Aviator
- `GET /888starz-aviator` - 888starz Aviator

## 🔒 Seguridad

### Autenticación
- JWT tokens con expiración
- Verificación de roles de usuario
- Control de acceso basado en permisos

### WebSocket
- Verificación de origen de dominio
- Límite de conexiones por usuario
- Logging de todas las conexiones

### Rate Limiting
- Límite de 30 requests por minuto en APIs críticas
- Protección contra ataques de fuerza bruta

## 📊 Monitoreo

### Logs de Seguridad
- Todas las conexiones WebSocket
- Intentos de acceso no autorizado
- Cambios de estado de usuarios

### Métricas
- Usuarios conectados
- Señales enviadas
- Rendimiento del sistema

## 🚀 Despliegue

### Producción
```bash
# Configurar servidor web (Nginx/Apache)
# Configurar SSL/TLS
# Configurar base de datos PostgreSQL
# Configurar variables de entorno
```

### Docker (Próximamente)
```bash
# docker-compose up -d
```

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es privado y confidencial. Todos los derechos reservados.

## 📞 Soporte

Para soporte técnico, contacta al equipo de desarrollo.

---

**⚠️ ADVERTENCIA**: Este sistema es para uso educativo y de desarrollo. No se garantiza su uso en entornos de producción sin las modificaciones de seguridad apropiadas.
