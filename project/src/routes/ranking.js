// src/routes/ranking.js
// ─────────────────────────────────────────────────────────────────────────────
//  Ranking API Routes
//  POST /ranking/job/:jobId/rank-candidate/:candidateId  — rank one candidate
//  POST /ranking/job/:jobId/rank-all                     — rank all applicants
//  GET  /ranking/job/:jobId/results                      — leaderboard
//  GET  /ranking/job/:jobId/candidate/:cid               — specific result
// ─────────────────────────────────────────────────────────────────────────────

const express  = require('express');
const { v4: uuidv4 } = require('uuid');
const { authenticate, requireRole } = require('../middleware/auth');
const { rankCandidateForJob, batchRankCandidates } = require('../services/aiService');
const { logger } = require('../middleware/logger');

module.exports = function createRankingRoutes(db) {
  const router = express.Router();
  const auth   = authenticate(db);

  // Helper: get job + validate exists
  function getJob(jobId) {
    const job = db.prepare('SELECT * FROM job_postings WHERE id = ?').get(jobId);
    if (!job) return null;
    try { job.required_skills  = JSON.parse(job.required_skills); } catch(_) { job.required_skills = []; }
    try { job.preferred_skills = JSON.parse(job.preferred_skills); } catch(_) { job.preferred_skills = []; }
    return job;
  }

  // Helper: get candidate's latest completed resume + parsed data
  function getCandidateWithResume(candidateId) {
    const candidate = db.prepare('SELECT * FROM candidates WHERE id = ?').get(candidateId);
    if (!candidate) return null;

    const resume = db.prepare(`
      SELECT * FROM resumes
      WHERE candidate_id = ? AND parse_status = 'completed'
      ORDER BY created_at DESC LIMIT 1`
    ).get(candidateId);

    if (!resume) return { ...candidate, parsedResume: null };

    let parsedResume = null;
    try { parsedResume = JSON.parse(resume.ai_parsed_data); } catch (_) {}

    return { ...candidate, resume, parsedResume };
  }

  // ── POST /ranking/job/:jobId/rank-candidate/:candidateId ──────────────────
  /**
   * @swagger
   * Rank a single candidate against a job posting.
   * Returns: score breakdown, recommendation, interview questions.
   */
  router.post(
    '/job/:jobId/rank-candidate/:candidateId',
    auth,
    requireRole('admin', 'recruiter'),
    async (req, res) => {
      const job = getJob(req.params.jobId);
      if (!job) return res.status(404).json({ error: 'Job posting not found' });

      const candidateData = getCandidateWithResume(req.params.candidateId);
      if (!candidateData) return res.status(404).json({ error: 'Candidate not found' });
      if (!candidateData.parsedResume)
        return res.status(422).json({
          error: 'No completed resume parse found for this candidate. Upload and wait for parsing to complete.'
        });

      try {
        const ranking = await rankCandidateForJob(candidateData.parsedResume, job);

        // Upsert ranking_results
        db.prepare(`
          INSERT INTO ranking_results
            (id, job_id, candidate_id, resume_id, overall_score, skill_score,
             experience_score, education_score, keyword_score, score_breakdown,
             ai_recommendation, ranked_by)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
          ON CONFLICT(job_id, candidate_id) DO UPDATE SET
            overall_score     = excluded.overall_score,
            skill_score       = excluded.skill_score,
            experience_score  = excluded.experience_score,
            education_score   = excluded.education_score,
            keyword_score     = excluded.keyword_score,
            score_breakdown   = excluded.score_breakdown,
            ai_recommendation = excluded.ai_recommendation,
            ranked_by         = excluded.ranked_by,
            created_at        = datetime('now')`
        ).run(
          uuidv4(),
          job.id, candidateData.id, candidateData.resume?.id || null,
          ranking.overall_score, ranking.skill_score, ranking.experience_score,
          ranking.education_score, ranking.keyword_score,
          JSON.stringify(ranking.score_breakdown),
          ranking.recommendation,
          req.user.id
        );

        res.json({
          job:       { id: job.id, title: job.title },
          candidate: {
            id:    candidateData.id,
            name:  `${candidateData.first_name} ${candidateData.last_name}`,
            email: candidateData.email,
          },
          ranking,
        });
      } catch (err) {
        logger.error('Ranking error', { error: err.message });
        res.status(500).json({ error: 'AI ranking failed', detail: err.message });
      }
    }
  );

  // ── POST /ranking/job/:jobId/rank-all ─────────────────────────────────────
  /**
   * Rank ALL candidates who have completed resumes and return leaderboard.
   * Optional body: { candidate_ids: ["id1","id2",...] }  — to limit scope
   */
  router.post('/job/:jobId/rank-all', auth, requireRole('admin', 'recruiter'), async (req, res) => {
    const job = getJob(req.params.jobId);
    if (!job) return res.status(404).json({ error: 'Job posting not found' });

    let candidateIds = req.body?.candidate_ids;

    if (!Array.isArray(candidateIds) || candidateIds.length === 0) {
      // All candidates with completed resumes
      const rows = db.prepare(`
        SELECT DISTINCT candidate_id FROM resumes WHERE parse_status = 'completed'
      `).all();
      candidateIds = rows.map(r => r.candidate_id);
    }

    if (candidateIds.length === 0)
      return res.status(422).json({ error: 'No candidates with completed resume parses found' });

    const candidates = candidateIds
      .map(id => getCandidateWithResume(id))
      .filter(c => c && c.parsedResume);

    if (candidates.length === 0)
      return res.status(422).json({ error: 'None of the specified candidates have usable parsed resumes' });

    try {
      const results = await batchRankCandidates(candidates, job);

      // Persist all results
      const upsert = db.prepare(`
        INSERT INTO ranking_results
          (id, job_id, candidate_id, overall_score, skill_score, experience_score,
           education_score, keyword_score, score_breakdown, ai_recommendation, rank_position, ranked_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id, candidate_id) DO UPDATE SET
          overall_score = excluded.overall_score,
          rank_position = excluded.rank_position,
          score_breakdown = excluded.score_breakdown,
          ai_recommendation = excluded.ai_recommendation,
          ranked_by = excluded.ranked_by,
          created_at = datetime('now')`);

      const persistAll = db.transaction(() => {
        for (const r of results) {
          upsert.run(
            uuidv4(), job.id, r.candidate_id,
            r.overall_score, r.skill_score, r.experience_score,
            r.education_score, r.keyword_score,
            JSON.stringify(r.score_breakdown),
            r.recommendation, r.rank, req.user.id
          );
        }
      });
      persistAll();

      res.json({
        job:     { id: job.id, title: job.title },
        ranked:  results.length,
        results: results.map(r => ({
          rank:          r.rank,
          candidate_id:  r.candidate_id,
          candidate_name: r.candidate_name,
          overall_score: r.overall_score,
          skill_score:   r.skill_score,
          experience_score: r.experience_score,
          recommendation: r.recommendation,
          error:         r.error,
        })),
      });
    } catch (err) {
      logger.error('Batch ranking error', { error: err.message });
      res.status(500).json({ error: 'Batch ranking failed', detail: err.message });
    }
  });

  // ── GET /ranking/job/:jobId/results ──────────────────────────────────────
  router.get('/job/:jobId/results', auth, (req, res) => {
    const { limit = 20, offset = 0, min_score } = req.query;

    let query = `
      SELECT rr.*, c.first_name, c.last_name, c.email,
             c.years_experience, c.location
      FROM ranking_results rr
      JOIN candidates c ON rr.candidate_id = c.id
      WHERE rr.job_id = ?`;
    const params = [req.params.jobId];

    if (min_score) { query += ' AND rr.overall_score >= ?'; params.push(Number(min_score)); }
    query += ' ORDER BY rr.overall_score DESC LIMIT ? OFFSET ?';
    params.push(Number(limit), Number(offset));

    const results = db.prepare(query).all(...params);

    for (const r of results) {
      try { r.score_breakdown = JSON.parse(r.score_breakdown); } catch (_) {}
    }

    const total = db.prepare('SELECT COUNT(*) as n FROM ranking_results WHERE job_id = ?').get(req.params.jobId)?.n || 0;

    res.json({ job_id: req.params.jobId, total, results });
  });

  // ── GET /ranking/job/:jobId/candidate/:cid ────────────────────────────────
  router.get('/ranking/job/:jobId/candidate/:cid', auth, (req, res) => {
    const result = db.prepare(`
      SELECT * FROM ranking_results WHERE job_id = ? AND candidate_id = ?`
    ).get(req.params.jobId, req.params.cid);

    if (!result) return res.status(404).json({ error: 'No ranking result found' });

    try { result.score_breakdown = JSON.parse(result.score_breakdown); } catch (_) {}
    res.json({ result });
  });

  return router;
};
