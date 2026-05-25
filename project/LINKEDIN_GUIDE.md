# LinkedIn Upload Guide

## What To Upload

For LinkedIn, do not upload the whole ZIP directly as the main post. The best approach is:

1. Push the project to GitHub.
2. Add the GitHub link in your LinkedIn post.
3. Add 2-4 screenshots or a short demo video.
4. Write a short explanation of what the project does.

GitHub repository:

```text
https://github.com/labibhaider4-hash/hr-ai-resume-ranking-api
```

## Screenshots To Take

Take screenshots of:

1. Professional homepage UI
2. Resume upload section
3. Excel output after screening
4. CSV screening or PDF-to-CSV section

## Optional Demo Video

Record a 30-60 second video:

1. Open `http://127.0.0.1:5000/`
2. Select required skills
3. Upload a sample resume
4. Download Excel result
5. Show the score and decision columns

## LinkedIn Post Template

```text
I built an HR AI Resume Ranking API as my final year project.

The project helps recruiters screen resumes faster by extracting skills, experience, education, and contact details, then ranking candidates based on job requirements.

Key features:
- Bulk resume screening for TXT, DOCX, and PDF files
- Skill checklist and adjustable job requirements
- CSV resume data screening
- PDF data to CSV conversion
- Excel result export
- Token/API key authentication
- SQLite database storage
- Professional browser UI
- Python-only backend with no Node.js dependency

Tech stack:
Python, SQLite, HTML, CSS, JavaScript, REST API

GitHub:
https://github.com/labibhaider4-hash/hr-ai-resume-ranking-api

#Python #MachineLearning #NLP #ResumeScreening #HRTech #FinalYearProject #API #SQLite #WebDevelopment
```

## Short LinkedIn Version

```text
I built a Python-based HR AI Resume Ranking API.

It screens resumes, extracts skills and experience, ranks candidates against job requirements, and exports results in Excel.

Features include bulk resume upload, CSV screening, PDF-to-CSV conversion, authentication, SQLite storage, and a professional browser UI.

GitHub:
https://github.com/labibhaider4-hash/hr-ai-resume-ranking-api

#Python #NLP #HRTech #FinalYearProject #API
```

## How To Add The GitHub Link

1. Open LinkedIn.
2. Click `Start a post`.
3. Paste the post text.
4. Paste the GitHub link.
5. Upload screenshots or a demo video.
6. Click `Post`.

## What To Write In The GitHub Repository Description

Use this:

```text
Python HR AI Resume Ranking API with bulk resume screening, CSV screening, PDF-to-CSV conversion, Excel export, SQLite database, authentication, and professional browser UI.
```

## LinkedIn Profile Project Section

You can also add it under your LinkedIn profile:

1. Go to your LinkedIn profile.
2. Click `Add profile section`.
3. Choose `Recommended`.
4. Choose `Add projects`.
5. Fill in:

Project name:

```text
HR AI Resume Ranking API
```

Description:

```text
Built a Python-based resume screening API that extracts skills, experience, education, and contact details from resumes, ranks candidates against job requirements, and exports screening results in Excel. The project supports TXT, DOCX, PDF, and CSV inputs, includes PDF-to-CSV conversion, SQLite storage, authentication, and a professional browser UI.
```

Project URL:

```text
https://github.com/labibhaider4-hash/hr-ai-resume-ranking-api
```

## What To Say If Someone Asks About It

Simple answer:

```text
This project automates the first level of resume screening. A recruiter can enter job requirements, upload resumes or CSV candidate data, and the system extracts useful details, calculates a match score, gives a shortlist/review/not recommended decision, and exports the result to Excel.
```

Technical answer:

```text
The backend is built in Python using the standard library HTTP server and SQLite. It parses TXT, DOCX, PDF, and CSV data, extracts skills and contact information using regex and keyword matching, calculates a weighted ranking score, stores structured data, and exposes REST API endpoints with authentication, request IDs, CORS, and health/docs routes.
```
