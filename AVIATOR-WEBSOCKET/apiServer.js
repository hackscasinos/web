const express = require('express');
const cors = require('cors');
const WebSocket = require('ws');
const https = require('https');
const http = require('http');
const Database = require('./database');
const fs = require('fs');
const path = require('path');

class ApiServer {
  constructor() {
    this.app = express();
    
    // Configuración SSL
    this.sslOptions = this.loadSSLCertificates();
    
    // Crear servidor HTTPS si hay certificados SSL
    if (this.sslOptions) {
      this.server = https.createServer(this.sslOptions, this.app);
      console.log('🔒 Servidor HTTPS configurado con SSL');
    } else {
      this.server = http.createServer(this.app);
      console.log('⚠️ Servidor HTTP configurado (sin SSL)');
    }
    
    this.wss = new WebSocket.Server({ server: this.server });
    this.database = new Database();
    this.clients = new Set();
    this.websocketService = null;
    
    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSocket();
  }

  setWebSocketService(websocketService) {
    this.websocketService = websocketService;
    // Configurar callback para notificaciones de reinicio
    if (websocketService && typeof websocketService.setRestartCallback === 'function') {
      websocketService.setRestartCallback((type) => {
        this.broadcastMessage('websocket_status', {
          type: type,
          message: type === 'websocket_restarted' ? 'Servicio WebSocket reiniciado' : 'Reinicio manual completado',
          timestamp: new Date().toISOString()
        });
      });
    }
    console.log('🔗 Servicio WebSocket configurado en API Server');
  }

  setupMiddleware() {
    // Cargar configuración CORS desde archivo
    let allowedOrigins = ['http://localhost:5000', 'http://127.0.0.1:5000'];
    
    try {
      const configPath = path.join(__dirname, 'ssl-config.json');
      if (fs.existsSync(configPath)) {
        const sslConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        if (sslConfig?.cors?.allowed_origins) {
          allowedOrigins = sslConfig.cors.allowed_origins;
          console.log('🌐 CORS configurado con orígenes permitidos:', allowedOrigins);
        }
      }
    } catch (error) {
      console.warn('⚠️ Error cargando configuración CORS, usando valores por defecto');
    }

    this.app.use(cors({
      origin: allowedOrigins,
      credentials: true
    }));
    this.app.use(express.json());
    // Removido: this.app.use(express.static('public'));
  }

  loadSSLCertificates() {
    try {
      // Cargar configuración SSL
      const configPath = path.join(__dirname, 'ssl-config.json');
      let sslConfig = null;
      
      if (fs.existsSync(configPath)) {
        sslConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        console.log('📋 Configuración SSL cargada desde ssl-config.json');
      } else {
        console.warn('⚠️ Archivo ssl-config.json no encontrado. Usando configuración por defecto.');
      }

      // Usar configuración del archivo o valores por defecto
      const certPath = sslConfig?.ssl?.certificates?.cert || 'C:/Users/Administrator/Desktop/statszones.com-crt.pem';
      const keyPath = sslConfig?.ssl?.certificates?.key || 'C:/Users/Administrator/Desktop/statszones.com-key.pem';
      const chainPath = sslConfig?.ssl?.certificates?.chain || 'C:/Users/Administrator/Desktop/statszones.com-chain.pem';

      // Verificar que existan los archivos de certificados
      if (!fs.existsSync(certPath) || !fs.existsSync(keyPath) || !fs.existsSync(chainPath)) {
        console.warn('⚠️ Archivos de certificados SSL no encontrados. Usando HTTP.');
        console.warn(`Certificado: ${certPath} - ${fs.existsSync(certPath) ? '✅' : '❌'}`);
        console.warn(`Clave privada: ${keyPath} - ${fs.existsSync(keyPath) ? '✅' : '❌'}`);
        console.warn(`Cadena de certificados: ${chainPath} - ${fs.existsSync(chainPath) ? '✅' : '❌'}`);
        return null;
      }

      const sslOptions = {
        cert: fs.readFileSync(certPath),
        key: fs.readFileSync(keyPath),
        ca: fs.readFileSync(chainPath)
      };

      console.log('🔒 Certificados SSL cargados exitosamente');
      console.log(`📜 Certificado: ${certPath}`);
      console.log(`🔑 Clave privada: ${keyPath}`);
      console.log(`⛓️ Cadena de certificados: ${chainPath}`);
      return sslOptions;
      
    } catch (error) {
      console.error('❌ Error cargando certificados SSL:', error.message);
      console.warn('⚠️ Continuando con servidor HTTP');
      return null;
    }
  }

  setupRoutes() {
    // Obtener configuración del bookmaker
    this.app.get('/api/config', (req, res) => {
      try {
        const configPath = path.join(__dirname, 'bookmaker.json');
        if (fs.existsSync(configPath)) {
          const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
          res.json({
            success: true,
            data: config
          });
        } else {
          res.status(404).json({
            success: false,
            error: 'Archivo de configuración no encontrado'
          });
        }
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Actualizar configuración del bookmaker
    this.app.post('/api/config', (req, res) => {
      try {
        const { second_message, third_message } = req.body;
        
        if (!second_message || !third_message) {
          return res.status(400).json({
            success: false,
            error: 'second_message y third_message son requeridos'
          });
        }

        // Validar formato base64
        if (!/^[A-Za-z0-9+/=]+$/.test(second_message) || !/^[A-Za-z0-9+/=]+$/.test(third_message)) {
          return res.status(400).json({
            success: false,
            error: 'Los mensajes deben estar en formato base64 válido'
          });
        }

        const configPath = path.join(__dirname, 'bookmaker.json');
        const currentConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        
        // Actualizar solo los mensajes
        const updatedConfig = {
          ...currentConfig,
          second_message,
          third_message,
          last_updated: new Date().toISOString()
        };

        // Crear backup antes de actualizar
        const backupPath = path.join(__dirname, `bookmaker_backup_${Date.now()}.json`);
        fs.writeFileSync(backupPath, JSON.stringify(currentConfig, null, 2));
        
        // Actualizar configuración
        fs.writeFileSync(configPath, JSON.stringify(updatedConfig, null, 2));

        // Notificar a todos los clientes WebSocket sobre el cambio de configuración
        this.broadcastConfigUpdate(updatedConfig);

        res.json({
          success: true,
          message: 'Configuración actualizada exitosamente',
          data: updatedConfig,
          backup_created: backupPath
        });

        console.log('✅ Configuración del bookmaker actualizada desde el frontend');
        
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Ruta para reiniciar todo el sistema
    this.app.post('/api/restart', async (req, res) => {
      try {
        console.log('🔄 Reinicio del sistema solicitado desde la API');
        
        // Notificar a todos los clientes WebSocket sobre el reinicio
        this.broadcastMessage('system_restart', {
          message: 'Sistema reiniciándose...',
          timestamp: new Date().toISOString()
        });
        
        // Reiniciar el servicio WebSocket si está disponible
        if (this.websocketService) {
          const result = await this.websocketService.restartService();
          if (result.success) {
            res.json({
              success: true,
              message: 'Reinicio del sistema iniciado exitosamente',
              timestamp: new Date().toISOString()
            });
          } else {
            res.status(500).json({
              success: false,
              error: 'Error durante el reinicio del servicio WebSocket'
            });
          }
        } else {
          res.json({
            success: true,
            message: 'Reinicio del sistema iniciado (servicio WebSocket no disponible)',
            timestamp: new Date().toISOString()
          });
        }
        
      } catch (error) {
        console.error('❌ Error durante el reinicio del sistema:', error.message);
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Obtener todas las rondas
    this.app.get('/api/rounds', async (req, res) => {
      try {
        const limit = parseInt(req.query.limit) || 100;
        const offset = parseInt(req.query.offset) || 0;
        const rounds = await this.database.getRounds(limit, offset);
        
        res.json({
          success: true,
          data: rounds,
          pagination: {
            limit,
            offset,
            total: rounds.length
          }
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Obtener rondas por bookmaker
    this.app.get('/api/rounds/bookmaker/:id', async (req, res) => {
      try {
        const bookmakerId = parseInt(req.params.id);
        const limit = parseInt(req.query.limit) || 100;
        const rounds = await this.database.getRoundsByBookmaker(bookmakerId, limit);
        
        res.json({
          success: true,
          data: rounds,
          bookmaker_id: bookmakerId
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Obtener la ronda más reciente
    this.app.get('/api/rounds/latest', async (req, res) => {
      try {
        const round = await this.database.getLatestRound();
        
        res.json({
          success: true,
          data: round
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Estadísticas generales
    this.app.get('/api/stats', async (req, res) => {
      try {
        const rounds = await this.database.getRounds(1000);
        
        if (rounds.length === 0) {
          return res.json({
            success: true,
            data: {
              total_rounds: 0,
              average_multiplier: 0,
              total_bets: 0,
              total_profit: 0
            }
          });
        }

        const stats = {
          total_rounds: rounds.length,
          average_multiplier: rounds.reduce((sum, r) => sum + r.max_multiplier, 0) / rounds.length,
          total_bets: rounds.reduce((sum, r) => sum + r.bets_count, 0),
          total_profit: rounds.reduce((sum, r) => sum + r.casino_profit, 0),
          highest_multiplier: Math.max(...rounds.map(r => r.max_multiplier)),
          lowest_multiplier: Math.min(...rounds.map(r => r.max_multiplier))
        };

        res.json({
          success: true,
          data: stats
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Estado del sistema
    this.app.get('/api/system-status', async (req, res) => {
      try {
        const configPath = path.join(__dirname, 'bookmaker.json');
        const config = fs.existsSync(configPath) ? JSON.parse(fs.readFileSync(configPath, 'utf8')) : null;
        
        const status = {
          timestamp: new Date().toISOString(),
          database: 'connected',
          websocket_clients: this.clients.size,
          config: config ? {
            id: config.id,
            name: config.name,
            last_updated: config.last_updated || 'Nunca actualizado'
          } : null
        };

        res.json({
          success: true,
          data: status
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Health check
    this.app.get('/api/health', (req, res) => {
      res.json({
        success: true,
        status: 'OK',
        timestamp: new Date().toISOString()
      });
    });

    // Obtener estado actual del WebSocket
    this.app.get('/api/status', (req, res) => {
      try {
        const wsStatus = this.getWebSocketStatus();
        res.json({
          success: true,
          data: wsStatus
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Obtener datos de la ronda actual en tiempo real
    this.app.get('/api/current-round', (req, res) => {
      try {
        const currentRound = this.getCurrentRoundData();
        res.json({
          success: true,
          data: currentRound
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });

    // Obtener historial de rondas con filtros
    this.app.get('/api/rounds/filter', async (req, res) => {
      try {
        const { 
          bookmaker_id, 
          start_date, 
          end_date, 
          min_multiplier, 
          max_multiplier,
          limit = 100,
          offset = 0
        } = req.query;

        const rounds = await this.database.getFilteredRounds({
          bookmaker_id,
          start_date,
          end_date,
          min_multiplier,
          max_multiplier,
          limit: parseInt(limit),
          offset: parseInt(offset)
        });

        res.json({
          success: true,
          data: rounds
        });
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message
        });
      }
    });
  }

  setupWebSocket() {
    this.wss.on('connection', (ws) => {
      console.log('Nuevo cliente WebSocket conectado');
      this.clients.add(ws);

      // Enviar mensaje de bienvenida
      ws.send(JSON.stringify({
        type: 'connection',
        message: 'Conectado al servidor de Aviator',
        timestamp: new Date().toISOString()
      }));

      ws.on('close', () => {
        console.log('Cliente WebSocket desconectado');
        this.clients.delete(ws);
      });

      ws.on('error', (error) => {
        console.error('Error en WebSocket:', error);
        this.clients.delete(ws);
      });
    });
  }

  // Método para enviar actualizaciones a todos los clientes WebSocket
  broadcastRoundUpdate(roundData) {
    const message = JSON.stringify({
      type: 'round_completed',
      data: roundData,
      timestamp: new Date().toISOString()
    });

    this.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(message);
        } catch (error) {
          console.error('Error enviando mensaje WebSocket:', error);
        }
      }
    });
  }

  // Método para notificar cambios de configuración
  broadcastConfigUpdate(config) {
    const message = JSON.stringify({
      type: 'config_updated',
      data: config,
      timestamp: new Date().toISOString()
    });

    this.broadcastMessage('config_updated', config);
  }

  // Método general para broadcast de mensajes
  broadcastMessage(type, data) {
    const message = JSON.stringify({
      type: type,
      data: data,
      timestamp: new Date().toISOString()
    });

    this.clients.forEach((client) => {
      if (client.readyState === WebSocket.OPEN) {
        try {
          client.send(message);
        } catch (error) {
          console.error('Error enviando mensaje WebSocket:', error);
        }
      }
    });
  }

  // Método para insertar una nueva ronda y notificar a los clientes
  async insertRoundAndNotify(roundData) {
    try {
      await this.database.insertRound(roundData);
      this.broadcastRoundUpdate(roundData);
      console.log(`Ronda ${roundData.round_id} insertada y notificada`);
    } catch (error) {
      console.error('Error insertando ronda:', error);
    }
  }

  // Método para obtener estado del WebSocket
  getWebSocketStatus() {
    return {
      websocket_clients: this.clients.size,
      timestamp: new Date().toISOString()
    };
  }

  // Método para obtener datos de la ronda actual
  getCurrentRoundData() {
    // Este método debe ser implementado para obtener datos del WebSocketService
    // Por ahora retornamos un placeholder
    return {
      status: 'active',
      timestamp: new Date().toISOString(),
      message: 'Datos de ronda actual disponibles via WebSocket'
    };
  }

  start(port = 3000) {
    this.server.listen(port, () => {
      const protocol = this.sslOptions ? 'HTTPS' : 'HTTP';
      const wsProtocol = this.sslOptions ? 'wss' : 'ws';
      const apiProtocol = this.sslOptions ? 'https' : 'http';
      
      console.log(`🚀 Servidor API ${protocol} iniciado en puerto ${port}`);
      console.log(`📡 WebSocket disponible en ${wsProtocol}://localhost:${port}`);
      console.log(`🌐 API REST disponible en ${apiProtocol}://localhost:${port}/api`);
      
      if (this.sslOptions) {
        console.log('🔒 SSL habilitado - Servidor seguro y público');
        console.log('🌍 Accesible desde internet con certificado válido');
      } else {
        console.log('⚠️ SSL no disponible - Solo acceso local');
      }
    });
  }
}

module.exports = ApiServer;
