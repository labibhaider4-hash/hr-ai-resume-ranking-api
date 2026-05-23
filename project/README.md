# HR AI API
**AI-Powered Resume Parsing & Candidate Ranking System**

---

## Overview

A production-ready REST API that uses Anthropic Claude to automatically:
- Extract structured data from PDF/DOCX/TXT resumes
- Rank candidates against job postings with explainable AI scores
- Maintain a full candidate + skills database
- Log all API activity with JWT / API-key authentication

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Express API                          │
│  /auth   /candidates   /jobs   /resumes   /ranking          │
└────────────┬────────────────────────────┬───────────────────┘
             │                            │
     ┌───────▼────────┐          ┌────────▼────────┐
     │  SQLite (WAL)  │          │  Anthropic API  │
     │  8 tables      │          │  claude-sonnet  │
     └────────────────┘          └─────────────────┘
             │
     ┌───────▼────────┐
     │  NLP Pipeline  │
     │  pdf-parse     │
     │  mammoth       │
     │  text cleaning │
     └────────────────┘
```

---

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY and JWT_SECRET

# 3. Initialise and seed database
npm run seed

# 4. Start the server
npm run dev          # development (nodemon)
npm start            # production
```

---

## Database Schema

| Table               | Purpose                                      |
|---------------------|----------------------------------------------|
| `users`             | HR staff accounts with roles & API keys      |
| `candidates`        | Candidate profiles                           |
| `job_postings`      | Open/closed job listings                     |
| `resumes`           | File references + AI-extracted data          |
| `skills`            | Global skills taxonomy with aliases          |
| `candidate_skills`  | Candidate ↔ skill many-to-many               |
| `ranking_results`   | AI scores per candidate–job pair             |
| `api_logs`          | Full audit trail of every request            |

---

## API Endpoints

### Authentication

| Method | Endpoint            | Description              | Auth |
|--------|---------------------|--------------------------|------|
| POST   | `/auth/register`    | Create account           | —    |
| POST   | `/auth/login`       | Get JWT token            | —    |
| GET    | `/auth/me`          | Current user info        | ✓    |
| POST   | `/auth/rotate-key`  | Regenerate API key       | ✓    |

**Auth methods:**
- `Authorization: Bearer <jwt_token>`
- `X-API-Key: <api_key>`

---

### Candidates

| Method | Endpoint              | Description                    |
|--------|-----------------------|--------------------------------|
| GET    | `/candidates`         | List (search with `?q=name`)   |
| GET    | `/candidates/:id`     | Profile + skills + resumes     |
| POST   | `/candidates`         | Create candidate               |
| PATCH  | `/candidates/:id`     | Update fields                  |
| DELETE | `/candidates/:id`     | Delete (admin only)            |

**POST /candidates — Request:**
```json
{
  "first_name": "Alice",
  "last_name": "Chen",
  "email": "alice@example.com",
  "phone": "+1-555-0100",
  "location": "San Francisco, CA"
}
```

---

### Job Postings

| Method | Endpoint     | Description                        |
|--------|--------------|------------------------------------|
| GET    | `/jobs`      | List (`?status=open&department=Eng`)|
| GET    | `/jobs/:id`  | Full posting + applicant count     |
| POST   | `/jobs`      | Create posting                     |
| PATCH  | `/jobs/:id`  | Update / change status             |
| DELETE | `/jobs/:id`  | Delete (admin only)                |

**POST /jobs — Request:**
```json
{
  "title": "Senior Backend Engineer",
  "department": "Engineering",
  "location": "Remote",
  "employment_type": "full_time",
  "description": "Build our core services...",
  "requirements": "5+ years Python, strong API design...",
  "required_skills": ["Python", "PostgreSQL", "Docker"],
  "preferred_skills": ["Go", "Kubernetes", "AWS"],
  "min_experience_yrs": 5,
  "salary_min": 130000,
  "salary_max": 170000
}
```

---

### Resume Upload & Parsing

| Method | Endpoint                       | Description                      |
|--------|--------------------------------|----------------------------------|
| POST   | `/resumes/upload`              | Upload file → trigger AI parse   |
| GET    | `/resumes/:id`                 | Resume + all AI-extracted data   |
| GET    | `/resumes/candidate/:cid`      | All resumes for a candidate      |
| POST   | `/resumes/:id/reparse`         | Re-run AI extraction             |
| DELETE | `/resumes/:id`                 | Delete resume + file             |

**POST /resumes/upload — multipart/form-data:**
```
Content-Type: multipart/form-data
Field: resume   (file — PDF, DOCX, or TXT, max 10MB)
Field: candidate_id   (UUID)
```

**Response (202 Accepted — parsing async):**
```json
{
  "message": "Resume uploaded. AI parsing in progress.",
  "resume_id": "abc123",
  "status": "processing"
}
```

**GET /resumes/:id — Response (after parse completes):**
```json
{
  "resume": {
    "id": "abc123",
    "parse_status": "completed",
    "summary": "Experienced full-stack engineer with 7 years...",
    "ai_parsed_data": {
      "full_name": "Alice Chen",
      "years_experience": 7,
      "education_level": "master",
      "skills": [
        { "name": "Python", "category": "programming", "proficiency": "expert", "years": 6 }
      ],
      "experience": [
        {
          "title": "Senior Engineer",
          "company": "TechCorp",
          "start_year": 2019,
          "end_year": null,
          "is_current": true,
          "technologies": ["Python", "FastAPI", "PostgreSQL"]
        }
      ],
      "education": [
        { "degree": "Master of Science", "field": "Computer Science", "institution": "Stanford University", "graduation_year": 2017 }
      ]
    }
  }
}
```

---

### Candidate Ranking (AI)

| Method | Endpoint                                      | Description                   |
|--------|-----------------------------------------------|-------------------------------|
| POST   | `/ranking/job/:jobId/rank-candidate/:cid`     | Rank one candidate            |
| POST   | `/ranking/job/:jobId/rank-all`                | Rank all / subset             |
| GET    | `/ranking/job/:jobId/results`                 | Leaderboard (`?min_score=70`) |
| GET    | `/ranking/job/:jobId/candidate/:cid`          | Specific result               |

**POST /ranking/job/:jobId/rank-candidate/:cid — Response:**
```json
{
  "job": { "id": "...", "title": "Senior Backend Engineer" },
  "candidate": { "id": "...", "name": "Alice Chen", "email": "alice@example.com" },
  "ranking": {
    "overall_score": 87.5,
    "skill_score": 92,
    "experience_score": 85,
    "education_score": 80,
    "keyword_score": 88,
    "score_breakdown": {
      "matched_required_skills": ["Python", "PostgreSQL", "Docker"],
      "missing_required_skills": [],
      "matched_preferred_skills": ["AWS"],
      "strengths": ["7 years experience exceeds requirement", "Expert Python proficiency"],
      "weaknesses": ["No Kubernetes experience"]
    },
    "recommendation": "Alice is an excellent match for this role...",
    "interview_questions": [
      "Describe a high-traffic API you've designed in Python...",
      "How do you approach database performance tuning?",
      "Tell me about a project where you had to scale infrastructure..."
    ]
  }
}
```

---

## AI / NLP Workflow

```
File Upload
    │
    ▼
Text Extraction          ← pdf-parse | mammoth | fs.readFile
    │
    ▼
NLP Pre-processing       ← clean whitespace, normalise encoding,
    │                       detect sections, extract contact info,
    │                       estimate years of experience
    ▼
Claude Resume Parse      ← Structured JSON extraction:
    │                       skills, experience, education,
    │                       certifications, summary, red flags
    ▼
Skill Taxonomy Sync      ← Upsert into skills + candidate_skills tables
    │
    ▼
[On Rank Request]
    │
    ▼
Claude Candidate Rank    ← Score breakdown (skill 40%, exp 30%,
    │                       education 15%, keyword 15%)
    │                       + recommendation + interview questions
    ▼
Persist to DB            ← ranking_results table
```

---

## Scoring Model

| Component         | Weight | How Calculated                                      |
|-------------------|--------|-----------------------------------------------------|
| Skill Match       | 40%    | Required skills covered (bonus for preferred)       |
| Experience        | 30%    | Years vs requirement, seniority progression         |
| Education         | 15%    | Degree level vs requirement, field relevance        |
| Keyword Overlap   | 15%    | NLP keyword match between resume and JD             |

`overall_score = skill×0.40 + experience×0.30 + education×0.15 + keyword×0.15`

---

## Authentication & Security

- **JWT** (24h expiry) or **API keys** (header `X-API-Key`)  
- **Roles**: `admin` > `recruiter` > `viewer`  
- **Rate limiting**: 100 req / 15 min per IP  
- **Helmet.js**: HTTP security headers  
- **Input validation** on all endpoints  
- **Audit log**: every request → `api_logs` table  

---

## File Support

| Format | Parser       | Max Size |
|--------|--------------|----------|
| PDF    | pdf-parse    | 10 MB    |
| DOCX   | mammoth      | 10 MB    |
| TXT    | Node fs      | 10 MB    |

---

## Environment Variables

| Variable                    | Default                | Description                |
|-----------------------------|------------------------|----------------------------|
| `PORT`                      | `3000`                 | Server port                |
| `ANTHROPIC_API_KEY`         | —                      | **Required**               |
| `JWT_SECRET`                | —                      | **Required in production** |
| `JWT_EXPIRES_IN`            | `24h`                  | Token TTL                  |
| `DB_PATH`                   | `./data/hr_system.db`  | SQLite file path           |
| `UPLOAD_DIR`                | `./uploads`            | File storage directory     |
| `MAX_FILE_SIZE_MB`          | `10`                   | Upload size limit          |
| `RATE_LIMIT_MAX_REQUESTS`   | `100`                  | Requests per window        |
| `RATE_LIMIT_WINDOW_MS`      | `900000`               | Window (15 min)            |
| `LOG_LEVEL`                 | `info`                 | winston log level          |

---

## Deployment

### Docker (recommended)
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

### Fly.io / Railway / Render
Set environment variables via dashboard. Mount a persistent volume at `/app/data` for SQLite and `/app/uploads` for files.

---

## Integration Examples

### cURL — Upload resume
```bash
curl -X POST http://localhost:3000/resumes/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "resume=@alice_cv.pdf" \
  -F "candidate_id=CANDIDATE_UUID"
```

### cURL — Rank all candidates for a job
```bash
curl -X POST http://localhost:3000/ranking/job/JOB_UUID/rank-all \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

### JavaScript — Get leaderboard
```javascript
const res = await fetch(`/ranking/job/${jobId}/results?min_score=70&limit=10`, {
  headers: { 'X-API-Key': 'sk-your-key-here' }
});
const { results } = await res.json();
```
