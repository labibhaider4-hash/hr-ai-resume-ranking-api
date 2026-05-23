// src/database/schema.js
// ─────────────────────────────────────────────────────────────────────────────
//  Database Schema — SQLite via better-sqlite3
//  Tables: users, candidates, job_postings, resumes, skills,
//          candidate_skills, ranking_results, api_logs
// ─────────────────────────────────────────────────────────────────────────────

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const DB_PATH = process.env.DB_PATH || './data/hr_system.db';

function initDatabase() {
  // Ensure data directory exists
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    -- ── USERS (HR staff / API consumers) ──────────────────────────────────
    CREATE TABLE IF NOT EXISTS users (
      id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      email       TEXT UNIQUE NOT NULL,
      password    TEXT NOT NULL,
      name        TEXT NOT NULL,
      role        TEXT NOT NULL DEFAULT 'recruiter'
                    CHECK(role IN ('admin','recruiter','viewer')),
      api_key     TEXT UNIQUE,
      is_active   INTEGER NOT NULL DEFAULT 1,
      created_at  TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── CANDIDATES ────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS candidates (
      id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      first_name      TEXT NOT NULL,
      last_name       TEXT NOT NULL,
      email           TEXT UNIQUE NOT NULL,
      phone           TEXT,
      location        TEXT,
      linkedin_url    TEXT,
      github_url      TEXT,
      portfolio_url   TEXT,
      years_experience REAL DEFAULT 0,
      education_level TEXT CHECK(education_level IN
                        ('high_school','associate','bachelor','master','phd','other')),
      status          TEXT NOT NULL DEFAULT 'active'
                        CHECK(status IN ('active','hired','rejected','archived')),
      created_at      TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── JOB POSTINGS ──────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS job_postings (
      id                  TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      title               TEXT NOT NULL,
      department          TEXT,
      location            TEXT,
      employment_type     TEXT CHECK(employment_type IN
                            ('full_time','part_time','contract','internship','remote')),
      description         TEXT NOT NULL,
      requirements        TEXT NOT NULL,
      nice_to_have        TEXT,
      salary_min          REAL,
      salary_max          REAL,
      required_skills     TEXT NOT NULL DEFAULT '[]',   -- JSON array
      preferred_skills    TEXT NOT NULL DEFAULT '[]',   -- JSON array
      min_experience_yrs  REAL DEFAULT 0,
      education_required  TEXT,
      status              TEXT NOT NULL DEFAULT 'open'
                            CHECK(status IN ('draft','open','closed','paused')),
      created_by          TEXT REFERENCES users(id),
      created_at          TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── RESUMES ───────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS resumes (
      id                    TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      candidate_id          TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
      filename              TEXT NOT NULL,
      file_path             TEXT NOT NULL,
      file_type             TEXT NOT NULL CHECK(file_type IN ('pdf','docx','txt')),
      file_size_bytes       INTEGER,
      raw_text              TEXT,           -- extracted full text
      preprocessed_text     TEXT,           -- cleaned/normalized text
      ai_parsed_data        TEXT,           -- JSON: AI extraction result
      extracted_skills      TEXT DEFAULT '[]',  -- JSON array of skills
      extracted_experience  TEXT DEFAULT '[]',  -- JSON array of {role, company, years, description}
      extracted_education   TEXT DEFAULT '[]',  -- JSON array of {degree, institution, year}
      extracted_certifications TEXT DEFAULT '[]',
      summary               TEXT,           -- AI-generated 2-sentence summary
      parse_status          TEXT NOT NULL DEFAULT 'pending'
                              CHECK(parse_status IN ('pending','processing','completed','failed')),
      parse_error           TEXT,
      uploaded_by           TEXT REFERENCES users(id),
      created_at            TEXT NOT NULL DEFAULT (datetime('now')),
      updated_at            TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── SKILLS TAXONOMY ───────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS skills (
      id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      name        TEXT UNIQUE NOT NULL,
      category    TEXT CHECK(category IN
                    ('programming','framework','cloud','database','devops',
                     'soft_skill','domain','language','tool','other')),
      aliases     TEXT DEFAULT '[]',  -- JSON array of alternate names
      created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── CANDIDATE ↔ SKILLS (many-to-many) ────────────────────────────────
    CREATE TABLE IF NOT EXISTS candidate_skills (
      id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      candidate_id  TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
      skill_id      TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
      resume_id     TEXT REFERENCES resumes(id) ON DELETE CASCADE,
      proficiency   TEXT CHECK(proficiency IN ('beginner','intermediate','advanced','expert')),
      years         REAL,
      UNIQUE(candidate_id, skill_id)
    );

    -- ── RANKING RESULTS ───────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS ranking_results (
      id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      job_id          TEXT NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
      candidate_id    TEXT NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
      resume_id       TEXT REFERENCES resumes(id),
      overall_score   REAL NOT NULL DEFAULT 0 CHECK(overall_score BETWEEN 0 AND 100),
      skill_score     REAL DEFAULT 0,
      experience_score REAL DEFAULT 0,
      education_score REAL DEFAULT 0,
      keyword_score   REAL DEFAULT 0,
      score_breakdown TEXT DEFAULT '{}',  -- JSON: detailed sub-scores
      ai_recommendation TEXT,             -- AI narrative explanation
      rank_position   INTEGER,
      ranked_by       TEXT REFERENCES users(id),
      created_at      TEXT NOT NULL DEFAULT (datetime('now')),
      UNIQUE(job_id, candidate_id)
    );

    -- ── API REQUEST LOG ───────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS api_logs (
      id            TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
      user_id       TEXT REFERENCES users(id),
      method        TEXT NOT NULL,
      endpoint      TEXT NOT NULL,
      status_code   INTEGER,
      request_body  TEXT,
      response_ms   INTEGER,
      ip_address    TEXT,
      user_agent    TEXT,
      error_message TEXT,
      created_at    TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- ── INDEXES ───────────────────────────────────────────────────────────
    CREATE INDEX IF NOT EXISTS idx_resumes_candidate ON resumes(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_resumes_status    ON resumes(parse_status);
    CREATE INDEX IF NOT EXISTS idx_ranking_job       ON ranking_results(job_id);
    CREATE INDEX IF NOT EXISTS idx_ranking_score     ON ranking_results(overall_score DESC);
    CREATE INDEX IF NOT EXISTS idx_candidate_skills  ON candidate_skills(candidate_id);
    CREATE INDEX IF NOT EXISTS idx_logs_user         ON api_logs(user_id);
    CREATE INDEX IF NOT EXISTS idx_logs_created      ON api_logs(created_at);
  `);

  console.log('✅  Database initialised at', DB_PATH);
  return db;
}

module.exports = { initDatabase };
