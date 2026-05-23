// src/routes/resumes.js
// ─────────────────────────────────────────────────────────────────────────────
//  Resume API Routes
//  POST   /resumes/upload           — upload & trigger AI parsing
//  GET    /resumes/:id              — get resume with parsed data
//  GET    /resumes/candidate/:cid   — all resumes for a candidate
//  DELETE /resumes/:id              — remove resume
//  POST   /resumes/:id/reparse      — re-trigger AI parsing
// ─────────────────────────────────────────────────────────────────────────────

const express  = require('express');
const multer   = require('multer');
const path     = require('path');
const fs       = require('fs');
const { v4: uuidv4 } = require('uuid');
const { authenticate, requireRole } = require('../middleware/auth');
const { preprocessResume }          = require('../services/nlpService');
const { parseResume }               = require('../services/aiService');
const { logger }                    = require('../middleware/logger');

const UPLOAD_DIR     = process.env.UPLOAD_DIR    || './uploads';
const MAX_SIZE_BYTES = (parseInt(process.env.MAX_FILE_SIZE_MB) || 10) * 1024 * 1024;
const ALLOWED_EXTS   = new Set(['pdf', 'docx', 'txt']);

// Ensure upload dir exists
if (!fs.existsSync(UPLOAD_DIR)) fs.mkdirSync(UPLOAD_DIR, { recursive: true });

// ── Multer config ─────────────────────────────────────────────────────────────
const storage = multer.diskStorage({
  destination: UPLOAD_DIR,
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).slice(1).toLowerCase();
    cb(null, `${uuidv4()}.${ext}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_SIZE_BYTES },
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname).slice(1).toLowerCase();
    if (ALLOWED_EXTS.has(ext)) return cb(null, true);
    cb(new Error(`Only ${[...ALLOWED_EXTS].join(', ')} files are allowed`));
  },
});

module.exports = function createResumeRoutes(db) {
  const router = express.Router();
  const auth   = authenticate(db);

  // ── POST /resumes/upload ────────────────────────────────────────────────────
  router.post('/upload', auth, upload.single('resume'), async (req, res) => {
    const { candidate_id } = req.body;

    if (!req.file)        return res.status(400).json({ error: 'No file uploaded' });
    if (!candidate_id)    return res.status(400).json({ error: 'candidate_id is required' });

    const candidate = db.prepare('SELECT id FROM candidates WHERE id = ?').get(candidate_id);
    if (!candidate)  return res.status(404).json({ error: 'Candidate not found' });

    const fileType = path.extname(req.file.filename).slice(1).toLowerCase();
    const resumeId = uuidv4();

    // Insert resume record as 'processing'
    db.prepare(`
      INSERT INTO resumes (id, candidate_id, filename, file_path, file_type, file_size_bytes, parse_status, uploaded_by)
      VALUES (?, ?, ?, ?, ?, ?, 'processing', ?)`
    ).run(resumeId, candidate_id, req.file.originalname, req.file.path, fileType, req.file.size, req.user.id);

    res.status(202).json({
      message:   'Resume uploaded. AI parsing in progress.',
      resume_id: resumeId,
      status:    'processing',
    });

    // ── Async AI pipeline (non-blocking) ──────────────────────────────────────
    setImmediate(async () => {
      try {
        logger.info('NLP: Preprocessing resume', { resumeId });
        const nlp = await preprocessResume(req.file.path, fileType);

        logger.info('AI: Parsing resume', { resumeId });
        const aiData = await parseResume(nlp.preprocessedText);

        // Merge NLP contact info if AI missed them
        if (!aiData.email)    aiData.email    = nlp.contactInfo.email;
        if (!aiData.linkedin_url) aiData.linkedin_url = nlp.contactInfo.linkedin;
        if (!aiData.github_url)   aiData.github_url   = nlp.contactInfo.github;
        if (!aiData.years_experience || aiData.years_experience === 0)
          aiData.years_experience = nlp.estimatedYears;

        // Update resume record
        db.prepare(`
          UPDATE resumes SET
            raw_text = ?, preprocessed_text = ?, ai_parsed_data = ?,
            extracted_skills = ?, extracted_experience = ?,
            extracted_education = ?, extracted_certifications = ?,
            summary = ?, parse_status = 'completed', updated_at = datetime('now')
          WHERE id = ?`
        ).run(
          nlp.rawText,
          nlp.preprocessedText,
          JSON.stringify(aiData),
          JSON.stringify(aiData.skills         || []),
          JSON.stringify(aiData.experience      || []),
          JSON.stringify(aiData.education       || []),
          JSON.stringify(aiData.certifications  || []),
          aiData.summary,
          resumeId
        );

        // Update candidate with aggregated info
        db.prepare(`
          UPDATE candidates SET
            years_experience = ?, education_level = ?,
            linkedin_url = ?, github_url = ?,
            updated_at = datetime('now')
          WHERE id = ?`
        ).run(
          aiData.years_experience,
          aiData.education_level,
          aiData.linkedin_url,
          aiData.github_url,
          candidate_id
        );

        // Sync skills to candidate_skills table
        if (Array.isArray(aiData.skills)) {
          for (const skill of aiData.skills) {
            // Find or create skill
            let skillRow = db.prepare('SELECT id FROM skills WHERE LOWER(name) = LOWER(?)').get(skill.name);
            if (!skillRow) {
              const sid = uuidv4();
              db.prepare('INSERT INTO skills (id, name, category) VALUES (?, ?, ?)').run(sid, skill.name, skill.category || 'other');
              skillRow = { id: sid };
            }
            // Upsert candidate_skills
            db.prepare(`
              INSERT INTO candidate_skills (id, candidate_id, skill_id, resume_id, proficiency, years)
              VALUES (?, ?, ?, ?, ?, ?)
              ON CONFLICT(candidate_id, skill_id) DO UPDATE SET
                proficiency = excluded.proficiency, years = excluded.years`
            ).run(uuidv4(), candidate_id, skillRow.id, resumeId, skill.proficiency || null, skill.years || null);
          }
        }

        logger.info('AI: Resume parsing complete', { resumeId, candidate_id });
      } catch (err) {
        logger.error('AI: Resume parsing failed', { resumeId, error: err.message });
        db.prepare(`UPDATE resumes SET parse_status = 'failed', parse_error = ? WHERE id = ?`)
          .run(err.message, resumeId);
      }
    });
  });

  // ── GET /resumes/:id ────────────────────────────────────────────────────────
  router.get('/:id', auth, (req, res) => {
    const resume = db.prepare(`
      SELECT r.*, c.first_name, c.last_name, c.email as candidate_email
      FROM resumes r JOIN candidates c ON r.candidate_id = c.id
      WHERE r.id = ?`
    ).get(req.params.id);

    if (!resume) return res.status(404).json({ error: 'Resume not found' });

    // Parse JSON fields
    for (const field of ['ai_parsed_data','extracted_skills','extracted_experience','extracted_education','extracted_certifications']) {
      if (resume[field]) {
        try { resume[field] = JSON.parse(resume[field]); } catch (_) {}
      }
    }

    res.json({ resume });
  });

  // ── GET /resumes/candidate/:cid ─────────────────────────────────────────────
  router.get('/candidate/:cid', auth, (req, res) => {
    const resumes = db.prepare(`
      SELECT id, filename, file_type, file_size_bytes, parse_status, summary, created_at
      FROM resumes WHERE candidate_id = ? ORDER BY created_at DESC`
    ).all(req.params.cid);

    res.json({ count: resumes.length, resumes });
  });

  // ── POST /resumes/:id/reparse ───────────────────────────────────────────────
  router.post('/:id/reparse', auth, requireRole('admin', 'recruiter'), async (req, res) => {
    const resume = db.prepare('SELECT * FROM resumes WHERE id = ?').get(req.params.id);
    if (!resume) return res.status(404).json({ error: 'Resume not found' });
    if (!fs.existsSync(resume.file_path))
      return res.status(410).json({ error: 'File no longer exists on disk' });

    db.prepare(`UPDATE resumes SET parse_status = 'processing', parse_error = null WHERE id = ?`)
      .run(resume.id);
    res.json({ message: 'Re-parsing triggered', resume_id: resume.id });

    setImmediate(async () => {
      try {
        const nlp    = await preprocessResume(resume.file_path, resume.file_type);
        const aiData = await parseResume(nlp.preprocessedText);
        db.prepare(`
          UPDATE resumes SET
            preprocessed_text = ?, ai_parsed_data = ?,
            extracted_skills = ?, extracted_experience = ?,
            extracted_education = ?, summary = ?,
            parse_status = 'completed', updated_at = datetime('now')
          WHERE id = ?`
        ).run(nlp.preprocessedText, JSON.stringify(aiData),
          JSON.stringify(aiData.skills || []), JSON.stringify(aiData.experience || []),
          JSON.stringify(aiData.education || []), aiData.summary, resume.id);
      } catch (err) {
        db.prepare(`UPDATE resumes SET parse_status = 'failed', parse_error = ? WHERE id = ?`)
          .run(err.message, resume.id);
      }
    });
  });

  // ── DELETE /resumes/:id ─────────────────────────────────────────────────────
  router.delete('/:id', auth, requireRole('admin', 'recruiter'), (req, res) => {
    const resume = db.prepare('SELECT * FROM resumes WHERE id = ?').get(req.params.id);
    if (!resume) return res.status(404).json({ error: 'Resume not found' });

    try { if (fs.existsSync(resume.file_path)) fs.unlinkSync(resume.file_path); } catch (_) {}
    db.prepare('DELETE FROM resumes WHERE id = ?').run(req.params.id);

    res.json({ message: 'Resume deleted' });
  });

  return router;
};
