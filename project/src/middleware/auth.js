// src/middleware/auth.js
// ─────────────────────────────────────────────────────────────────────────────
//  Authentication Middleware
//  Supports: Bearer JWT tokens  |  API key (X-API-Key header)
// ─────────────────────────────────────────────────────────────────────────────

const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');

const JWT_SECRET  = process.env.JWT_SECRET  || 'change_me_in_production';
const JWT_EXPIRES = process.env.JWT_EXPIRES_IN || '24h';

// ── Token generation ──────────────────────────────────────────────────────────
function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, role: user.role },
    JWT_SECRET,
    { expiresIn: JWT_EXPIRES }
  );
}

// ── Core auth middleware ──────────────────────────────────────────────────────
function authenticate(db) {
  return (req, res, next) => {
    // 1. Try Bearer token
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      const token = authHeader.slice(7);
      try {
        const payload = jwt.verify(token, JWT_SECRET);
        const user = db.prepare(
          'SELECT id, email, name, role, is_active FROM users WHERE id = ?'
        ).get(payload.id);

        if (!user || !user.is_active)
          return res.status(401).json({ error: 'Account inactive or not found' });

        req.user = user;
        return next();
      } catch {
        return res.status(401).json({ error: 'Invalid or expired token' });
      }
    }

    // 2. Try API key
    const apiKey = req.headers['x-api-key'];
    if (apiKey) {
      const user = db.prepare(
        'SELECT id, email, name, role, is_active FROM users WHERE api_key = ?'
      ).get(apiKey);

      if (!user || !user.is_active)
        return res.status(401).json({ error: 'Invalid API key' });

      req.user = user;
      return next();
    }

    return res.status(401).json({ error: 'Authentication required' });
  };
}

// ── Role-based access guard ───────────────────────────────────────────────────
function requireRole(...roles) {
  return (req, res, next) => {
    if (!req.user) return res.status(401).json({ error: 'Not authenticated' });
    if (!roles.includes(req.user.role))
      return res.status(403).json({
        error: `Requires role: ${roles.join(' or ')}. You have: ${req.user.role}`
      });
    next();
  };
}

// ── Auth route handlers ───────────────────────────────────────────────────────
function createAuthRoutes(db) {
  const router = require('express').Router();

  /**
   * POST /auth/register
   * Body: { email, password, name, role? }
   */
  router.post('/register', (req, res) => {
    const { email, password, name, role = 'recruiter' } = req.body;
    if (!email || !password || !name)
      return res.status(400).json({ error: 'email, password, name required' });
    if (password.length < 8)
      return res.status(400).json({ error: 'Password must be at least 8 characters' });

    const existing = db.prepare('SELECT id FROM users WHERE email = ?').get(email);
    if (existing) return res.status(409).json({ error: 'Email already registered' });

    const id      = uuidv4();
    const hashed  = bcrypt.hashSync(password, 12);
    const api_key = 'sk-' + uuidv4().replace(/-/g, '');

    db.prepare(
      `INSERT INTO users (id, email, password, name, role, api_key)
       VALUES (?, ?, ?, ?, ?, ?)`
    ).run(id, email, hashed, name, role, api_key);

    const user = db.prepare(
      'SELECT id, email, name, role FROM users WHERE id = ?'
    ).get(id);

    res.status(201).json({
      message: 'Account created',
      user,
      token: generateToken(user),
      api_key
    });
  });

  /**
   * POST /auth/login
   * Body: { email, password }
   */
  router.post('/login', (req, res) => {
    const { email, password } = req.body;
    if (!email || !password)
      return res.status(400).json({ error: 'email and password required' });

    const user = db.prepare('SELECT * FROM users WHERE email = ?').get(email);
    if (!user || !bcrypt.compareSync(password, user.password))
      return res.status(401).json({ error: 'Invalid credentials' });
    if (!user.is_active)
      return res.status(403).json({ error: 'Account is disabled' });

    res.json({
      message: 'Login successful',
      token: generateToken(user),
      user: { id: user.id, email: user.email, name: user.name, role: user.role }
    });
  });

  /**
   * GET /auth/me
   */
  router.get('/me', authenticate(db), (req, res) => {
    res.json({ user: req.user });
  });

  /**
   * POST /auth/rotate-key  — regenerate API key
   */
  router.post('/rotate-key', authenticate(db), (req, res) => {
    const newKey = 'sk-' + uuidv4().replace(/-/g, '');
    db.prepare('UPDATE users SET api_key = ? WHERE id = ?').run(newKey, req.user.id);
    res.json({ message: 'API key rotated', api_key: newKey });
  });

  return router;
}

module.exports = { authenticate, requireRole, generateToken, createAuthRoutes };
