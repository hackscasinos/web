/**
 * CONFIGURACIÓN CENTRALIZADA - SIGNALS CASINO
 * Versión: 2.0.0
 * Autor: Hacks.Casino
 */

const APP_CONFIG = {
    // Configuración de la aplicación
    app: {
        name: 'Signals Casino',
        version: '2.0.0',
        environment: 'production', // development, staging, production
        debug: false
    },
    
    // Configuración de API
    api: {
        baseUrl: '/api',
        timeout: 10000,
        retryAttempts: 3,
        retryDelay: 1000
    },
    
    // Configuración de WebSocket
    websocket: {
        endpoint: '/ws',
        port: 8888,
        reconnectAttempts: 5,
        reconnectDelay: 3000,
        heartbeatInterval: 30000,
        connectionTimeout: 10000,
        maxMessageSize: 1024 * 1024 // 1MB
    },
    
    // Configuración de seguridad
    security: {
        tokenExpiryThreshold: 300, // 5 minutos antes de expirar
        maxFailedAuthAttempts: 3,
        lockoutDuration: 900000, // 15 minutos
        sessionTimeout: 3600000, // 1 hora
        csrfTokenHeader: 'X-CSRF-Token'
    },
    
    // Configuración de UI
    ui: {
        animationDuration: 300,
        notificationDuration: 5000,
        skeletonLoadingDelay: 1000,
        scrollThreshold: 100,
        hoverDelay: 200
    },
    
    // Configuración de juegos
    games: {
        aviator: {
            name: 'Aviator',
            provider: 'Spribe',
            type: 'Multiplicadores',
            route: '/aviator-signals',
            defaultStats: {
                signals: 0,
                precision: 0,
                status: 'offline'
            }
        },
        roulette: {
            name: 'Ruleta Live',
            provider: 'Evolution',
            type: 'Números',
            route: '/roulette-signals',
            defaultStats: {
                rounds: 67,
                precision: 92.1,
                status: 'online'
            }
        },
        spaceman: {
            name: 'Spaceman',
            provider: 'Pragmatic',
            type: 'Crash',
            route: '/spaceman-signals',
            defaultStats: {
                flights: 38,
                precision: 95.4,
                status: 'online'
            }
        }
    },
    
    // Configuración de errores
    errors: {
        reportToServer: true,
        logToConsole: true,
        showUserNotification: true,
        maxErrorLogSize: 100
    },
    
    // Configuración de performance
    performance: {
        throttleDelay: 16, // 60fps
        debounceDelay: 300,
        lazyLoadThreshold: 0.1,
        imageOptimization: true
    }
};

// Configuración específica por entorno
const ENV_CONFIG = {
    development: {
        debug: true,
        websocket: {
            endpoint: 'ws://localhost:8888'
        }
    },
    staging: {
        debug: false,
        websocket: {
            endpoint: 'wss://staging.hacks.casino:8888'
        }
    },
    production: {
        debug: false,
        websocket: {
            endpoint: 'wss://hacks.casino:8888'
        }
    }
};

// Función para obtener configuración del entorno actual
function getEnvironmentConfig() {
    const env = APP_CONFIG.app.environment;
    return ENV_CONFIG[env] || ENV_CONFIG.production;
}

// Función para obtener configuración completa
function getConfig() {
    const envConfig = getEnvironmentConfig();
    return {
        ...APP_CONFIG,
        ...envConfig
    };
}

// Función para validar configuración
function validateConfig(config) {
    const required = ['app', 'api', 'websocket', 'security'];
    const missing = required.filter(key => !config[key]);
    
    if (missing.length > 0) {
        console.error('Configuración incompleta. Faltan:', missing);
        return false;
    }
    
    return true;
}

// Función para obtener configuración validada
function getValidatedConfig() {
    const config = getConfig();
    
    if (!validateConfig(config)) {
        throw new Error('Configuración inválida');
    }
    
    return config;
}

// Exportar configuración
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        APP_CONFIG,
        ENV_CONFIG,
        getConfig,
        getEnvironmentConfig,
        validateConfig,
        getValidatedConfig
    };
} else {
    // Para uso en navegador
    window.APP_CONFIG = APP_CONFIG;
    window.getConfig = getConfig;
    window.getValidatedConfig = getValidatedConfig;
}
