# HR AI Resume Ranking API - Full Project Documentation

## 1. Project Overview

HR AI Resume Ranking API is a Python-based resume screening system for recruiters and HR teams. The system accepts resumes and candidate data, extracts useful information, compares it with job requirements, ranks candidates, and exports results in Excel or CSV format.

The project is built as a complete local API and browser demo. It does not require Node.js, Flask, FastAPI, or paid AI APIs. It uses Python standard-library modules for the server, database, parsing, authentication, Excel generation, CSV generation, and file processing.

## 2. Main Objective

The objective is to create an API that processes resumes, extracts key skills, and ranks candidates for jobs using AI/NLP-style logic.

The project fulfills these goals:

- Resume upload and processing
- Skill extraction from resume text
- Candidate ranking based on job requirements
- API endpoints for candidates, jobs, resumes, and ranking
- Authentication and API key support
- PDF, DOCX, TXT, and CSV handling
- Bulk resume screening
- Excel and CSV export
- Professional browser interface
- Local database storage
- API documentation endpoint

## 3. Problem Statement

Recruiters often receive many resumes for one job opening. Manually reading every resume takes time, and shortlisting can become inconsistent. This project helps by automatically reading resume data, finding relevant skills and experience, and producing a ranked output.

The system does not fully replace the recruiter. It helps the recruiter quickly identify strong candidates and review weaker or partial matches.

## 4. Users

The main users are:

- Recruiters
- HR executives
- Placement coordinators
- Small companies screening many resumes
- Students demonstrating an AI/NLP final year project

## 5. Technology Stack

- Language: Python
- Server: Python `http.server`
- Database: SQLite
- Frontend: HTML, CSS, JavaScript
- File formats: TXT, DOCX, PDF, CSV, XLSX
- Authentication: Token and API key
- Output: JSON, CSV, XLSX

The project intentionally avoids heavy frameworks so it can run easily on college laptops and be explained in a presentation.

## 6. Folder Structure

```text
project/
  app.py
  README.md
  PROJECT_DOCUMENTATION.md
  API_REFERENCE.md
  LINKEDIN_GUIDE.md
  start_clean_server.bat
  examples/
    sample_resume.txt
    sample_resume.docx
    sample_candidates.csv
  data/
    hr_python_api.db
  uploads/
```

## 7. How To Run

Open PowerShell and run:

```powershell
cd C:\Users\haide\OneDrive\Documents\fy\Final_Submission_Package\project
.\start_clean_server.bat
```

Then open:

```text
http://127.0.0.1:5000/
```

The batch file stops old servers on port `5000` and starts the correct current version.

## 8. Main Features

### 8.1 Professional Browser UI

The homepage provides a dashboard-style interface with:

- Job title input
- Minimum experience input
- Preferred skills input
- Required skills checklist
- Extra required skills input
- Resume upload
- PDF to CSV converter
- CSV resume screening
- Status panels
- Excel and CSV download buttons

### 8.2 Resume Screening

Supported resume file types:

- TXT
- DOCX
- PDF

The user selects required skills, uploads resumes, and downloads an Excel result.

### 8.3 Bulk Screening

The system supports up to `200` resume files in one batch upload.

For each resume, the output includes:

- File name
- Status
- Email
- Phone
- Extracted skills
- Estimated years of experience
- Education level
- Overall score
- Skill score
- Experience score
- Education score
- Keyword score
- Decision
- Matched required skills
- Missing required skills
- Matched preferred skills
- Recommendation
- Error message if any

### 8.4 CSV Resume Screening

The system can directly screen candidate data from a CSV file. This is useful when candidate details are already stored in spreadsheet format.

Supported useful CSV columns:

- `resume_text`
- `skills`
- `experience`
- `education`
- `summary`
- `profile`
- `candidate`
- `name`

If these columns are not present, the system combines all values in the row and screens that combined text.

The CSV screening limit is `1,000,000` rows.

### 8.5 PDF Data to CSV

The project can accept PDF data files and convert readable PDF text into CSV rows. It attempts to extract real text and filters out internal PDF code such as:

- `%PDF`
- `obj`
- `stream`
- `/Type`
- `/FlateDecode`

If a PDF is scanned as an image and has no readable text layer, OCR would be needed. This project does not include OCR because it was designed to run without external heavy dependencies.

### 8.6 Excel Export

The project creates `.xlsx` files using Python ZIP/XML logic. It does not need `openpyxl`.

This makes the project easier to run on systems where external packages are missing.

### 8.7 Authentication

The API includes recruiter registration and login.

Supported authentication methods:

- Bearer token
- `X-API-Key` header

Public demo routes such as `/screen-batch`, `/screen-csv`, and `/pdf-to-csv` are open so the browser UI is easy to test.

## 9. Ranking Logic

The ranking algorithm is heuristic and explainable.

Scores are calculated from:

- Required skill match
- Preferred skill match
- Years of experience
- Education level
- Keyword match

Overall score formula:

```text
overall =
  skill_score * 0.45 +
  experience_score * 0.30 +
  education_score * 0.15 +
  keyword_score * 0.10
```

Decision rules:

- `80+` = SHORTLIST
- `60-79` = REVIEW
- Below `60` = NOT RECOMMENDED

## 10. Skill Extraction

The system checks resume text against a predefined skill list:

```text
python, javascript, node.js, node, react, sql, sqlite, postgresql,
mongodb, express, html, css, docker, aws, java, c++, git,
rest api, api, machine learning, nlp, flask, fastapi, django
```

Extra required skills can also be typed from the UI.

## 11. Experience Extraction

The project estimates experience using patterns like:

```text
3 years
5+ years
2 yrs
```

It takes the highest detected number as the estimated years of experience.

## 12. Education Detection

The system detects education keywords and maps them to:

- bachelor
- master
- phd
- other

## 13. Contact Extraction

The system extracts:

- Email addresses
- Phone numbers

Regex is used for simple, explainable contact detection.

## 14. Database Design

SQLite is used as the database.

Main tables:

- `users`
- `candidates`
- `job_postings`
- `resumes`
- `ranking_results`
- `api_logs`

### Users Table

Stores recruiter account details, password hash, role, API key, and creation date.

### Candidates Table

Stores candidate profile information such as name, email, phone, location, experience, education, and status.

### Job Postings Table

Stores job details, required skills, preferred skills, minimum experience, and job status.

### Resumes Table

Stores uploaded resume file information, extracted raw text, processed text, parsed JSON data, parse status, and errors.

### Ranking Results Table

Stores the ranking result for a candidate against a job.

### API Logs Table

Stores API method, endpoint, status code, response time, and timestamp.

## 15. API Readiness Features

The project now includes several practical API features:

- CORS headers
- `OPTIONS` preflight support
- Security headers
- Request ID header
- Maximum request body size
- Health endpoint
- API docs endpoint
- SQLite logging
- Structured JSON errors
- Token and API key authentication

## 16. Important Endpoints

- `GET /`
- `GET /health`
- `GET /api/docs`
- `GET /stats`
- `POST /screen-resume`
- `POST /screen-batch`
- `POST /pdf-to-csv`
- `POST /screen-csv`
- `POST /auth/register`
- `POST /auth/login`
- `POST /candidates`
- `GET /candidates`
- `POST /jobs`
- `GET /jobs`
- `POST /resumes/upload`
- `GET /resumes/<resume_id>`
- `POST /ranking/job/<job_id>/rank-candidate/<candidate_id>`

Full API details are in [API_REFERENCE.md](API_REFERENCE.md).

## 17. Testing Guide

### Test Homepage

Open:

```text
http://127.0.0.1:5000/
```

### Test Health

Open:

```text
http://127.0.0.1:5000/health
```

Expected result:

```json
{
  "status": "healthy"
}
```

### Test Resume Screening

1. Select skills.
2. Upload `examples/sample_resume.txt` or `examples/sample_resume.docx`.
3. Click `Screen Resumes and Download Excel`.
4. Open the downloaded Excel file.

### Test CSV Screening

1. Upload `examples/sample_candidates.csv`.
2. Select required skills.
3. Click `Screen CSV Data`.
4. Open the downloaded Excel file.

### Test PDF to CSV

1. Upload a PDF with selectable text.
2. Click `Convert PDF to CSV`.
3. Open the downloaded CSV file.

## 18. Known Limitations

- Scanned image PDFs need OCR, which is not included.
- Ranking is heuristic, not a trained deep learning model.
- PDF parsing works best with selectable text PDFs.
- Very large CSV files may take time and memory depending on the computer.
- This is a local demo API and would need production hosting configuration for public deployment.

## 19. Future Enhancements

- Add OCR for scanned PDFs
- Add trained ML model for ranking
- Add recruiter dashboard with saved screening history
- Add role-based access control
- Add cloud deployment
- Add pagination for very large CSV screening output
- Add more skills and domain-specific skill dictionaries

## 20. Presentation Explanation

In simple words:

This project helps recruiters screen resumes faster. The recruiter enters job requirements, uploads resumes or candidate data, and the system extracts skills, experience, education, and contact details. Then it compares the candidate profile with the job requirements and gives a score and decision. The result can be downloaded in Excel for easy review.

## 21. Conclusion

The HR AI Resume Ranking API provides an end-to-end solution for resume screening. It includes file parsing, candidate ranking, API endpoints, authentication, exports, database storage, and a professional UI. It is simple enough to run locally but complete enough to demonstrate real-world HR automation concepts.
