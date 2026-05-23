# AI-Powered Resume Parsing and Candidate Ranking API

MCA final year project for an AI/NLP-based recruitment support API.

## Project Overview

This project is a Node.js and Express REST API that helps recruiters process resumes, extract structured candidate information, and rank candidates against job postings.

The system supports:

- User registration and login
- JWT/API-key authentication
- Candidate management
- Job posting management
- Resume upload in PDF, DOCX, and TXT format
- Resume text preprocessing
- AI/NLP-based resume parsing
- Candidate ranking against job requirements
- API request logging
- Project report and presentation files

## Folder Structure

```text
Final_Submission_Package/
├── project/          # Full backend source code
├── report/           # Project report DOCX
├── presentation/     # Final presentation PPTX and previews
└── README_SUBMISSION.txt
```

## Tech Stack

- Node.js
- Express.js
- SQLite
- better-sqlite3
- Multer
- JWT
- bcryptjs
- pdf-parse
- Mammoth
- Winston / Morgan
- AI/NLP service integration

## How To Run

Open the `project` folder:

```bash
cd project
npm install
```

Create a `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Set required values such as:

```env
PORT=3000
JWT_SECRET=mysecret123
ANTHROPIC_API_KEY=your_api_key_here
DB_PATH=./data/hr_system.db
UPLOAD_DIR=./uploads
```

Start the server:

```bash
npm start
```

Test in browser:

```text
http://localhost:3000/health
```

## Main API Modules

- `/auth`
- `/candidates`
- `/jobs`
- `/resumes`
- `/ranking`
- `/health`
- `/stats`

## Notes

The project uses AI API integration for resume parsing and ranking. Custom model training and cloud deployment are listed as future enhancements.
