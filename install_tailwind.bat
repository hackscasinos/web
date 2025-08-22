@echo off
echo ========================================
echo    Instalando Tailwind CSS Localmente
echo ========================================
echo.

echo Verificando Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js no esta instalado
    echo Por favor instala Node.js desde: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js encontrado: 
node --version
echo.

echo Verificando npm...
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: npm no esta disponible
    pause
    exit /b 1
)

echo npm encontrado:
npm --version
echo.

echo Instalando dependencias...
npm install
if %errorlevel% neq 0 (
    echo ERROR: Fallo al instalar dependencias
    pause
    exit /b 1
)

echo.
echo Compilando CSS inicial...
npm run build-prod
if %errorlevel% neq 0 (
    echo ERROR: Fallo al compilar CSS
    pause
    exit /b 1
)

echo.
echo ========================================
echo    ¡Instalacion completada!
echo ========================================
echo.
echo Para desarrollo, ejecuta: npm run build
echo Para produccion, ejecuta: npm run build-prod
echo.
echo El archivo CSS esta en: static/css/output.css
echo.
pause
