const WebSocket = require('ws');
const fs = require('fs');
const { decodeMessage } = require('./decoder');
const Database = require('./database');

// Configurar redirección de logs a logs.txt
const logStream = fs.createWriteStream('logs.txt', { flags: 'w' });
const originalConsoleLog = console.log;
const originalConsoleError = console.error;

console.log = (...args) => {
  const timestamp = new Date().toISOString();
  const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg, null, 2) : arg).join(' ');
  logStream.write(`${timestamp} - ${message}\n`);
};

console.error = (...args) => {
  const timestamp = new Date().toISOString();
  const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg, null, 2) : arg).join(' ');
  logStream.write(`${timestamp} - ERROR: ${message}\n`);
};

class WebSocketService {
  constructor() {
    this.connection = null;
    this.roundData = null;
    this.maxRetries = 5;
    this.retryDelay = 5000;
    this.database = new Database();
    this.apiServer = null;
    this.isInitialized = false;
    this.fileWatcher = null;
    this.configPath = 'bookmaker.json';
    this.lastConfigHash = null;
    this.restartCallback = null;
  }

  setApiServer(apiServer) {
    this.apiServer = apiServer;
  }

  setRestartCallback(callback) {
    this.restartCallback = callback;
  }

  // Monitorear cambios en el archivo de configuración
  startFileWatcher() {
    try {
      // Calcular hash inicial del archivo
      this.lastConfigHash = this.calculateFileHash(this.configPath);
      console.log('🔍 Monitoreo de archivo de configuración iniciado');

      // Configurar watcher de archivos
      this.fileWatcher = fs.watch(this.configPath, (eventType, filename) => {
        if (eventType === 'change' && filename) {
          console.log('📝 Archivo de configuración modificado, verificando cambios...');
          
          // Esperar un poco para que el archivo se termine de escribir
          setTimeout(() => {
            this.checkForConfigChanges();
          }, 1000);
        }
      });

      console.log('✅ Watcher de archivo configurado correctamente');
    } catch (error) {
      console.error('❌ Error al configurar watcher de archivo:', error.message);
    }
  }

  // Calcular hash del archivo para detectar cambios
  calculateFileHash(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const crypto = require('crypto');
      return crypto.createHash('md5').update(content).digest('hex');
    } catch (error) {
      console.error('❌ Error calculando hash del archivo:', error.message);
      return null;
    }
  }

  // Verificar si hay cambios en la configuración
  checkForConfigChanges() {
    try {
      const currentHash = this.calculateFileHash(this.configPath);
      
      if (currentHash && currentHash !== this.lastConfigHash) {
        console.log('🔄 Cambios detectados en la configuración del bookmaker');
        console.log('📊 Hash anterior:', this.lastConfigHash);
        console.log('📊 Hash actual:', currentHash);
        
        this.lastConfigHash = currentHash;
        
        // Reiniciar la conexión con la nueva configuración
        this.restartConnection();
      }
    } catch (error) {
      console.error('❌ Error verificando cambios de configuración:', error.message);
    }
  }

  // Reiniciar la conexión con nueva configuración
  async restartConnection() {
    try {
      console.log('🔄 Reiniciando conexión con nueva configuración...');
      
      // Cerrar conexión actual si existe
      if (this.connection && this.connection.ws) {
        this.connection.intentionalClose = true;
        this.connection.ws.close(1000, 'Reinicio por cambio de configuración');
      }
      
      // Limpiar datos de la ronda actual
      this.roundData = null;
      this.isInitialized = false;
      
      // Esperar un momento antes de reinicializar
      setTimeout(async () => {
        try {
          await this.initialize();
          console.log('✅ Conexión reiniciada exitosamente con nueva configuración');
          
          // Notificar al servidor API si es necesario
          if (this.restartCallback) {
            this.restartCallback('websocket_restarted');
          }
        } catch (error) {
          console.error('❌ Error al reinicializar la conexión:', error.message);
        }
      }, 2000);
      
    } catch (error) {
      console.error('❌ Error durante el reinicio de la conexión:', error.message);
    }
  }

  async initialize() {
    if (this.isInitialized) {
      console.log('WebSocketService ya está inicializado');
      return;
    }

    try {
      console.log('🔌 Inicializando WebSocketService...');
      
      // Leer configuración del bookmaker
      const data = fs.readFileSync('bookmaker.json', 'utf8');
      const bookmaker = JSON.parse(data);

      if (
        !bookmaker.url_websocket ||
        !bookmaker.url_websocket.startsWith('wss://') ||
        !bookmaker.first_message ||
        !bookmaker.second_message ||
        !bookmaker.third_message
      ) {
        throw new Error('Configuración inválida del bookmaker en bookmaker.json');
      }

      console.log(`📡 Iniciando conexión con el bookmaker ${bookmaker.id} (${bookmaker.name})`);
      this.connectToBookmaker(bookmaker, 0);
      this.isInitialized = true;
      
      // Iniciar monitoreo de archivos si no está activo
      if (!this.fileWatcher) {
        this.startFileWatcher();
      }
      
    } catch (error) {
      console.error('❌ Error al inicializar la conexión:', error.message);
      throw error;
    }
  }

  connectToBookmaker(bookmaker, retryCount) {
    const { id, name, url_websocket, first_message, second_message, third_message } = bookmaker;
    const headers = {
      Pragma: 'no-cache',
      'Cache-Control': 'no-cache',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
      Origin: 'https://aviator-next.spribegaming.com',
      'Accept-Encoding': 'gzip, deflate, br, zstd',
      'Accept-Language': 'es-419,es;q=0.9',
      'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
    };

    try {
      if (!third_message || !/^[A-Za-z0-9+/=]+$/.test(third_message)) {
        throw new Error(`Formato inválido del tercer mensaje para el bookmaker ${id}`);
      }

      console.log(`🔗 Conectando a ${url_websocket}...`);
      const ws = new WebSocket(url_websocket, [], { headers });

      this.connection = { ws, status: 'CONNECTING', lastPing: null, intentionalClose: false };
      this.roundData = {
        bookmaker_id: id,
        betsCount: 0,
        totalBetAmount: 0,
        onlinePlayers: 0,
        roundId: null,
        maxMultiplier: 0,
        currentMultiplier: 0,
        totalCashout: 0,
        cashoutRecords: new Set(),
        gameState: 'Bet',
      };

      ws.on('open', () => {
        this.connection = { ws, status: 'CONNECTED', lastPing: new Date(), intentionalClose: false };
        console.log(`✅ Conectado exitosamente al bookmaker ${id} (${name})`);
        console.log(`📤 Enviando primer mensaje de autenticación...`);
        ws.send(Buffer.from(first_message, 'base64'));
      });

      ws.on('message', async (data) => {
        try {
          const decodedMessage = decodeMessage(data);
          if (!decodedMessage) {
            console.warn(`⚠️ Mensaje inválido o vacío recibido del bookmaker ${id}`);
            return;
          }

          this.connection = { ws, status: 'CONNECTED', lastPing: new Date(), intentionalClose: false };

          if (!ws.firstResponseReceived) {
            console.log(`📤 Enviando segundo mensaje al bookmaker ${id}`);
            ws.send(Buffer.from(second_message, 'base64'));
            ws.firstResponseReceived = true;
          }

          if (decodedMessage.p) {
            const { p, c } = decodedMessage.p;

            if (c === 'updateCurrentBets') {
              this.roundData.betsCount = Math.max(this.roundData.betsCount, p.betsCount || 0);
              this.roundData.totalBetAmount = p.bets?.reduce((sum, bet) => sum + (bet.bet || 0), 0) || 0;
              this.roundData.gameState = 'Bet';
              console.log(`💰 Apuestas actualizadas: ${this.roundData.betsCount} apuestas, $${this.roundData.totalBetAmount.toFixed(2)} total`);
            } else if (c === 'onlinePlayers') {
              this.roundData.onlinePlayers = p.onlinePlayers || 0;
              console.log(`👥 Jugadores en línea del bookmaker ${id}: ${this.roundData.onlinePlayers}`);
            } else if (c === 'changeState') {
              if (p.newStateId === 1) {
                this.roundData.gameState = 'Bet';
                this.roundData.roundId = p.roundId || this.roundData.roundId;
                this.roundData.currentMultiplier = 0;
                if (p.roundId) {
                  console.log(`🎯 Nueva ronda iniciada en el bookmaker ${id}: ID=${p.roundId}, Estado=Apuestas`);
                }
              } else if (p.newStateId === 2) {
                this.roundData.gameState = 'Run';
                this.roundData.roundId = p.roundId || this.roundData.roundId;
                this.roundData.currentMultiplier = 0;
                console.log(`✈️ Avión despegando! Ronda ${this.roundData.roundId} en progreso...`);
              }
            } else if (c === 'updateCurrentCashOuts') {
              p.cashouts?.forEach((cashout) => {
                const cashoutKey = `${cashout.player_id || ''}-${cashout.betId || ''}-${cashout.multiplier || 0}`;
                if (!this.roundData.cashoutRecords.has(cashoutKey)) {
                  this.roundData.totalCashout += cashout.winAmount || 0;
                  this.roundData.cashoutRecords.add(cashoutKey);
                }
              });
              console.log(`💸 Total de cashouts del bookmaker ${id}: $${this.roundData.totalCashout.toFixed(2)}`);
            } else if (c === 'x') {
              if (p.crashX !== undefined) {
                this.roundData.maxMultiplier = p.crashX || 0;
                this.roundData.currentMultiplier = p.crashX || 0;
                this.roundData.gameState = 'End';
                console.log(`💥 RONDA FINALIZADA!`);
                console.log(`ID: ${this.roundData.roundId}`);
                console.log(`MULTIPLICADOR MÁXIMO: ${this.roundData.maxMultiplier.toFixed(2)}x`);
                console.log(`${'─'.repeat(50)}`);
                
                // Guardar ronda en base de datos y notificar a la API
                await this.saveRoundToDatabase();
                
                setTimeout(() => this.resetRoundData(), 4000);
              } else {
                this.roundData.currentMultiplier = p.x || 0;
                this.roundData.gameState = 'Run';
                // El avión sigue volando...
                if (this.roundData.currentMultiplier > 1.5) {
                  console.log(`✈️ Multiplicador actual: ${this.roundData.currentMultiplier.toFixed(2)}x`);
                }
              }
            } else if (c === 'roundChartInfo') {
              if (p.roundId) {
                this.roundData.roundId = p.roundId;
                this.roundData.maxMultiplier = p.maxMultiplier || 0;
                this.roundData.currentMultiplier = p.maxMultiplier || 0;
                console.log(`📊 RONDA FINALIZADA (ChartInfo)`);
                console.log(`ID: ${p.roundId}`);
                console.log(`MULTIPLICADOR MÁXIMO: ${p.maxMultiplier.toFixed(2)}x`);
                console.log(`${'─'.repeat(50)}`);
                
                // Guardar ronda en base de datos y notificar a la API
                await this.saveRoundToDatabase();
              }
            }
          }
        } catch (error) {
          console.error(`❌ Error al procesar mensaje del bookmaker ${id}:`, error.message);
        }
      });

      ws.on('error', (error) => {
        console.error(`❌ Error en la conexión WebSocket del bookmaker ${id}:`, error.message);
        this.connection = { ws, status: 'DISCONNECTED', lastPing: this.connection?.lastPing, intentionalClose: false };
      });

      ws.on('close', (code, reason) => {
        console.log(`🔌 Conexión WebSocket cerrada para el bookmaker ${id} (código: ${code}, razón: ${reason || 'ninguna'})`);
        if (code === 1000) {
          this.connection = { ws: null, status: 'DISCONNECTED', lastPing: null, intentionalClose: true };
          this.roundData = null;
        } else {
          this.connection = { ws, status: 'DISCONNECTED', lastPing: this.connection?.lastPing, intentionalClose: false };
          this.handleReconnect(bookmaker, retryCount);
        }
      });

      const pingInterval = setInterval(() => {
        if (!this.connection || this.connection.intentionalClose) return;
        if (ws.readyState === WebSocket.OPEN) {
          try {
            ws.send(Buffer.from(third_message, 'base64'));
            console.log(`📡 Ping enviado al bookmaker ${id}`);
          } catch (error) {
            console.error(`❌ Error al enviar PING al bookmaker ${id}:`, error.message);
            this.connection = { ws, status: 'DISCONNECTED', lastPing: this.connection?.lastPing, intentionalClose: false };
            this.handleReconnect(bookmaker, retryCount);
          }
        } else {
          this.handleReconnect(bookmaker, retryCount);
        }
      }, 10000);

      ws.on('pong', () => {
        this.connection = { ws, status: 'CONNECTED', lastPing: new Date(), intentionalClose: false };
        console.log(`📡 Pong recibido del bookmaker ${id}`);
      });

      ws.on('close', () => {
        clearInterval(pingInterval);
        console.log(`🔌 WebSocket cerrado, limpiando recursos...`);
      });
      
    } catch (error) {
      console.error(`❌ Fallo al conectar WebSocket para el bookmaker ${id}:`, error.message);
      this.handleReconnect(bookmaker, retryCount);
    }
  }

  async saveRoundToDatabase() {
    if (!this.roundData || !this.roundData.roundId) {
      console.warn('⚠️ No hay datos de ronda válidos para guardar');
      return;
    }

    try {
      // Calcular casino profit y loss percentage
      const casinoProfit = this.roundData.totalBetAmount - this.roundData.totalCashout;
      const lossPercentage = this.roundData.totalBetAmount > 0 
        ? ((casinoProfit / this.roundData.totalBetAmount) * 100) 
        : 0;

      const roundData = {
        bookmaker_id: this.roundData.bookmaker_id,
        round_id: this.roundData.roundId,
        bets_count: this.roundData.betsCount,
        total_bet_amount: this.roundData.totalBetAmount,
        online_players: this.roundData.onlinePlayers,
        max_multiplier: this.roundData.maxMultiplier,
        total_cashout: this.roundData.totalCashout,
        casino_profit: casinoProfit,
        loss_percentage: lossPercentage
      };

      // Guardar en base de datos
      await this.database.insertRound(roundData);
      console.log(`💾 Ronda ${this.roundData.roundId} guardada en base de datos`);

      // Notificar a la API si está disponible
      if (this.apiServer) {
        this.apiServer.insertRoundAndNotify(roundData);
        console.log(`📢 Ronda notificada a la API`);
      }
    } catch (error) {
      console.error('❌ Error guardando ronda en base de datos:', error);
    }
  }

  handleReconnect(bookmaker, retryCount) {
    if (this.connection?.intentionalClose) {
      console.log(`⏭️ Omitiendo reconexión para el bookmaker ${bookmaker.id} debido a cierre intencional`);
      return;
    }

    if (retryCount >= this.maxRetries) {
      console.error(`❌ Máximo de reintentos alcanzado para el bookmaker ${bookmaker.id}. Abandonando.`);
      this.connection = null;
      this.roundData = null;
      return;
    }

    console.log(`🔄 Intentando reconexión para el bookmaker ${bookmaker.id} (intento ${retryCount + 1}/${this.maxRetries})`);
    setTimeout(() => {
      this.connectToBookmaker(bookmaker, retryCount + 1);
    }, this.retryDelay * (retryCount + 1));
  }

  resetRoundData() {
    if (this.roundData) {
      this.roundData = {
        bookmaker_id: this.roundData.bookmaker_id,
        betsCount: 0,
        totalBetAmount: 0,
        onlinePlayers: this.roundData.onlinePlayers,
        roundId: null,
        maxMultiplier: 0,
        currentMultiplier: 0,
        totalCashout: 0,
        cashoutRecords: new Set(),
        gameState: 'Bet',
      };
      console.log('🔄 Datos de la ronda reiniciados');
    }
  }

  getStatus() {
    return {
      initialized: this.isInitialized,
      connection: this.connection ? {
        status: this.connection.status,
        lastPing: this.connection.lastPing
      } : null,
      roundData: this.roundData ? {
        gameState: this.roundData.gameState,
        roundId: this.roundData.roundId,
        currentMultiplier: this.roundData.currentMultiplier
      } : null
    };
  }

  // Método para reinicio manual completo
  async restartService() {
    try {
      console.log('🔄 Reinicio manual del servicio solicitado...');
      
      // Cerrar conexión actual si existe
      if (this.connection && this.connection.ws) {
        this.connection.intentionalClose = true;
        this.connection.ws.close(1000, 'Reinicio manual solicitado');
      }
      
      // Limpiar estado
      this.roundData = null;
      this.isInitialized = false;
      
      // Esperar un momento y reinicializar
      setTimeout(async () => {
        try {
          await this.initialize();
          console.log('✅ Servicio reiniciado manualmente exitosamente');
          
          // Notificar al servidor API
          if (this.restartCallback) {
            this.restartCallback('manual_restart');
          }
        } catch (error) {
          console.error('❌ Error durante el reinicio manual:', error.message);
        }
      }, 2000);
      
      return { success: true, message: 'Reinicio iniciado' };
    } catch (error) {
      console.error('❌ Error durante el reinicio manual:', error.message);
      return { success: false, error: error.message };
    }
  }

  // Limpiar recursos al cerrar
  cleanup() {
    if (this.fileWatcher) {
      this.fileWatcher.close();
      this.fileWatcher = null;
      console.log('🔍 Watcher de archivo cerrado');
    }
    
    if (this.connection && this.connection.ws) {
      this.connection.intentionalClose = true;
      this.connection.ws.close(1000, 'Limpieza del servicio');
    }
    
    console.log('🧹 Recursos del WebSocketService limpiados');
  }
}

// Exportar la clase pero NO inicializarla automáticamente
module.exports = WebSocketService;