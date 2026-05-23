# AI-Powered Resume Parsing and Candidate Ranking API

MCA final year project for an AI/NLP-based recruitment support API.

This repository now contains the **Python version** of the project. It uses Python's standard library, SQLite, and a simple local NLP/ranking approach, so it can run without Node.js and without installing Flask/FastAPI.

## Project Overview

The system helps recruiters:

- Register and login
- Add candidates
- Create job postings
- Upload resumes
- Extract useful resume details
- Match candidate skills with job requirements
- Generate candidate ranking scores
- Store API logs and results

## Folder Structure

```text
Final_Submission_Package/
├── project/          # Python API source code
├── report/           # Project report DOCX
├── presentation/     # Final presentation PPTX and previews
└── README_SUBMISSION.txt
```

## Tech Stack

- Python
- SQLite
- Python standard library HTTP server
- Local NLP-style text preprocessing
- Heuristic candidate ranking

## How To Run

Open the project folder:

```bash
cd project
python app.py
```

The API runs at:

```text
http://127.0.0.1:5000
```

Test health:

```text
http://127.0.0.1:5000/health
```

## Main API Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /candidates`
- `GET /candidates`
- `POST /jobs`
- `GET /jobs`
- `POST /resumes/upload`
- `GET /resumes/<resume_id>`
- `POST /ranking/job/<job_id>/rank-candidate/<candidate_id>`
- `GET /stats`

## Important Note

This Python version works locally without an external AI API key. It extracts resume details from TXT resumes and ranks candidates using skill matching, experience matching, education score, and keyword score.

PDF/DOCX upload is accepted, but full PDF/DOCX text extraction would require adding external parser libraries in the future.
