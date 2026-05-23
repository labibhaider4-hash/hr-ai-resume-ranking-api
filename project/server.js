// server.js
// ─────────────────────────────────────────────────────────────────────────────
//  HR AI API — Express Server
//  Start: node server.js  |  Dev: npm run dev
// ─────────────────────────────────────────────────────────────────────────────

require('dotenv').config();
const express     = require('express');
const cors        = require('cors');
const helmet      = require('helmet');
const rateLimit   = require('express-rate-limit');

const { initDatabase }           = require('./src/database/schema');
const { logger, requestLogger }  = require('./src/middleware/logger');
const { createAuthRoutes }       = require('./src/middleware/auth');
const createCandidateRoutes      = require('./src/routes/candidates');
const createJobRoutes            = require('./src/routes/jobs');
const createResumeRoutes         = require('./src/routes/resumes');
const createRankingRoutes        = require('./src/routes/ranking');

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const db  = initDatabase();
const app = express();
const PORT = process.env.PORT || 3000;

// ── Global middleware ─────────────────────────────────────────────────────────
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '2mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(requestLogger(db));

// Rate limiting
app.use(rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 15 * 60 * 1000,
  max:      parseInt(process.env.RATE_LIMIT_MAX_REQUESTS) || 100,
  message:  { error: 'Too many requests, please try again later' },
}));

// ── Routes ────────────────────────────────────────────────────────────────────
app.use('/auth',       createAuthRoutes(db));
app.use('/candidates', createCandidateRoutes(db));
app.use('/jobs',       createJobRoutes(db));
app.use('/resumes',    createResumeRoutes(db));
app.use('/ranking',    createRankingRoutes(db));

// ── Health check ──────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
  const dbOk = !!db.prepare('SELECT 1').get();
  res.json({
    status:    dbOk ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    version:   require('./package.json').version,
    uptime_s:  Math.floor(process.uptime()),
  });
});

// ── API stats (admin endpoint) ────────────────────────────────────────────────
app.get('/stats', (req, res) => {
  res.json({
    candidates:   db.prepare('SELECT COUNT(*) as n FROM candidates').get().n,
    jobs:         db.prepare("SELECT COUNT(*) as n FROM job_postings WHERE status='open'").get().n,
    resumes:      db.prepare('SELECT COUNT(*) as n FROM resumes').get().n,
    parsed:       db.prepare("SELECT COUNT(*) as n FROM resumes WHERE parse_status='completed'").get().n,
    rankings:     db.prepare('SELECT COUNT(*) as n FROM ranking_results').get().n,
    api_requests: db.prepare('SELECT COUNT(*) as n FROM api_logs').get().n,
  });
});

// ── 404 ───────────────────────────────────────────────────────────────────────
app.use((req, res) => res.status(404).json({ error: `Route not found: ${req.method} ${req.path}` }));

// ── Global error handler ──────────────────────────────────────────────────────
app.use((err, req, res, _next) => {
  logger.error('Unhandled error', { error: err.message, stack: err.stack });
  if (err.code === 'LIMIT_FILE_SIZE')
    return res.status(413).json({ error: `File too large (max ${process.env.MAX_FILE_SIZE_MB || 10}MB)` });
  res.status(500).json({ error: 'Internal server error', message: err.message });
});

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  logger.info(`🚀  HR AI API running on port ${PORT}`, {
    env:  process.env.NODE_ENV,
    port: PORT,
  });
});

module.exports = app;
