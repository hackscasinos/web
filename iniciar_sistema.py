#!/usr/bin/env python3
"""
Script de inicio simplificado para el sistema de múltiples ruletas
DESA BOTS - Sistema de Trading Automatizado
"""

import subprocess
import sys
import time
import os
from datetime import datetime

def mostrar_banner():
    """Muestra el banner del sistema"""
    print("🎰" * 20)
    print("🚀 DESA BOTS - SISTEMA DE MÚLTIPLES RULETAS")
    print("🎯 Trading Automatizado en Tiempo Real")
    print("🎰" * 20)
    print()

def verificar_archivos():
    """Verifica que existan los archivos necesarios"""
    archivos_requeridos = [
        'ruleta.py',
        'config_ruletas.py'
    ]
    
    archivos_faltantes = []
    for archivo in archivos_requeridos:
        if not os.path.exists(archivo):
            archivos_faltantes.append(archivo)
    
    if archivos_faltantes:
        print("❌ Archivos faltantes:")
        for archivo in archivos_faltantes:
            print(f"   • {archivo}")
        print("\n💡 Asegúrate de estar en el directorio correcto")
        return False
    
    print("✅ Todos los archivos requeridos están presentes")
    return True

def verificar_certificados_ssl():
    """Verifica que existan los certificados SSL"""
    from config_ruletas import SSL_CONFIG
    
    certificados_faltantes = []
    for tipo, ruta in SSL_CONFIG.items():
        if not os.path.exists(ruta):
            certificados_faltantes.append(f"{tipo}: {ruta}")
    
    if certificados_faltantes:
        print("⚠️  Certificados SSL faltantes:")
        for cert in certificados_faltantes:
            print(f"   • {cert}")
        print("\n💡 Verifica las rutas en config_ruletas.py")
        return False
    
    print("✅ Certificados SSL verificados")
    return True

def mostrar_configuracion():
    """Muestra la configuración actual del sistema"""
    try:
        from config_ruletas import RULETAS_CONFIG, SSL_CONFIG, WS_CONFIG
        
        print("\n📋 CONFIGURACIÓN DEL SISTEMA:")
        print("-" * 40)
        
        print("🎯 RULETAS CONFIGURADAS:")
        for id_ruleta, config in RULETAS_CONFIG.items():
            print(f"   • {config['name']} (ID: {id_ruleta}) → Puerto {config['puerto']}")
        
        print(f"\n🔒 CONFIGURACIÓN SSL:")
        print(f"   • Certificado: {SSL_CONFIG['certfile']}")
        print(f"   • Clave: {SSL_CONFIG['keyfile']}")
        print(f"   • Cadena: {SSL_CONFIG['cafile']}")
        
        print(f"\n🌐 CONFIGURACIÓN WEBSOCKET:")
        print(f"   • Host: {WS_CONFIG['host']}")
        print(f"   • Casino ID: {WS_CONFIG['casino_id']}")
        print(f"   • Moneda: {WS_CONFIG['currency']}")
        
    except ImportError as e:
        print(f"❌ Error importando configuración: {e}")
        return False
    
    return True

def iniciar_sistema():
    """Inicia el sistema principal"""
    print("\n🚀 INICIANDO SISTEMA DE MÚLTIPLES RULETAS...")
    print("=" * 50)
    
    try:
        # Ejecutar el sistema principal
        proceso = subprocess.Popen([
            sys.executable, 'ruleta.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print(f"✅ Sistema iniciado (PID: {proceso.pid})")
        print("\n📊 MONITOREO EN TIEMPO REAL:")
        print("   • Mega Ruleta: wss://localhost:8865")
        print("   • Roulette Azure: wss://localhost:8866")
        print("   • Roulette Ruby: wss://localhost:8867")
        print("   • Auto Roulette: wss://localhost:8868")
        
        print("\n💡 Para detener el sistema, presiona Ctrl+C")
        print("🔗 Cada ruleta funciona independientemente en su puerto")
        
        # Mostrar logs en tiempo real
        while True:
            output = proceso.stdout.readline()
            if output:
                print(output.strip())
            
            # Verificar si el proceso sigue activo
            if proceso.poll() is not None:
                print("❌ El sistema se ha detenido")
                break
                
    except KeyboardInterrupt:
        print("\n\n⏹️  Deteniendo sistema...")
        if 'proceso' in locals():
            proceso.terminate()
            proceso.wait()
        print("✅ Sistema detenido correctamente")
    except Exception as e:
        print(f"❌ Error iniciando sistema: {e}")

def mostrar_menu():
    """Muestra el menú principal"""
    while True:
        print("\n" + "=" * 50)
        print("🎰 MENÚ PRINCIPAL - DESA BOTS")
        print("=" * 50)
        print("1. 🚀 Iniciar Sistema de Ruletas")
        print("2. 🧪 Ejecutar Pruebas")
        print("3. 📋 Ver Configuración")
        print("4. 📚 Ver Documentación")
        print("5. ❌ Salir")
        print("=" * 50)
        
        opcion = input("\n🎯 Selecciona una opción (1-5): ").strip()
        
        if opcion == "1":
            if verificar_archivos() and verificar_certificados_ssl():
                iniciar_sistema()
            else:
                print("\n❌ No se puede iniciar el sistema. Verifica los errores anteriores.")
        elif opcion == "2":
            print("\n🧪 Ejecutando pruebas del sistema...")
            try:
                subprocess.run([sys.executable, 'test_multiple_ruletas.py'])
            except FileNotFoundError:
                print("❌ Archivo de pruebas no encontrado")
        elif opcion == "3":
            mostrar_configuracion()
        elif opcion == "4":
            print("\n📚 DOCUMENTACIÓN DISPONIBLE:")
            print("   • README_MULTIPLE_RULETAS.md - Guía completa del sistema")
            print("   • config_ruletas.py - Configuración de ruletas")
            print("   • test_multiple_ruletas.py - Script de pruebas")
            print("   • ruleta.py - Sistema principal")
        elif opcion == "5":
            print("\n👋 ¡Hasta luego! Sistema DESA BOTS cerrado.")
            break
        else:
            print("❌ Opción inválida. Selecciona 1-5.")
        
        input("\n⏸️  Presiona Enter para continuar...")

def main():
    """Función principal"""
    mostrar_banner()
    
    if not verificar_archivos():
        print("\n❌ No se pueden verificar los archivos. Verifica el directorio.")
        return
    
    mostrar_menu()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Sistema interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en el sistema: {e}")
        print("💡 Verifica la configuración y archivos")
