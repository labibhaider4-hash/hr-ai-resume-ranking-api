// src/routes/jobs.js — CRUD for job postings
const express = require('express');
const { v4: uuidv4 } = require('uuid');
const { authenticate, requireRole } = require('../middleware/auth');

module.exports = function createJobRoutes(db) {
  const router = express.Router();
  const auth   = authenticate(db);

  function parseJob(job) {
    if (!job) return null;
    try { job.required_skills  = JSON.parse(job.required_skills); } catch(_) {}
    try { job.preferred_skills = JSON.parse(job.preferred_skills); } catch(_) {}
    return job;
  }

  // GET /jobs
  router.get('/', auth, (req, res) => {
    const { status, department, q, limit = 20, offset = 0 } = req.query;
    let sql    = 'SELECT * FROM job_postings WHERE 1=1';
    const params = [];

    if (status)     { sql += ' AND status = ?';                    params.push(status); }
    if (department) { sql += ' AND department = ?';                params.push(department); }
    if (q)          { sql += ' AND title LIKE ?';                  params.push(`%${q}%`); }
    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(Number(limit), Number(offset));

    const jobs = db.prepare(sql).all(...params).map(parseJob);
    const total = db.prepare('SELECT COUNT(*) as n FROM job_postings').get().n;
    res.json({ total, count: jobs.length, jobs });
  });

  // GET /jobs/:id
  router.get('/:id', auth, (req, res) => {
    const job = parseJob(db.prepare('SELECT * FROM job_postings WHERE id = ?').get(req.params.id));
    if (!job) return res.status(404).json({ error: 'Job not found' });

    const applicantCount = db.prepare(
      'SELECT COUNT(*) as n FROM ranking_results WHERE job_id = ?'
    ).get(req.params.id)?.n || 0;

    res.json({ job: { ...job, applicant_count: applicantCount } });
  });

  // POST /jobs
  router.post('/', auth, requireRole('admin', 'recruiter'), (req, res) => {
    const { title, department, location, employment_type, description, requirements,
            nice_to_have, salary_min, salary_max, required_skills, preferred_skills,
            min_experience_yrs, education_required } = req.body;

    if (!title || !description || !requirements)
      return res.status(400).json({ error: 'title, description, requirements required' });

    const id = uuidv4();
    db.prepare(`
      INSERT INTO job_postings
        (id, title, department, location, employment_type, description, requirements,
         nice_to_have, salary_min, salary_max, required_skills, preferred_skills,
         min_experience_yrs, education_required, created_by)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`
    ).run(
      id, title, department||null, location||null, employment_type||'full_time',
      description, requirements, nice_to_have||null, salary_min||null, salary_max||null,
      JSON.stringify(required_skills || []), JSON.stringify(preferred_skills || []),
      min_experience_yrs||0, education_required||null, req.user.id
    );

    res.status(201).json({ message: 'Job posting created', job: parseJob(db.prepare('SELECT * FROM job_postings WHERE id = ?').get(id)) });
  });

  // PATCH /jobs/:id
  router.patch('/:id', auth, requireRole('admin', 'recruiter'), (req, res) => {
    const allowed = ['title','department','location','employment_type','description',
                     'requirements','nice_to_have','salary_min','salary_max',
                     'required_skills','preferred_skills','min_experience_yrs',
                     'education_required','status'];
    const body = req.body;

    if (body.required_skills)  body.required_skills  = JSON.stringify(body.required_skills);
    if (body.preferred_skills) body.preferred_skills = JSON.stringify(body.preferred_skills);

    const updates = Object.entries(body).filter(([k]) => allowed.includes(k));
    if (!updates.length) return res.status(400).json({ error: 'No valid fields' });

    const setClauses = updates.map(([k]) => `${k} = ?`).join(', ');
    db.prepare(`UPDATE job_postings SET ${setClauses}, updated_at = datetime('now') WHERE id = ?`)
      .run(...updates.map(([,v]) => v), req.params.id);

    res.json({ job: parseJob(db.prepare('SELECT * FROM job_postings WHERE id = ?').get(req.params.id)) });
  });

  // DELETE /jobs/:id
  router.delete('/:id', auth, requireRole('admin'), (req, res) => {
    const job = db.prepare('SELECT id FROM job_postings WHERE id = ?').get(req.params.id);
    if (!job) return res.status(404).json({ error: 'Job not found' });
    db.prepare('DELETE FROM job_postings WHERE id = ?').run(req.params.id);
    res.json({ message: 'Job deleted' });
  });

  return router;
};
