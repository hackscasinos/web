#!/bin/bash

# Script de despliegue para DESA BOTS
# Uso: ./deploy.sh [production|staging|local]

set -e

ENVIRONMENT=${1:-local}
echo "🚀 Desplegando DESA BOTS en entorno: $ENVIRONMENT"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar que estamos en el directorio correcto
if [ ! -f "app.py" ]; then
    print_error "No se encontró app.py. Asegúrate de estar en el directorio raíz del proyecto."
    exit 1
fi

case $ENVIRONMENT in
    "local")
        print_status "Configurando entorno local..."
        
        # Crear entorno virtual si no existe
        if [ ! -d "venv" ]; then
            print_status "Creando entorno virtual..."
            python -m venv venv
        fi
        
        # Activar entorno virtual
        print_status "Activando entorno virtual..."
        source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
        
        # Instalar dependencias Python
        print_status "Instalando dependencias Python..."
        pip install -r requirements.txt
        
        # Instalar dependencias Node.js
        print_status "Instalando dependencias Node.js..."
        npm install
        
        # Construir CSS
        print_status "Construyendo CSS..."
        npm run build:css
        
        print_status "✅ Entorno local configurado correctamente"
        print_status "Para ejecutar:"
        echo "  Terminal 1: python app.py"
        echo "  Terminal 2: python ruleta.py"
        echo "  Terminal 3: npm run watch:css"
        ;;
        
    "staging")
        print_status "Configurando entorno de staging..."
        
        # Verificar variables de entorno
        if [ ! -f ".env" ]; then
            print_warning "Archivo .env no encontrado. Copiando desde .env.example..."
            cp env.example .env
            print_warning "Por favor, edita .env con las configuraciones correctas"
        fi
        
        # Construir Docker
        print_status "Construyendo imagen Docker..."
        docker-compose build
        
        print_status "✅ Entorno de staging configurado"
        print_status "Para ejecutar: docker-compose up"
        ;;
        
    "production")
        print_status "Configurando entorno de producción..."
        
        # Verificar que estamos en una rama de producción
        if [ "$(git branch --show-current)" != "main" ]; then
            print_warning "No estás en la rama main. Cambiando a main..."
            git checkout main
        fi
        
        # Pull de cambios recientes
        print_status "Actualizando código desde Git..."
        git pull origin main
        
        # Construir CSS de producción
        print_status "Construyendo CSS de producción..."
        npm run build:css
        
        # Verificar archivos de configuración
        if [ ! -f ".env" ]; then
            print_error "Archivo .env no encontrado. Es obligatorio para producción."
            exit 1
        fi
        
        print_status "✅ Entorno de producción configurado"
        print_status "Para ejecutar: gunicorn app:app --bind 0.0.0.0:5000"
        ;;
        
    *)
        print_error "Entorno no válido. Usa: local, staging, o production"
        echo "Uso: ./deploy.sh [production|staging|local]"
        exit 1
        ;;
esac

print_status "🎉 Despliegue completado exitosamente!"
