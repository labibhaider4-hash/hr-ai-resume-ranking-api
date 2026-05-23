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

## Browser Homepage

Open this URL after starting the server:

```text
http://127.0.0.1:5000/
```

The homepage gives a simple demo UI for:

- Register / login
- Create candidate
- Create job
- Upload resume
- Rank candidate
- View API response

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
- `GET /stats`

## Notes

This Python version uses a local heuristic NLP/ranking system so it works without an external AI key. It extracts email, phone, skills, estimated experience, and education keywords from uploaded TXT resumes.

PDF/DOCX files can be uploaded, but this standard-library version only extracts text directly from TXT files. For PDF/DOCX parsing, external libraries such as `pdfplumber`, `PyPDF2`, or `python-docx` can be added later.
