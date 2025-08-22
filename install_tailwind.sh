#!/bin/bash

echo "========================================"
echo "   Instalando Tailwind CSS Localmente"
echo "========================================"
echo

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js no está instalado"
    echo "Por favor instala Node.js desde: https://nodejs.org/"
    exit 1
fi

echo "Node.js encontrado: $(node --version)"

# Verificar npm
if ! command -v npm &> /dev/null; then
    echo "ERROR: npm no está disponible"
    exit 1
fi

echo "npm encontrado: $(npm --version)"
echo

# Instalar dependencias
echo "Instalando dependencias..."
if ! npm install; then
    echo "ERROR: Fallo al instalar dependencias"
    exit 1
fi

echo
echo "Compilando CSS inicial..."
if ! npm run build-prod; then
    echo "ERROR: Fallo al compilar CSS"
    exit 1
fi

echo
echo "========================================"
echo "   ¡Instalación completada!"
echo "========================================"
echo
echo "Para desarrollo, ejecuta: npm run build"
echo "Para producción, ejecuta: npm run build-prod"
echo
echo "El archivo CSS está en: static/css/output.css"
echo
