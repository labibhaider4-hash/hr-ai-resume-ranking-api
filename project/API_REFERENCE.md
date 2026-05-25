# API Reference

Base URL:

```text
http://127.0.0.1:5000
```

## Health

### GET `/health`

Checks if the API is running.

Response:

```json
{
  "status": "healthy",
  "version": "python-1.1.0",
  "service": "hr-ai-resume-ranking-api"
}
```

## API Docs

### GET `/api/docs`

Returns available endpoints and limits.

## Stats

### GET `/stats`

Returns database counts for candidates, jobs, resumes, and rankings.

## Resume Screening

### POST `/screen-resume`

Screens one resume file.

Request type:

```text
multipart/form-data
```

Fields:

- `resume`: TXT, DOCX, or PDF file
- `job_title`: job title
- `required_skills`: comma-separated skills
- `preferred_skills`: comma-separated skills
- `min_experience_yrs`: minimum years of experience

Response:

```json
{
  "message": "Resume screened successfully",
  "parsed_resume": {},
  "ranking": {}
}
```

## Bulk Resume Screening

### POST `/screen-batch`

Screens up to 1,000,000 resume files and returns an Excel file.

Request type:

```text
multipart/form-data
```

Fields:

- `resumes`: one or more TXT, DOCX, or PDF files
- `job_title`: job title
- `required_skills`: comma-separated skills
- `preferred_skills`: comma-separated skills
- `min_experience_yrs`: minimum years of experience

Output:

```text
resume_screening_results.xlsx
```

## PDF Data to CSV

### POST `/pdf-to-csv`

Converts readable PDF text into CSV rows.

Request type:

```text
multipart/form-data
```

Fields:

- `pdf_files`: one or more PDF files

Output:

```text
pdf_data_output.csv
```

Important: scanned image PDFs need OCR and may not extract readable text.

## CSV Resume Screening

### POST `/screen-csv`

Screens candidate/resume data directly from a CSV file.

Request type:

```text
multipart/form-data
```

Fields:

- `csv_file`: CSV file
- `job_title`: job title
- `required_skills`: comma-separated skills
- `preferred_skills`: comma-separated skills
- `min_experience_yrs`: minimum years of experience

Useful CSV columns:

- `resume_text`
- `skills`
- `experience`
- `education`
- `summary`
- `profile`
- `candidate`
- `name`

Output:

```text
csv_resume_screening_results.xlsx
```

Limit:

```text
1,000,000 CSV rows
```

## Authentication

### POST `/auth/register`

Creates a recruiter account.

Request JSON:

```json
{
  "name": "Recruiter Name",
  "email": "recruiter@example.com",
  "password": "password123",
  "role": "recruiter"
}
```

Response includes:

- token
- API key

### POST `/auth/login`

Logs in a recruiter.

Request JSON:

```json
{
  "email": "recruiter@example.com",
  "password": "password123"
}
```

## Authenticated Candidate APIs

These routes require either:

```text
Authorization: Bearer <token>
```

or:

```text
X-API-Key: <api_key>
```

### POST `/candidates`

Creates a candidate.

### GET `/candidates`

Lists candidates.

## Authenticated Job APIs

### POST `/jobs`

Creates a job posting.

### GET `/jobs`

Lists job postings.

## Authenticated Resume APIs

### POST `/resumes/upload`

Uploads a resume for an existing candidate.

### GET `/resumes/<resume_id>`

Returns parsed resume details.

## Authenticated Ranking API

### POST `/ranking/job/<job_id>/rank-candidate/<candidate_id>`

Ranks one candidate against one job posting.

## Response Headers

The API includes practical response headers:

- `X-Request-ID`
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Referrer-Policy`
- `Access-Control-Allow-Origin`

## Error Format

Example:

```json
{
  "error": "Request too large",
  "message": "Request body is too large.",
  "request_id": "..."
}
```
