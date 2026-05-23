import base64
import cgi
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "hr_python_api.db"
SECRET = os.environ.get("JWT_SECRET", "python_demo_secret")
PORT = int(os.environ.get("PORT", "5000"))

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)


HOME_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HR AI Resume Ranking API</title>
  <style>
    :root {
      --ink: #111827;
      --muted: #64748b;
      --line: #dbe3ef;
      --soft: #f6f8fc;
      --purple: #5136c2;
      --blue: #2563eb;
      --green: #159947;
      --amber: #d97706;
      font-family: Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f6fb; color: var(--ink); }
    header {
      background: linear-gradient(120deg, #4f36b8, #2563eb);
      color: white;
      padding: 28px 38px;
    }
    header h1 { margin: 0 0 8px; font-size: 28px; }
    header p { margin: 0; color: #e8edff; }
    main { max-width: 1180px; margin: 24px auto; padding: 0 18px 40px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .card {
      background: white;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
    }
    .card h2 { margin: 0 0 12px; font-size: 18px; }
    label { display: block; font-size: 12px; font-weight: bold; color: var(--muted); margin: 12px 0 5px; }
    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 11px;
      font-size: 14px;
      background: #fff;
    }
    textarea { min-height: 72px; resize: vertical; }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 14px;
      margin-top: 12px;
      background: var(--purple);
      color: white;
      font-weight: bold;
      cursor: pointer;
    }
    button.secondary { background: var(--blue); }
    button.good { background: var(--green); }
    button.warn { background: var(--amber); }
    .full { grid-column: 1 / -1; }
    .status {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .pill {
      background: white;
      border: 1px solid var(--line);
      border-left: 5px solid var(--purple);
      border-radius: 8px;
      padding: 12px;
      min-height: 62px;
    }
    .pill span { display: block; font-size: 12px; color: var(--muted); }
    .pill strong { font-size: 15px; word-break: break-word; }
    pre {
      background: #0f172a;
      color: #dbeafe;
      border-radius: 8px;
      padding: 14px;
      overflow: auto;
      min-height: 190px;
      white-space: pre-wrap;
    }
    .hint { color: var(--muted); font-size: 13px; line-height: 1.45; }
    @media (max-width: 850px) {
      .grid, .status { grid-template-columns: 1fr; }
      .full { grid-column: auto; }
      header { padding: 24px 20px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>AI-Powered Resume Parsing and Candidate Ranking API</h1>
    <p>Python demo homepage connected to the backend API</p>
  </header>
  <main>
    <section class="status">
      <div class="pill"><span>Server</span><strong id="serverState">Checking...</strong></div>
      <div class="pill"><span>Token</span><strong id="tokenState">Not logged in</strong></div>
      <div class="pill"><span>Candidate ID</span><strong id="candidateState">Not created</strong></div>
      <div class="pill"><span>Job ID</span><strong id="jobState">Not created</strong></div>
    </section>

    <section class="grid">
      <div class="card">
        <h2>1. Register / Login</h2>
        <p class="hint">Create a recruiter account. The token is saved automatically for the next steps.</p>
        <label>Email</label>
        <input id="email" value="">
        <label>Password</label>
        <input id="password" value="password123" type="password">
        <label>Name</label>
        <input id="name" value="Labib Recruiter">
        <button onclick="registerUser()">Register</button>
        <button class="secondary" onclick="loginUser()">Login</button>
      </div>

      <div class="card">
        <h2>2. Create Candidate</h2>
        <label>First Name</label>
        <input id="firstName" value="Ali">
        <label>Last Name</label>
        <input id="lastName" value="Khan">
        <label>Candidate Email</label>
        <input id="candidateEmail" value="">
        <label>Location</label>
        <input id="location" value="Mumbai">
        <button onclick="createCandidate()">Create Candidate</button>
      </div>

      <div class="card">
        <h2>3. Create Job</h2>
        <label>Job Title</label>
        <input id="jobTitle" value="Full Stack Developer">
        <label>Required Skills comma separated</label>
        <input id="requiredSkills" value="node.js, react, sql">
        <label>Preferred Skills comma separated</label>
        <input id="preferredSkills" value="docker">
        <label>Minimum Experience</label>
        <input id="minExp" value="2" type="number">
        <button onclick="createJob()">Create Job</button>
      </div>

      <div class="card">
        <h2>4. Upload Resume</h2>
        <p class="hint">Use a TXT resume for this Python demo. A sample file is included in <b>examples/sample_resume.txt</b>.</p>
        <label>Resume File</label>
        <input id="resumeFile" type="file" accept=".txt,.pdf,.docx">
        <button onclick="uploadResume()">Upload Resume</button>
      </div>

      <div class="card">
        <h2>5. Rank Candidate</h2>
        <p class="hint">This compares the latest parsed resume with the created job and returns a score.</p>
        <button class="good" onclick="rankCandidate()">Rank Candidate</button>
        <button class="warn" onclick="getStats()">Refresh Stats</button>
      </div>

      <div class="card">
        <h2>Demo Order</h2>
        <ol class="hint">
          <li>Register or login.</li>
          <li>Create candidate.</li>
          <li>Create job.</li>
          <li>Upload TXT resume.</li>
          <li>Rank candidate.</li>
        </ol>
      </div>

      <div class="card full">
        <h2>API Response</h2>
        <pre id="output">Ready.</pre>
      </div>
    </section>
  </main>

  <script>
    let token = localStorage.getItem("hr_token") || "";
    let candidateId = localStorage.getItem("candidate_id") || "";
    let jobId = localStorage.getItem("job_id") || "";
    const unique = Date.now();
    email.value = `labib${unique}@example.com`;
    candidateEmail.value = `candidate${unique}@example.com`;

    function show(data) {
      output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
      updateState();
    }

    function updateState() {
      tokenState.textContent = token ? "Available" : "Not logged in";
      candidateState.textContent = candidateId || "Not created";
      jobState.textContent = jobId || "Not created";
    }

    async function api(path, options = {}) {
      const headers = options.headers || {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const res = await fetch(path, { ...options, headers });
      const data = await res.json();
      if (!res.ok) throw data;
      return data;
    }

    async function checkHealth() {
      try {
        const data = await api("/health");
        serverState.textContent = data.status;
        show(data);
      } catch (e) {
        serverState.textContent = "Error";
        show(e);
      }
    }

    async function registerUser() {
      try {
        const data = await api("/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email.value,
            password: password.value,
            name: name.value,
            role: "recruiter"
          })
        });
        token = data.token;
        localStorage.setItem("hr_token", token);
        show(data);
      } catch (e) { show(e); }
    }

    async function loginUser() {
      try {
        const data = await api("/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.value, password: password.value })
        });
        token = data.token;
        localStorage.setItem("hr_token", token);
        show(data);
      } catch (e) { show(e); }
    }

    async function createCandidate() {
      try {
        const data = await api("/candidates", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            first_name: firstName.value,
            last_name: lastName.value,
            email: candidateEmail.value,
            phone: "9999999999",
            location: location.value
          })
        });
        candidateId = data.candidate.id;
        localStorage.setItem("candidate_id", candidateId);
        show(data);
      } catch (e) { show(e); }
    }

    async function createJob() {
      try {
        const split = (v) => v.split(",").map(s => s.trim().toLowerCase()).filter(Boolean);
        const data = await api("/jobs", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: jobTitle.value,
            department: "IT",
            location: "Remote",
            employment_type: "full_time",
            description: "Build web applications",
            requirements: requiredSkills.value,
            required_skills: split(requiredSkills.value),
            preferred_skills: split(preferredSkills.value),
            min_experience_yrs: Number(minExp.value || 0)
          })
        });
        jobId = data.job.id;
        localStorage.setItem("job_id", jobId);
        show(data);
      } catch (e) { show(e); }
    }

    async function uploadResume() {
      try {
        if (!candidateId) throw { error: "Create candidate first" };
        if (!resumeFile.files.length) throw { error: "Choose a resume file first" };
        const form = new FormData();
        form.append("candidate_id", candidateId);
        form.append("resume", resumeFile.files[0]);
        const data = await api("/resumes/upload", { method: "POST", body: form });
        show(data);
      } catch (e) { show(e); }
    }

    async function rankCandidate() {
      try {
        if (!candidateId || !jobId) throw { error: "Create candidate and job first" };
        const data = await api(`/ranking/job/${jobId}/rank-candidate/${candidateId}`, { method: "POST" });
        show(data);
      } catch (e) { show(e); }
    }

    async function getStats() {
      try { show(await api("/stats")); } catch (e) { show(e); }
    }

    updateState();
    checkHealth();
  </script>
</body>
</html>"""


SIMPLE_HOME_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HR AI API Demo</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f4f6fb; color: #111827; }
    .wrap { max-width: 880px; margin: 50px auto; background: white; padding: 32px; border-radius: 10px; box-shadow: 0 10px 28px rgba(0,0,0,.08); }
    h1 { margin-top: 0; color: #4f36b8; }
    .ok { padding: 14px; background: #ecfdf5; border-left: 5px solid #16a34a; margin: 18px 0; }
    button { background: #4f36b8; color: white; border: 0; padding: 11px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; }
    pre { background: #0f172a; color: #dbeafe; padding: 16px; border-radius: 8px; overflow: auto; }
    code { background: #eef2ff; padding: 2px 5px; border-radius: 4px; }
    li { margin: 8px 0; }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>AI-Powered Resume Parsing and Candidate Ranking API</h1>
    <p>This is a simple Python API demo page.</p>
    <div class="ok"><strong>Status:</strong> API server is running if health check shows healthy.</div>
    <button onclick="checkApi()">Check API</button>
    <h2>Demo URLs</h2>
    <ul>
      <li><code>/health</code> checks if the API is running.</li>
      <li><code>/stats</code> shows database counts.</li>
      <li><code>/auth/register</code> creates a recruiter user.</li>
      <li><code>/candidates</code> creates/lists candidates.</li>
      <li><code>/jobs</code> creates/lists jobs.</li>
      <li><code>/resumes/upload</code> uploads a resume.</li>
      <li><code>/ranking/job/&lt;job_id&gt;/rank-candidate/&lt;candidate_id&gt;</code> ranks a candidate.</li>
    </ul>
    <h2>API Response</h2>
    <pre id="out">Click "Check API"</pre>
  </div>
  <script>
    async function checkApi() {
      const health = await fetch('/health').then(r => r.json());
      const stats = await fetch('/stats').then(r => r.json());
      document.getElementById('out').textContent = JSON.stringify({ health, stats }, null, 2);
    }
    checkApi();
  </script>
</body>
</html>"""


RESUME_SCREEN_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bulk Resume Screening System</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f4f6fb; color: #111827; }
    .wrap { max-width: 980px; margin: 35px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 10px 28px rgba(0,0,0,.08); }
    h1 { margin-top: 0; color: #4f36b8; }
    .box { padding: 14px; background: #eef2ff; border-left: 5px solid #4f36b8; margin: 18px 0; }
    label { display:block; margin-top: 16px; font-weight: bold; color:#475569; }
    input { width: 100%; padding: 11px; border:1px solid #cbd5e1; border-radius:6px; margin-top:6px; }
    button { background: #4f36b8; color: white; border: 0; padding: 12px 18px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top:16px; }
    button.secondary { background:#2563eb; }
    pre { background: #0f172a; color: #dbeafe; padding: 16px; border-radius: 8px; overflow: auto; white-space: pre-wrap; }
    .skills { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px 14px; margin-top: 10px; }
    .skill { background:#f8fafc; border:1px solid #dbe3ef; border-radius:6px; padding:8px; font-size:14px; }
    .skill input { width:auto; margin:0 6px 0 0; }
    .row { display:grid; grid-template-columns: 1fr 1fr; gap:16px; }
    .result { margin-top: 20px; }
    .hint { color:#64748b; font-size:14px; line-height:1.45; }
    @media (max-width: 780px) { .skills, .row { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Bulk Resume Screening System</h1>
    <p>Select required skills, upload resumes, and download the screening result in Excel.</p>
    <div class="box"><strong>Decision:</strong> 80+ Shortlist, 60-79 Review, below 60 Not Recommended. You can upload up to 200 resumes at once.</div>
    <label>Job Title</label>
    <input id="jobTitle" value="Full Stack Developer">
    <div class="row">
      <div>
        <label>Minimum Experience in Years</label>
        <input id="minExperience" type="number" value="2">
      </div>
      <div>
        <label>Preferred Skills comma separated optional</label>
        <input id="preferredSkills" value="docker">
      </div>
    </div>
    <label>Required Skills Checklist</label>
    <div id="skills" class="skills"></div>
    <p class="hint">Tick the skills needed for the job. You may also type extra required skills below.</p>
    <label>Extra Required Skills comma separated optional</label>
    <input id="extraSkills" placeholder="example: pandas, excel, linux">
    <label>Upload Resumes TXT, DOCX, or PDF</label>
    <input id="resumeFiles" type="file" accept=".txt,.docx,.pdf" multiple>
    <button onclick="screenBatch()">Screen Resumes and Download Excel</button>
    <button class="secondary" onclick="selectCommon()">Select Common Developer Skills</button>
    <div class="result">
      <h2>Status</h2>
      <pre id="out">Choose skills, upload resumes, then click the screening button.</pre>
    </div>
  </div>
  <script>
    const allSkills = [
      'python','javascript','node.js','react','sql','sqlite','postgresql','mongodb',
      'express','html','css','docker','aws','java','c++','git','rest api','api',
      'machine learning','nlp','flask','fastapi','django'
    ];

    function renderSkills() {
      skills.innerHTML = allSkills.map(skill => `
        <label class="skill"><input type="checkbox" value="${skill}"> ${skill}</label>
      `).join('');
    }

    function selectedSkills() {
      const checked = Array.from(document.querySelectorAll('#skills input:checked')).map(x => x.value);
      const extra = extraSkills.value.split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
      return [...new Set([...checked, ...extra])];
    }

    function selectCommon() {
      const common = new Set(['node.js','react','sql','javascript','html','css','docker','git']);
      document.querySelectorAll('#skills input').forEach(box => box.checked = common.has(box.value));
    }

    async function screenBatch() {
      const files = resumeFiles.files;
      const req = selectedSkills();
      if (!files.length) {
        alert('Please choose at least one resume.');
        return;
      }
      if (files.length > 200) {
        alert('Maximum 200 resumes allowed.');
        return;
      }
      if (!req.length) {
        alert('Please select at least one required skill.');
        return;
      }
      const form = new FormData();
      for (const file of files) form.append('resumes', file);
      form.append('job_title', jobTitle.value);
      form.append('required_skills', req.join(','));
      form.append('preferred_skills', preferredSkills.value);
      form.append('min_experience_yrs', minExperience.value);

      out.textContent = 'Screening ' + files.length + ' resume(s)...';
      const res = await fetch('/screen-batch', { method: 'POST', body: form });
      if (!res.ok) {
        const error = await res.json();
        out.textContent = JSON.stringify(error, null, 2);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'resume_screening_results.xlsx';
      a.click();
      URL.revokeObjectURL(url);
      out.textContent = 'Done. Excel file downloaded: resume_screening_results.xlsx';
    }

    renderSkills();
    selectCommon();
  </script>
</body>
</html>"""


SKILL_KEYWORDS = [
    "python", "javascript", "node.js", "node", "react", "sql", "sqlite",
    "postgresql", "mongodb", "express", "html", "css", "docker", "aws",
    "java", "c++", "git", "rest api", "api", "machine learning", "nlp",
    "flask", "fastapi", "django",
]


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'recruiter',
                api_key TEXT UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                location TEXT,
                years_experience REAL DEFAULT 0,
                education_level TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS job_postings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                department TEXT,
                location TEXT,
                employment_type TEXT,
                description TEXT,
                requirements TEXT,
                required_skills TEXT DEFAULT '[]',
                preferred_skills TEXT DEFAULT '[]',
                min_experience_yrs REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_by TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS resumes (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                raw_text TEXT,
                preprocessed_text TEXT,
                parsed_data TEXT,
                parse_status TEXT DEFAULT 'pending',
                parse_error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ranking_results (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                candidate_id TEXT NOT NULL,
                resume_id TEXT,
                overall_score REAL,
                skill_score REAL,
                experience_score REAL,
                education_score REAL,
                keyword_score REAL,
                score_breakdown TEXT,
                recommendation TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES job_postings(id) ON DELETE CASCADE,
                FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS api_logs (
                id TEXT PRIMARY KEY,
                method TEXT,
                endpoint TEXT,
                status_code INTEGER,
                response_ms INTEGER,
                created_at TEXT NOT NULL
            );
            """
        )


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return hmac.compare_digest(check, digest)


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def sign(data):
    return b64(hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).digest())


def create_token(user):
    payload = {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "exp": int(time.time()) + 24 * 60 * 60,
    }
    body = b64(json.dumps(payload).encode())
    return f"{body}.{sign(body)}"


def read_token(token):
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(sign(body), sig):
            return None
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def clean_text(text):
    text = text.replace("\r\n", "\n").replace("\t", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_docx(data):
    text_parts = []
    with zipfile.ZipFile(BytesIO(data)) as zf:
        xml_data = zf.read("word/document.xml")
    root = ET.fromstring(xml_data)
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            text_parts.append(node.text)
        elif node.tag.endswith("}p"):
            text_parts.append("\n")
    return " ".join(text_parts)


def extract_text_from_pdf(data):
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        # Fallback for demo: extract readable text-like fragments from simple PDFs.
        raw = data.decode("latin-1", errors="ignore")
        chunks = re.findall(r"[A-Za-z0-9@.+#,/()\- ]{4,}", raw)
        return "\n".join(chunks)


def extract_text_from_file_bytes(filename, data):
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "txt":
        return data.decode("utf-8", errors="ignore")
    if ext == "docx":
        return extract_text_from_docx(data)
    if ext == "pdf":
        return extract_text_from_pdf(data)
    raise ValueError("Only TXT, DOCX, and PDF files are supported")


def extract_contact(text):
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"\+?\d[\d\s.-]{8,}\d", text)
    phone_value = phone.group(0) if phone else None
    if phone_value and len(re.sub(r"\D", "", phone_value)) < 10:
        phone_value = None
    return {
        "email": email.group(0) if email else None,
        "phone": phone_value,
    }


def extract_skills(text):
    lower = text.lower()
    found = []
    for skill in SKILL_KEYWORDS:
        if skill in lower and skill not in found:
            found.append(skill)
    return found


def estimate_experience(text):
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", text)]
    if len(years) >= 2:
        diff = max(years) - min(years)
        if 0 <= diff <= 40:
            return diff
    match = re.search(r"(\d+)\+?\s+years?", text, re.I)
    return int(match.group(1)) if match else 0


def detect_education(text):
    lower = text.lower()
    if "master" in lower or "mca" in lower:
        return "master"
    if "bachelor" in lower or "bca" in lower:
        return "bachelor"
    if "phd" in lower:
        return "phd"
    return "other"


def parse_resume_text(text):
    cleaned = clean_text(text)
    contact = extract_contact(cleaned)
    skills = extract_skills(cleaned)
    years = estimate_experience(cleaned)
    education = detect_education(cleaned)
    summary = f"Candidate has {years} years estimated experience and skills: {', '.join(skills[:8])}."
    return {
        "contact": contact,
        "skills": skills,
        "years_experience": years,
        "education_level": education,
        "summary": summary,
    }, cleaned


def score_resume(parsed, required, preferred, min_exp, job_title):
    candidate_skills = set(parsed.get("skills", []))
    matched_required = sorted(required & candidate_skills)
    matched_preferred = sorted(preferred & candidate_skills)
    skill_score = (len(matched_required) / max(len(required), 1)) * 70 + (len(matched_preferred) / max(len(preferred), 1)) * 30
    exp = float(parsed.get("years_experience", 0))
    experience_score = min((exp / max(min_exp, 1)) * 100, 100)
    education_score = 75 if parsed.get("education_level") in {"bachelor", "master", "phd"} else 50
    keyword_score = skill_score
    overall = round(skill_score * 0.45 + experience_score * 0.30 + education_score * 0.15 + keyword_score * 0.10, 2)

    if overall >= 80:
        decision = "SHORTLIST"
        decision_reason = "Candidate is a strong match for the entered requirements."
    elif overall >= 60:
        decision = "REVIEW"
        decision_reason = "Candidate has a partial match and should be reviewed manually."
    else:
        decision = "NOT RECOMMENDED"
        decision_reason = "Candidate does not match enough required skills or experience."

    recommendation = (
        f"Resume screened successfully for {job_title}. Candidate scored {overall}/100. "
        f"Decision: {decision}. {decision_reason}"
    )
    return {
        "overall_score": overall,
        "skill_score": round(skill_score, 2),
        "experience_score": round(experience_score, 2),
        "education_score": education_score,
        "keyword_score": round(keyword_score, 2),
        "matched_required_skills": matched_required,
        "missing_required_skills": sorted(required - candidate_skills),
        "matched_preferred_skills": matched_preferred,
        "decision": decision,
        "decision_reason": decision_reason,
        "recommendation": recommendation,
    }


def json_response(handler, status, payload):
    data = json.dumps(payload, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def xml_escape(value):
    text = "" if value is None else str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def excel_column_name(index):
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def create_xlsx(headers, rows, widths):
    worksheet_rows = [headers] + rows
    sheet_xml = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        "<sheetViews><sheetView workbookViewId=\"0\"><pane ySplit=\"1\" topLeftCell=\"A2\" activePane=\"bottomLeft\" state=\"frozen\"/></sheetView></sheetViews>",
        "<cols>",
    ]
    for idx, width in enumerate(widths, start=1):
        sheet_xml.append(f'<col min="{idx}" max="{idx}" width="{width}" customWidth="1"/>')
    sheet_xml.append("</cols><sheetData>")

    for row_index, row in enumerate(worksheet_rows, start=1):
        sheet_xml.append(f'<row r="{row_index}">')
        for col_index, value in enumerate(row, start=1):
            cell_ref = f"{excel_column_name(col_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                sheet_xml.append(f'<c r="{cell_ref}"{style}><v>{value}</v></c>')
            else:
                sheet_xml.append(f'<c r="{cell_ref}" t="inlineStr"{style}><is><t>{xml_escape(value)}</t></is></c>')
        sheet_xml.append("</row>")
    sheet_xml.append("</sheetData></worksheet>")

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Screening Results" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""
    workbook_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF4F36B8"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", "".join(sheet_xml))
        archive.writestr("xl/styles.xml", styles_xml)
    return output.getvalue()


def xlsx_response(handler, filename, content):
    handler.send_response(200)
    handler.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def html_response(handler, status, html):
    data = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


class App(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def send_json(self, status, payload):
        json_response(self, status, payload)

    def send_html(self, status, html):
        html_response(self, status, html)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def current_user(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            payload = read_token(auth[7:])
            if not payload:
                return None
            with db() as conn:
                return conn.execute("SELECT * FROM users WHERE id=?", (payload["id"],)).fetchone()
        api_key = self.headers.get("X-API-Key")
        if api_key:
            with db() as conn:
                return conn.execute("SELECT * FROM users WHERE api_key=?", (api_key,)).fetchone()
        return None

    def require_user(self):
        user = self.current_user()
        if not user:
            self.send_json(401, {"error": "Authentication required"})
            return None
        return user

    def do_GET(self):
        start = time.time()
        status = 200
        try:
            path = urlparse(self.path).path
            if path == "/":
                self.send_html(200, RESUME_SCREEN_PAGE)
            elif path == "/health":
                self.send_json(200, {"status": "healthy", "version": "python-1.0.0"})
            elif path == "/stats":
                with db() as conn:
                    self.send_json(200, {
                        "candidates": conn.execute("SELECT COUNT(*) n FROM candidates").fetchone()["n"],
                        "jobs": conn.execute("SELECT COUNT(*) n FROM job_postings WHERE status='open'").fetchone()["n"],
                        "resumes": conn.execute("SELECT COUNT(*) n FROM resumes").fetchone()["n"],
                        "rankings": conn.execute("SELECT COUNT(*) n FROM ranking_results").fetchone()["n"],
                    })
            elif path == "/candidates":
                if not self.require_user():
                    return
                with db() as conn:
                    rows = conn.execute("SELECT * FROM candidates ORDER BY created_at DESC").fetchall()
                    self.send_json(200, {"candidates": [row_to_dict(r) for r in rows]})
            elif path == "/jobs":
                if not self.require_user():
                    return
                with db() as conn:
                    rows = conn.execute("SELECT * FROM job_postings ORDER BY created_at DESC").fetchall()
                    out = []
                    for r in rows:
                        item = row_to_dict(r)
                        item["required_skills"] = json.loads(item["required_skills"])
                        item["preferred_skills"] = json.loads(item["preferred_skills"])
                        out.append(item)
                    self.send_json(200, {"jobs": out})
            elif path.startswith("/resumes/"):
                if not self.require_user():
                    return
                resume_id = path.split("/")[-1]
                with db() as conn:
                    row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
                    if not row:
                        self.send_json(404, {"error": "Resume not found"})
                        return
                    item = row_to_dict(row)
                    item["parsed_data"] = json.loads(item["parsed_data"]) if item["parsed_data"] else None
                    self.send_json(200, {"resume": item})
            else:
                status = 404
                self.send_json(404, {"error": f"Route not found: GET {path}"})
        finally:
            self.log_request_row(status, start)

    def do_POST(self):
        start = time.time()
        status = 200
        try:
            path = urlparse(self.path).path
            if path == "/screen-resume":
                self.handle_screen_resume()
            elif path == "/screen-batch":
                self.handle_screen_batch()
            elif path == "/auth/register":
                body = self.read_json()
                email = body.get("email")
                password = body.get("password")
                name = body.get("name")
                role = body.get("role", "recruiter")
                if not email or not password or not name:
                    self.send_json(400, {"error": "email, password, name required"})
                    return
                user_id = str(uuid.uuid4())
                api_key = "py-" + secrets.token_hex(16)
                with db() as conn:
                    try:
                        conn.execute(
                            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (user_id, email, hash_password(password), name, role, api_key, now()),
                        )
                    except sqlite3.IntegrityError:
                        self.send_json(409, {"error": "Email already registered"})
                        return
                    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
                self.send_json(201, {
                    "message": "Account created",
                    "user": {"id": user["id"], "email": user["email"], "name": user["name"], "role": user["role"]},
                    "token": create_token(user),
                    "api_key": api_key,
                })
            elif path == "/auth/login":
                body = self.read_json()
                with db() as conn:
                    user = conn.execute("SELECT * FROM users WHERE email=?", (body.get("email"),)).fetchone()
                if not user or not verify_password(body.get("password", ""), user["password_hash"]):
                    self.send_json(401, {"error": "Invalid credentials"})
                    return
                self.send_json(200, {"message": "Login successful", "token": create_token(user)})
            elif path == "/candidates":
                user = self.require_user()
                if not user:
                    return
                body = self.read_json()
                cid = str(uuid.uuid4())
                with db() as conn:
                    conn.execute(
                        """INSERT INTO candidates
                        (id, first_name, last_name, email, phone, location, years_experience, education_level, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 0, NULL, 'active', ?)""",
                        (cid, body.get("first_name"), body.get("last_name"), body.get("email"), body.get("phone"), body.get("location"), now()),
                    )
                    row = conn.execute("SELECT * FROM candidates WHERE id=?", (cid,)).fetchone()
                self.send_json(201, {"message": "Candidate created", "candidate": row_to_dict(row)})
            elif path == "/jobs":
                user = self.require_user()
                if not user:
                    return
                body = self.read_json()
                jid = str(uuid.uuid4())
                with db() as conn:
                    conn.execute(
                        """INSERT INTO job_postings
                        (id, title, department, location, employment_type, description, requirements,
                         required_skills, preferred_skills, min_experience_yrs, status, created_by, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)""",
                        (
                            jid,
                            body.get("title"),
                            body.get("department"),
                            body.get("location"),
                            body.get("employment_type"),
                            body.get("description"),
                            body.get("requirements"),
                            json.dumps(body.get("required_skills", [])),
                            json.dumps(body.get("preferred_skills", [])),
                            body.get("min_experience_yrs", 0),
                            user["id"],
                            now(),
                        ),
                    )
                    row = conn.execute("SELECT * FROM job_postings WHERE id=?", (jid,)).fetchone()
                item = row_to_dict(row)
                item["required_skills"] = json.loads(item["required_skills"])
                item["preferred_skills"] = json.loads(item["preferred_skills"])
                self.send_json(201, {"message": "Job posting created", "job": item})
            elif path == "/resumes/upload":
                user = self.require_user()
                if not user:
                    return
                self.handle_upload()
            elif re.match(r"^/ranking/job/[^/]+/rank-candidate/[^/]+$", path):
                user = self.require_user()
                if not user:
                    return
                parts = path.split("/")
                self.handle_rank(parts[3], parts[5])
            else:
                status = 404
                self.send_json(404, {"error": f"Route not found: POST {path}"})
        except Exception as exc:
            status = 500
            self.send_json(500, {"error": "Internal server error", "message": str(exc)})
        finally:
            self.log_request_row(status, start)

    def handle_upload(self):
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            self.send_json(400, {"error": "multipart/form-data required"})
            return
        pdict["boundary"] = bytes(pdict["boundary"], "utf-8")
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        candidate_id = form.getvalue("candidate_id")
        file_item = form["resume"] if "resume" in form else None
        if not candidate_id or file_item is None or not file_item.filename:
            self.send_json(400, {"error": "candidate_id and resume file required"})
            return
        ext = Path(file_item.filename).suffix.lower().lstrip(".")
        if ext not in {"txt", "pdf", "docx"}:
            self.send_json(400, {"error": "Only txt, pdf, docx allowed"})
            return
        resume_id = str(uuid.uuid4())
        safe_name = f"{resume_id}.{ext}"
        file_path = UPLOAD_DIR / safe_name
        data = file_item.file.read()
        file_path.write_bytes(data)
        raw_text = extract_text_from_file_bytes(file_item.filename, data)
        try:
            parsed, cleaned = parse_resume_text(raw_text)
            status = "completed" if raw_text.strip() else "failed"
            error = None if raw_text.strip() else "No readable text could be extracted from this file."
        except Exception as exc:
            parsed, cleaned, status, error = {}, "", "failed", str(exc)
        with db() as conn:
            conn.execute(
                """INSERT INTO resumes
                (id, candidate_id, filename, file_path, file_type, raw_text, preprocessed_text,
                 parsed_data, parse_status, parse_error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (resume_id, candidate_id, file_item.filename, str(file_path), ext, raw_text, cleaned, json.dumps(parsed), status, error, now()),
            )
            if parsed:
                conn.execute(
                    "UPDATE candidates SET years_experience=?, education_level=? WHERE id=?",
                    (parsed.get("years_experience", 0), parsed.get("education_level"), candidate_id),
            )
        self.send_json(202, {"message": "Resume uploaded and processed", "resume_id": resume_id, "status": status})

    def handle_screen_resume(self):
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        file_item = form["resume"] if "resume" in form else None
        if file_item is None or not file_item.filename:
            self.send_json(400, {"error": "Please upload a resume file"})
            return

        ext = Path(file_item.filename).suffix.lower().lstrip(".")
        if ext not in {"txt", "docx", "pdf"}:
            self.send_json(400, {"error": "Only TXT, DOCX, and PDF resumes are supported"})
            return

        raw_text = extract_text_from_file_bytes(file_item.filename, file_item.file.read())
        if not raw_text.strip():
            self.send_json(400, {"error": "No readable text could be extracted from this file"})
            return
        parsed, cleaned = parse_resume_text(raw_text)

        required = {
            s.strip().lower()
            for s in form.getvalue("required_skills", "node.js,react,sql").split(",")
            if s.strip()
        }
        preferred = {
            s.strip().lower()
            for s in form.getvalue("preferred_skills", "docker").split(",")
            if s.strip()
        }
        min_exp = float(form.getvalue("min_experience_yrs", "2") or 2)
        job_title = form.getvalue("job_title", "Selected Job")

        ranking = score_resume(parsed, required, preferred, min_exp, job_title)

        self.send_json(200, {
            "message": "Resume screened successfully",
            "parsed_resume": parsed,
            "ranking": ranking
        })

    def handle_screen_batch(self):
        ctype, pdict = cgi.parse_header(self.headers.get("Content-Type", ""))
        if ctype != "multipart/form-data":
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        files = form["resumes"] if "resumes" in form else []
        if not isinstance(files, list):
            files = [files]
        files = [item for item in files if item is not None and item.filename]

        if not files:
            self.send_json(400, {"error": "Please upload at least one resume"})
            return
        if len(files) > 200:
            self.send_json(400, {"error": "Maximum 200 resumes are allowed in one screening batch"})
            return

        required = {
            s.strip().lower()
            for s in form.getvalue("required_skills", "").split(",")
            if s.strip()
        }
        preferred = {
            s.strip().lower()
            for s in form.getvalue("preferred_skills", "").split(",")
            if s.strip()
        }
        if not required:
            self.send_json(400, {"error": "Please select at least one required skill"})
            return

        try:
            min_exp = float(form.getvalue("min_experience_yrs", "0") or 0)
        except ValueError:
            min_exp = 0
        job_title = form.getvalue("job_title", "Selected Job")

        headers = [
            "No", "File Name", "Status", "Candidate Email", "Phone", "Extracted Skills",
            "Years Experience", "Education", "Overall Score", "Skill Score", "Experience Score",
            "Education Score", "Keyword Score", "Decision", "Matched Required Skills",
            "Missing Required Skills", "Matched Preferred Skills", "Recommendation", "Error",
        ]
        rows = []

        for index, file_item in enumerate(files, start=1):
            filename = file_item.filename
            ext = Path(filename).suffix.lower().lstrip(".")
            if ext not in {"txt", "docx", "pdf"}:
                rows.append([index, filename, "ERROR", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "Only TXT, DOCX, and PDF files are supported"])
                continue

            try:
                raw_text = extract_text_from_file_bytes(filename, file_item.file.read())
                if not raw_text.strip():
                    raise ValueError("No readable text could be extracted from this file")
                parsed, cleaned = parse_resume_text(raw_text)
                ranking = score_resume(parsed, required, preferred, min_exp, job_title)
                contact = parsed.get("contact", {})
                rows.append([
                    index,
                    filename,
                    "SCREENED",
                    contact.get("email", ""),
                    contact.get("phone", ""),
                    ", ".join(parsed.get("skills", [])),
                    parsed.get("years_experience", 0),
                    parsed.get("education_level", ""),
                    ranking["overall_score"],
                    ranking["skill_score"],
                    ranking["experience_score"],
                    ranking["education_score"],
                    ranking["keyword_score"],
                    ranking["decision"],
                    ", ".join(ranking["matched_required_skills"]),
                    ", ".join(ranking["missing_required_skills"]),
                    ", ".join(ranking["matched_preferred_skills"]),
                    ranking["recommendation"],
                    "",
                ])
            except Exception as exc:
                rows.append([index, filename, "ERROR", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", str(exc)])

        widths = [8, 28, 14, 28, 18, 45, 18, 14, 15, 12, 18, 16, 14, 18, 35, 35, 35, 65, 40]
        xlsx_response(self, "resume_screening_results.xlsx", create_xlsx(headers, rows, widths))

    def handle_rank(self, job_id, candidate_id):
        with db() as conn:
            job = conn.execute("SELECT * FROM job_postings WHERE id=?", (job_id,)).fetchone()
            candidate = conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
            resume = conn.execute(
                "SELECT * FROM resumes WHERE candidate_id=? AND parse_status='completed' ORDER BY created_at DESC LIMIT 1",
                (candidate_id,),
            ).fetchone()
            if not job or not candidate:
                self.send_json(404, {"error": "Job or candidate not found"})
                return
            if not resume:
                self.send_json(422, {"error": "No completed parsed resume found for candidate"})
                return
            parsed = json.loads(resume["parsed_data"])
            candidate_skills = set(parsed.get("skills", []))
            required = {s.lower() for s in json.loads(job["required_skills"])}
            preferred = {s.lower() for s in json.loads(job["preferred_skills"])}
            matched_required = sorted(required & candidate_skills)
            matched_preferred = sorted(preferred & candidate_skills)
            skill_score = (len(matched_required) / max(len(required), 1)) * 70 + (len(matched_preferred) / max(len(preferred), 1)) * 30
            exp = float(parsed.get("years_experience", 0))
            min_exp = float(job["min_experience_yrs"] or 0)
            experience_score = min((exp / max(min_exp, 1)) * 100, 100)
            education_score = 75 if parsed.get("education_level") in {"bachelor", "master", "phd"} else 50
            keyword_score = skill_score
            overall = round(skill_score * 0.45 + experience_score * 0.30 + education_score * 0.15 + keyword_score * 0.10, 2)
            breakdown = {
                "matched_required_skills": matched_required,
                "missing_required_skills": sorted(required - candidate_skills),
                "matched_preferred_skills": matched_preferred,
            }
            recommendation = f"{candidate['first_name']} {candidate['last_name']} scored {overall}/100 for {job['title']}."
            rid = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO ranking_results
                (id, job_id, candidate_id, resume_id, overall_score, skill_score, experience_score,
                 education_score, keyword_score, score_breakdown, recommendation, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, job_id, candidate_id, resume["id"], overall, skill_score, experience_score, education_score, keyword_score, json.dumps(breakdown), recommendation, now()),
            )
        self.send_json(200, {
            "candidate": {"id": candidate_id, "name": f"{candidate['first_name']} {candidate['last_name']}"},
            "job": {"id": job_id, "title": job["title"]},
            "ranking": {
                "overall_score": overall,
                "skill_score": round(skill_score, 2),
                "experience_score": round(experience_score, 2),
                "education_score": education_score,
                "keyword_score": round(keyword_score, 2),
                "score_breakdown": breakdown,
                "recommendation": recommendation,
            },
        })

    def log_request_row(self, status, start):
        try:
            with db() as conn:
                conn.execute(
                    "INSERT INTO api_logs VALUES (?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), self.command, urlparse(self.path).path, status, int((time.time() - start) * 1000), now()),
                )
        except Exception:
            pass


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), App)
    print(f"Python HR AI API running at http://127.0.0.1:{PORT}")
    server.serve_forever()
