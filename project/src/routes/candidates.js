// src/routes/candidates.js — CRUD for candidates
const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { authenticate, requireRole } = require('../middleware/auth');

module.exports = function createCandidateRoutes(db) {
  const router = express.Router();
  const auth   = authenticate(db);

  // GET /candidates — list with pagination & search
  router.get('/', auth, (req, res) => {
    const { q, status, limit = 20, offset = 0 } = req.query;
    let sql    = 'SELECT * FROM candidates WHERE 1=1';
    const params = [];

    if (q) {
      sql += ' AND (first_name LIKE ? OR last_name LIKE ? OR email LIKE ?)';
      const like = `%${q}%`;
      params.push(like, like, like);
    }
    if (status) { sql += ' AND status = ?'; params.push(status); }
    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(Number(limit), Number(offset));

    const total = db.prepare('SELECT COUNT(*) as n FROM candidates').get().n;
    const candidates = db.prepare(sql).all(...params);

    res.json({ total, count: candidates.length, candidates });
  });

  // GET /candidates/:id — single candidate + skills
  router.get('/:id', auth, (req, res) => {
    const candidate = db.prepare('SELECT * FROM candidates WHERE id = ?').get(req.params.id);
    if (!candidate) return res.status(404).json({ error: 'Candidate not found' });

    const skills = db.prepare(`
      SELECT s.name, s.category, cs.proficiency, cs.years
      FROM candidate_skills cs JOIN skills s ON cs.skill_id = s.id
      WHERE cs.candidate_id = ?`
    ).all(req.params.id);

    const resumes = db.prepare(
      'SELECT id, filename, parse_status, summary, created_at FROM resumes WHERE candidate_id = ? ORDER BY created_at DESC'
    ).all(req.params.id);

    res.json({ candidate: { ...candidate, skills, resumes } });
  });

  // POST /candidates — create
  router.post('/', auth, (req, res) => {
    const { first_name, last_name, email, phone, location, linkedin_url, github_url } = req.body;
    if (!first_name || !last_name || !email)
      return res.status(400).json({ error: 'first_name, last_name, email required' });

    const existing = db.prepare('SELECT id FROM candidates WHERE email = ?').get(email);
    if (existing) return res.status(409).json({ error: 'Email already exists' });

    const id = uuidv4();
    db.prepare(`
      INSERT INTO candidates (id, first_name, last_name, email, phone, location, linkedin_url, github_url)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    ).run(id, first_name, last_name, email, phone || null, location || null, linkedin_url || null, github_url || null);

    res.status(201).json({
      message: 'Candidate created',
      candidate: db.prepare('SELECT * FROM candidates WHERE id = ?').get(id)
    });
  });

  // PATCH /candidates/:id — update
  router.patch('/:id', auth, requireRole('admin', 'recruiter'), (req, res) => {
    const allowed = ['first_name','last_name','phone','location','linkedin_url','github_url','portfolio_url','status'];
    const updates = Object.entries(req.body).filter(([k]) => allowed.includes(k));
    if (!updates.length) return res.status(400).json({ error: 'No valid fields to update' });

    const setClauses = updates.map(([k]) => `${k} = ?`).join(', ');
    db.prepare(`UPDATE candidates SET ${setClauses}, updated_at = datetime('now') WHERE id = ?`)
      .run(...updates.map(([,v]) => v), req.params.id);

    res.json({ candidate: db.prepare('SELECT * FROM candidates WHERE id = ?').get(req.params.id) });
  });

  // DELETE /candidates/:id
  router.delete('/:id', auth, requireRole('admin'), (req, res) => {
    const c = db.prepare('SELECT id FROM candidates WHERE id = ?').get(req.params.id);
    if (!c) return res.status(404).json({ error: 'Candidate not found' });
    db.prepare('DELETE FROM candidates WHERE id = ?').run(req.params.id);
    res.json({ message: 'Candidate deleted' });
  });

  return router;
};
