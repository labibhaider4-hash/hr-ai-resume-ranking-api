# Python Version: HR AI Resume Ranking API

This is a Python standard-library version of the project. It does not need Flask, FastAPI, or external packages.

## How To Run

```bash
python app.py
```

Server runs at:

```text
http://127.0.0.1:5000
```

## Simple Browser Demo

Open this URL after starting the server:

```text
http://127.0.0.1:5000/
```

The homepage now shows the simple screening system:

- Tick/select required skills from the checklist
- Add extra required skills if needed
- Upload TXT, DOCX, or PDF resumes
- Screen up to 200 resumes in one batch
- Download the results as an Excel `.xlsx` file

## Test Health

```text
GET http://127.0.0.1:5000/health
```

## Main Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /candidates`
- `GET /candidates`
- `POST /jobs`
- `GET /jobs`
- `POST /resumes/upload`
- `GET /resumes/<resume_id>`
- `POST /ranking/job/<job_id>/rank-candidate/<candidate_id>`
- `POST /screen-resume` for one resume demo
- `POST /screen-batch` for up to 200 resumes and Excel output
- `GET /stats`

## Notes

This Python version uses a local heuristic NLP/ranking system so it works without an external AI key. It extracts email, phone, skills, estimated experience, and education keywords from uploaded TXT, DOCX, and PDF resumes.

DOCX extraction uses Python's built-in ZIP/XML support. PDF extraction uses `pypdf` if installed, with a basic fallback for simple PDFs.

Excel export uses `openpyxl`. It creates one row per uploaded resume with extracted skills, score, decision, matched skills, missing skills, recommendation, and any file error.

## Decision System

- `80+` = SHORTLIST
- `60-79` = REVIEW
- Below `60` = NOT RECOMMENDED
