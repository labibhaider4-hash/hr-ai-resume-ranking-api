// src/middleware/logger.js
// ─────────────────────────────────────────────────────────────────────────────
//  Structured logging with Winston + request logging middleware
//  Writes: combined logs → logs/combined.log  |  errors → logs/error.log
// ─────────────────────────────────────────────────────────────────────────────

const winston = require('winston');
const path    = require('path');
const fs      = require('fs');

const LOG_DIR   = process.env.LOG_DIR   || './logs';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

// Ensure log directory exists
if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

// ── Winston logger ────────────────────────────────────────────────────────────
const logger = winston.createLogger({
  level: LOG_LEVEL,
  format: winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'hr-ai-api' },
  transports: [
    new winston.transports.File({
      filename: path.join(LOG_DIR, 'error.log'),
      level: 'error',
      maxsize: 5 * 1024 * 1024,  // 5 MB
      maxFiles: 5,
    }),
    new winston.transports.File({
      filename: path.join(LOG_DIR, 'combined.log'),
      maxsize: 10 * 1024 * 1024,
      maxFiles: 10,
    }),
  ],
});

// Pretty console output in dev
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.printf(({ timestamp, level, message, ...meta }) => {
        const extra = Object.keys(meta).length
          ? '\n  ' + JSON.stringify(meta, null, 2).replace(/\n/g, '\n  ')
          : '';
        return `${timestamp} [${level}] ${message}${extra}`;
      })
    )
  }));
}

// ── Request logging middleware + DB audit trail ───────────────────────────────
function requestLogger(db) {
  return (req, res, next) => {
    const start = Date.now();

    // Capture response finish
    res.on('finish', () => {
      const ms = Date.now() - start;

      logger.info('HTTP Request', {
        method:      req.method,
        url:         req.originalUrl,
        status:      res.statusCode,
        duration_ms: ms,
        ip:          req.ip,
        user_id:     req.user?.id,
        user_agent:  req.get('User-Agent'),
      });

      // Persist to DB (non-blocking)
      try {
        if (db) {
          db.prepare(`
            INSERT INTO api_logs
              (method, endpoint, status_code, response_ms, ip_address, user_agent, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
          `).run(
            req.method,
            req.originalUrl,
            res.statusCode,
            ms,
            req.ip,
            req.get('User-Agent') || null,
            req.user?.id || null
          );
        }
      } catch (_) { /* silently ignore log DB errors */ }
    });

    next();
  };
}

module.exports = { logger, requestLogger };
