AI-Powered Resume Parsing and Candidate Ranking API
Final Submission Package

Student: Labib Rizvi
Platform: Qollabb
Project type: MCA final year project

Folder contents:

1. project/
   Full Node.js/Express project source code arranged in runnable structure:
   - server.js
   - package.json
   - .env.example
   - src/database/schema.js
   - src/database/seed.js
   - src/middleware/auth.js
   - src/middleware/logger.js
   - src/routes/candidates.js
   - src/routes/jobs.js
   - src/routes/resumes.js
   - src/routes/ranking.js
   - src/services/aiService.js
   - src/services/nlpService.js
   - data/
   - uploads/

2. report/
   HR_AI_API_Project_Report.docx

3. presentation/
   HR_AI_API_Project_Presentation.pptx
   previews/contact-sheet.jpg

Run instructions:

1. Open the project folder.
2. Run npm install.
3. Copy .env.example to .env and fill required values such as JWT_SECRET and AI API key.
4. Run npm run seed if seed data is required.
5. Run npm start.
6. Check http://localhost:3000/health.

Notes:

- The project source was organized into the folder structure expected by server.js.
- The presentation contains 12 slides covering problem statement, objectives, architecture, database, API modules, NLP/AI workflow, testing, results, and future scope.
