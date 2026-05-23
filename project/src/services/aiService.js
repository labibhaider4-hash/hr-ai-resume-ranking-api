// src/services/aiService.js
// ─────────────────────────────────────────────────────────────────────────────
//  AI Service — Anthropic Claude Integration
//  Functions: parseResume, rankCandidate, batchRankCandidates
// ─────────────────────────────────────────────────────────────────────────────

const fetch  = require('node-fetch');
const { logger } = require('../middleware/logger');

const ANTHROPIC_API = 'https://api.anthropic.com/v1/messages';
const AI_MODEL      = process.env.AI_MODEL || 'claude-sonnet-4-20250514';

// ── API call helper ───────────────────────────────────────────────────────────

async function callClaude(systemPrompt, userContent, maxTokens = 1500) {
  const response = await fetch(ANTHROPIC_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': process.env.ANTHROPIC_API_KEY,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: AI_MODEL,
      max_tokens: maxTokens,
      system: systemPrompt,
      messages: [{ role: 'user', content: userContent }],
    }),
  });

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Claude API error ${response.status}: ${err}`);
  }

  const data = await response.json();
  return data.content.map(b => b.text || '').join('');
}

// ── Resume parsing ────────────────────────────────────────────────────────────

const RESUME_PARSE_SYSTEM = `You are an expert HR data extractor specialising in resume analysis.
Your output is ALWAYS valid JSON and nothing else — no markdown fences, no commentary.
Extract structured information with high precision. For unknown fields output null or [].`;

async function parseResume(resumeText) {
  const prompt = `Analyse the following resume and return a JSON object with EXACTLY this schema:

{
  "full_name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "linkedin_url": "string or null",
  "github_url": "string or null",
  "portfolio_url": "string or null",
  "summary": "2-sentence professional summary you write",
  "years_experience": number,
  "education_level": "high_school|associate|bachelor|master|phd|other",
  "skills": [
    { "name": "string", "category": "string", "proficiency": "beginner|intermediate|advanced|expert", "years": number or null }
  ],
  "experience": [
    { "title": "string", "company": "string", "start_year": number, "end_year": number or null, "is_current": boolean, "description": "string", "technologies": ["string"] }
  ],
  "education": [
    { "degree": "string", "field": "string", "institution": "string", "graduation_year": number or null, "gpa": number or null }
  ],
  "certifications": [
    { "name": "string", "issuer": "string", "year": number or null }
  ],
  "languages": ["string"],
  "key_achievements": ["string"],
  "red_flags": ["any concerns like employment gaps > 1 year, frequent job-hopping, etc."]
}

RESUME TEXT:
${resumeText}`;

  logger.info('AI: Parsing resume', { textLength: resumeText.length });
  const raw = await callClaude(RESUME_PARSE_SYSTEM, prompt, 2000);

  try {
    return JSON.parse(raw.replace(/```json|```/g, '').trim());
  } catch {
    logger.error('AI: Failed to parse JSON from resume extraction', { raw });
    throw new Error('AI returned malformed JSON for resume parse');
  }
}

// ── Candidate ranking ─────────────────────────────────────────────────────────

const RANK_SYSTEM = `You are a senior technical recruiter with 15+ years experience.
Score candidates objectively against job requirements on a 0-100 scale.
Return ONLY valid JSON. Be precise, fair, and explain your reasoning.`;

async function rankCandidateForJob(parsedResume, jobPosting) {
  const prompt = `Score this candidate against the job posting. Return JSON with EXACTLY this schema:

{
  "overall_score": number (0-100),
  "skill_score": number (0-100),
  "experience_score": number (0-100),
  "education_score": number (0-100),
  "keyword_score": number (0-100),
  "score_breakdown": {
    "matched_required_skills": ["string"],
    "missing_required_skills": ["string"],
    "matched_preferred_skills": ["string"],
    "experience_fit": "string",
    "education_fit": "string",
    "strengths": ["string"],
    "weaknesses": ["string"]
  },
  "recommendation": "string (3-4 sentences explaining fit, strengths, weaknesses, and hiring recommendation)",
  "interview_questions": ["3 tailored technical/behavioral questions to ask this candidate"]
}

Scoring guide:
- overall_score = (skill_score * 0.40) + (experience_score * 0.30) + (education_score * 0.15) + (keyword_score * 0.15)
- skill_score: % of required skills matched, bonus for preferred skills
- experience_score: years vs required, industry relevance, title progression
- education_score: degree level vs requirement, field relevance
- keyword_score: NLP keyword overlap with job description

JOB POSTING:
${JSON.stringify(jobPosting, null, 2)}

CANDIDATE PARSED RESUME:
${JSON.stringify(parsedResume, null, 2)}`;

  logger.info('AI: Ranking candidate', {
    candidate: parsedResume.full_name,
    job: jobPosting.title
  });

  const raw = await callClaude(RANK_SYSTEM, prompt, 1500);

  try {
    return JSON.parse(raw.replace(/```json|```/g, '').trim());
  } catch {
    logger.error('AI: Failed to parse JSON from ranking', { raw });
    throw new Error('AI returned malformed JSON for candidate ranking');
  }
}

// ── Batch ranking ─────────────────────────────────────────────────────────────
//  Ranks multiple candidates for one job and sorts them by overall_score desc.

async function batchRankCandidates(candidates, jobPosting) {
  const results = [];

  for (const candidate of candidates) {
    try {
      const ranking = await rankCandidateForJob(candidate.parsedResume, jobPosting);
      results.push({
        candidate_id:   candidate.id,
        candidate_name: candidate.parsedResume?.full_name || candidate.name,
        ...ranking,
      });
    } catch (err) {
      logger.error('AI: Error ranking candidate', { candidate_id: candidate.id, error: err.message });
      results.push({
        candidate_id:   candidate.id,
        candidate_name: candidate.name,
        overall_score:  0,
        error:          err.message,
      });
    }
  }

  // Sort by overall_score descending and add rank positions
  return results
    .sort((a, b) => b.overall_score - a.overall_score)
    .map((r, i) => ({ ...r, rank: i + 1 }));
}

// ── Skill extraction from free text ──────────────────────────────────────────

async function extractSkillsFromText(text) {
  const prompt = `Extract all technical and professional skills from this text.
Return JSON array only: [{"name": "string", "category": "programming|framework|cloud|database|devops|soft_skill|domain|language|tool|other", "confidence": 0.0-1.0}]

TEXT: ${text.slice(0, 3000)}`;

  const raw = await callClaude(
    'Extract skills from text. Return only a JSON array.',
    prompt,
    800
  );

  try {
    return JSON.parse(raw.replace(/```json|```/g, '').trim());
  } catch {
    return [];
  }
}

module.exports = {
  parseResume,
  rankCandidateForJob,
  batchRankCandidates,
  extractSkillsFromText,
};
