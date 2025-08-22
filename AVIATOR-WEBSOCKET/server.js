const WebSocketService = require('./websocketConnection');
const ApiServer = require('./apiServer');

class MainServer {
  constructor() {
    this.webSocketService = null;
    this.apiServer = null;
  }

  async start() {
    try {
      console.log('🚀 Iniciando servidor principal de Aviator...');
      
      // Iniciar servidor API
      console.log('📡 Iniciando servidor API...');
      this.apiServer = new ApiServer();
      this.apiServer.start(3000);
      console.log('✅ Servidor API iniciado');
      
      // Esperar un momento para que el servidor API se estabilice
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Iniciar servicio WebSocket
      console.log('🔌 Iniciando servicio WebSocket...');
      this.webSocketService = new WebSocketService();
      this.webSocketService.setApiServer(this.apiServer);
      
      // Configurar el WebSocketService en el ApiServer para comunicación bidireccional
      this.apiServer.setWebSocketService(this.webSocketService);
      
      await this.webSocketService.initialize();
      console.log('✅ Servicio WebSocket iniciado');
      
      console.log('✅ Servidor principal iniciado exitosamente');
      console.log('📊 Monitoreando partidas de Aviator en tiempo real');
      console.log('🌐 API REST disponible en: https://localhost:3000/api (con SSL)');
      console.log('📡 WebSocket disponible en wss://localhost:3000 (con SSL)');
      console.log('🔧 Sistema configurado como API backend puro y público');
      console.log('🌍 Accesible desde internet con certificado SSL válido');
      
      // Mantener el proceso activo
      console.log('🔄 Servidor ejecutándose... Presiona Ctrl+C para detener');
      
    } catch (error) {
      console.error('❌ Error al iniciar el servidor principal:', error);
      console.error('Stack trace:', error.stack);
      process.exit(1);
    }
  }

  // Método para cerrar limpiamente
  async shutdown() {
    console.log('🔄 Cerrando servidor...');
    
    if (this.webSocketService) {
      try {
        // Limpiar recursos del WebSocketService
        if (typeof this.webSocketService.cleanup === 'function') {
          this.webSocketService.cleanup();
        }
        console.log('✅ Servicio WebSocket cerrado');
      } catch (error) {
        console.error('❌ Error cerrando WebSocket:', error);
      }
    }
    
    if (this.apiServer) {
      try {
        // Cerrar servidor HTTP
        this.apiServer.server.close(() => {
          console.log('✅ Servidor HTTP cerrado');
        });
      } catch (error) {
        console.error('❌ Error cerrando servidor HTTP:', error);
      }
    }
    
    console.log('👋 Servidor cerrado exitosamente');
    process.exit(0);
  }
}

// Manejar señales de terminación
process.on('SIGINT', () => {
  console.log('\n🛑 Recibida señal SIGINT');
  if (mainServer) {
    mainServer.shutdown();
  } else {
    process.exit(0);
  }
});

process.on('SIGTERM', () => {
  console.log('\n🛑 Recibida señal SIGTERM');
  if (mainServer) {
    mainServer.shutdown();
  } else {
    process.exit(0);
  }
});

// Manejar errores no capturados
process.on('uncaughtException', (error) => {
  console.error('❌ Error no capturado:', error);
  console.error('Stack trace:', error.stack);
  if (mainServer) {
    mainServer.shutdown();
  } else {
    process.exit(1);
  }
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ Promesa rechazada no manejada:', reason);
  console.error('Promise:', promise);
  if (mainServer) {
    mainServer.shutdown();
  } else {
    process.exit(1);
  }
});

// Iniciar servidor
console.log('🚀 Iniciando sistema...');
let mainServer;

try {
  mainServer = new MainServer();
  mainServer.start().catch(error => {
    console.error('❌ Error fatal en el servidor:', error);
    process.exit(1);
  });
} catch (error) {
  console.error('❌ Error creando el servidor:', error);
  process.exit(1);
}
