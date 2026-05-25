# Python Version: HR AI Resume Ranking API

This is a Python standard-library version of the project. It does not need Flask, FastAPI, or external packages.

## Documentation

- [Full Project Documentation](PROJECT_DOCUMENTATION.md)
- [API Reference](API_REFERENCE.md)
- [LinkedIn Upload Guide](LINKEDIN_GUIDE.md)

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
- Convert PDF data files into CSV
- Upload CSV candidate/resume data directly and screen up to 1,000,000 rows

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
- `POST /pdf-to-csv` for converting PDF data files to CSV
- `POST /screen-csv` for screening resume/candidate data from a CSV file
- `GET /api/docs` for machine-readable API documentation
- `GET /stats`

## Notes

This Python version uses a local heuristic NLP/ranking system so it works without an external AI key. It extracts email, phone, skills, estimated experience, and education keywords from uploaded TXT, DOCX, and PDF resumes.

DOCX extraction uses Python's built-in ZIP/XML support. PDF extraction uses `pypdf` if installed, with a basic fallback for simple PDFs.

Excel export is generated with Python's built-in ZIP/XML libraries, so no extra Excel package is needed. It creates one row per uploaded resume with extracted skills, score, decision, matched skills, missing skills, recommendation, and any file error.

CSV screening can read columns such as `resume_text`, `skills`, `experience`, `education`, `summary`, `profile`, `candidate`, or `name`. If those exact columns are not present, it combines all row values and screens that text.

## Decision System

- `80+` = SHORTLIST
- `60-79` = REVIEW
- Below `60` = NOT RECOMMENDED
