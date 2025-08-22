const sqlite3 = require('sqlite3').verbose();
const path = require('path');

class Database {
  constructor() {
    this.dbPath = path.join(__dirname, 'aviator_rounds.db');
    this.db = null;
    this.init();
  }

  init() {
    this.db = new sqlite3.Database(this.dbPath, (err) => {
      if (err) {
        console.error('Error al abrir la base de datos:', err.message);
      } else {
        console.log('Base de datos conectada exitosamente');
        this.createTables();
      }
    });
  }

  createTables() {
    const createRoundsTable = `
      CREATE TABLE IF NOT EXISTS rounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bookmaker_id INTEGER NOT NULL,
        round_id TEXT UNIQUE NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        bets_count INTEGER DEFAULT 0,
        total_bet_amount REAL DEFAULT 0,
        online_players INTEGER DEFAULT 0,
        max_multiplier REAL DEFAULT 0,
        total_cashout REAL DEFAULT 0,
        casino_profit REAL DEFAULT 0,
        loss_percentage REAL DEFAULT 0
      )
    `;

    this.db.run(createRoundsTable, (err) => {
      if (err) {
        console.error('Error al crear tabla rounds:', err.message);
      } else {
        console.log('Tabla rounds creada/verificada exitosamente');
      }
    });
  }

  insertRound(roundData) {
    return new Promise((resolve, reject) => {
      const {
        bookmaker_id,
        round_id,
        bets_count,
        total_bet_amount,
        online_players,
        max_multiplier,
        total_cashout,
        casino_profit,
        loss_percentage
      } = roundData;

      const sql = `
        INSERT OR REPLACE INTO rounds 
        (bookmaker_id, round_id, bets_count, total_bet_amount, online_players, 
         max_multiplier, total_cashout, casino_profit, loss_percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `;

      this.db.run(sql, [
        bookmaker_id,
        round_id,
        bets_count,
        total_bet_amount,
        online_players,
        max_multiplier,
        total_cashout,
        casino_profit,
        loss_percentage
      ], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve(this.lastID);
        }
      });
    });
  }

  getRounds(limit = 100, offset = 0) {
    return new Promise((resolve, reject) => {
      const sql = `
        SELECT * FROM rounds 
        ORDER BY timestamp DESC 
        LIMIT ? OFFSET ?
      `;

      this.db.all(sql, [limit, offset], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  getRoundsByBookmaker(bookmakerId, limit = 100) {
    return new Promise((resolve, reject) => {
      const sql = `
        SELECT * FROM rounds 
        WHERE bookmaker_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
      `;

      this.db.all(sql, [bookmakerId, limit], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  getLatestRound() {
    return new Promise((resolve, reject) => {
      const sql = `
        SELECT * FROM rounds 
        ORDER BY timestamp DESC 
        LIMIT 1
      `;

      this.db.get(sql, (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(row);
        }
      });
    });
  }

  getFilteredRounds(filters) {
    return new Promise((resolve, reject) => {
      let sql = `SELECT * FROM rounds WHERE 1=1`;
      const params = [];

      if (filters.bookmaker_id) {
        sql += ` AND bookmaker_id = ?`;
        params.push(filters.bookmaker_id);
      }

      if (filters.start_date) {
        sql += ` AND timestamp >= ?`;
        params.push(filters.start_date);
      }

      if (filters.end_date) {
        sql += ` AND timestamp <= ?`;
        params.push(filters.end_date);
      }

      if (filters.min_multiplier) {
        sql += ` AND max_multiplier >= ?`;
        params.push(filters.min_multiplier);
      }

      if (filters.max_multiplier) {
        sql += ` AND max_multiplier <= ?`;
        params.push(filters.max_multiplier);
      }

      sql += ` ORDER BY timestamp DESC LIMIT ? OFFSET ?`;
      params.push(filters.limit, filters.offset);

      this.db.all(sql, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  getStats() {
    return new Promise((resolve, reject) => {
      const sql = `
        SELECT 
          COUNT(*) as total_rounds,
          AVG(max_multiplier) as avg_multiplier,
          MAX(max_multiplier) as max_multiplier_ever,
          SUM(total_bet_amount) as total_bets,
          SUM(total_cashout) as total_cashouts,
          AVG(casino_profit) as avg_casino_profit
        FROM rounds
      `;

      this.db.get(sql, (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(row);
        }
      });
    });
  }

  close() {
    if (this.db) {
      this.db.close((err) => {
        if (err) {
          console.error('Error al cerrar la base de datos:', err.message);
        } else {
          console.log('Base de datos cerrada exitosamente');
        }
      });
    }
  }
}

module.exports = Database;
