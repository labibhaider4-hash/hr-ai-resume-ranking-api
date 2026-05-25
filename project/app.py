import base64
import csv
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
import zlib
import xml.etree.ElementTree as ET
from io import BytesIO, StringIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = DATA_DIR / "hr_python_api.db"
SECRET = os.environ.get("JWT_SECRET", "python_demo_secret")
PORT = int(os.environ.get("PORT", "5000"))
APP_VERSION = "python-1.1.0"
MAX_REQUEST_BYTES = int(os.environ.get("MAX_REQUEST_BYTES", str(250 * 1024 * 1024)))

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_RESUME_FILES = 1_000_000
MAX_CSV_SCREENING_ROWS = 1_000_000


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


RESUME_SCREEN_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>HR TalentScan — HR Resume Intelligence</title>  <style>
    :root {
      --navy:        #0d1b38;
      --navy-mid:    #1a2f5a;
      --navy-light:  #243f78;
      --teal:        #0d9488;
      --teal-hover:  #0f8075;
      --teal-pale:   #f0fdfa;
      --teal-border: #99e6da;
      --bg:          #f0f4f9;
      --surface:     #ffffff;
      --border:      #dde3ed;
      --border-str:  #c6cfdf;
      --text:        #0d1526;
      --text-mid:    #2e3f5c;
      --text-muted:  #5f7090;
      --text-faint:  #9aacca;
      --success:     #059669;
      --success-bg:  #ecfdf5;
      --warning-bg:  #fffbeb;
      --warning:     #b45309;
      --info-bg:     #eff6ff;
      --info:        #1d4ed8;
      --info-border: #bfdbfe;
      --r-sm: 6px;
      --r:    10px;
      --r-lg: 14px;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 15px;
      line-height: 1.6;
      min-height: 100vh;
    }

    /* ═══════════════ HEADER ═══════════════ */
    .app-header {
      background: var(--navy);
      color: #fff;
      height: 62px;
      padding: 0 2rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: sticky;
      top: 0;
      z-index: 1,000,000;
      border-bottom: 1px solid rgba(255,255,255,0.07);
      box-shadow: 0 2px 20px rgba(0,0,0,0.25);
    }

    .header-brand { display: flex; align-items: center; gap: 12px; }

    .brand-mark {
      width: 36px; height: 36px;
      background: var(--teal);
      border-radius: 8px;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px; font-weight: 700; color: #fff;
      letter-spacing: -1px;
      flex-shrink: 0;
    }

    .brand-text { display: flex; flex-direction: column; gap: 1px; }
    .brand-name { font-size: 17px; font-weight: 600; letter-spacing: -0.4px; color: #fff; line-height: 1.2; }
    .brand-sub  { font-size: 10.5px; color: rgba(255,255,255,0.38); letter-spacing: 0.7px; text-transform: uppercase; }

    .header-pills { display: flex; align-items: center; gap: 8px; }
    .pill {
      background: rgba(255,255,255,0.07);
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 20px;
      padding: 4px 11px;
      font-size: 11.5px;
      color: rgba(255,255,255,0.6);
      letter-spacing: 0.1px;
    }
    .pill.accent { background: rgba(13,148,136,0.25); border-color: rgba(13,148,136,0.5); color: #5eead4; }

    /* ═══════════════ LAYOUT ═══════════════ */
    .app-body {
      max-width: 1280px;
      margin: 0 auto;
      padding: 1.75rem 1.5rem;
      display: grid;
      grid-template-columns: 268px 1fr;
      gap: 1.5rem;
      align-items: start;
    }

    /* ═══════════════ SIDEBAR ═══════════════ */
    .sidebar { display: flex; flex-direction: column; gap: 1rem; position: sticky; top: 78px; }

    .sidebar-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-lg);
      padding: 1.25rem;
      box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    .sidebar-heading {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--text-faint);
      margin-bottom: 1rem;
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0.75rem 0.875rem;
      background: var(--bg);
      border-radius: var(--r);
      margin-bottom: 8px;
      border-left: 3px solid var(--teal);
    }
    .stat-item.blue { border-left-color: #3b82f6; }
    .stat-item.purple { border-left-color: #7c3aed; }
    .stat-item:last-child { margin-bottom: 0; }

    .stat-icon { font-size: 20px; flex-shrink: 0; }
    .stat-body { flex: 1; min-width: 0; }
    .stat-val  { font-size: 17px; font-weight: 600; color: var(--text); letter-spacing: -0.3px; line-height: 1.2; }
    .stat-desc { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

    .feature-list { display: flex; flex-direction: column; gap: 2px; }
    .feat-row {
      display: flex; align-items: flex-start; gap: 9px;
      padding: 7px 0;
      border-bottom: 1px solid var(--border);
      font-size: 13px;
      color: var(--text-mid);
      line-height: 1.4;
    }
    .feat-row:last-child { border-bottom: none; }
    .feat-icon { font-size: 14px; flex-shrink: 0; margin-top: 1px; }

    .notice {
      background: var(--info-bg);
      border: 1px solid var(--info-border);
      border-radius: var(--r);
      padding: 0.875rem 1rem;
      font-size: 12px;
      color: var(--info);
      line-height: 1.55;
    }
    .notice strong { font-weight: 600; }

    /* ═══════════════ MAIN PANEL ═══════════════ */
    .main-panel { display: flex; flex-direction: column; }

    .tab-bar {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r-lg) var(--r-lg) 0 0;
      padding: 7px;
      display: flex;
      gap: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    .tab-btn {
      flex: 1;
      padding: 10px 14px;
      border: none;
      background: transparent;
      border-radius: var(--r);
      font-family: 'DM Sans', sans-serif;
      font-size: 13.5px;
      font-weight: 500;
      color: var(--text-muted);
      cursor: pointer;
      transition: background 0.16s, color 0.16s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      white-space: nowrap;
    }
    .tab-btn:hover { background: var(--bg); color: var(--text); }
    .tab-btn.active { background: var(--navy); color: #fff; }
    .tab-icon { font-size: 15px; }

    .panel-body {
      background: var(--surface);
      border: 1px solid var(--border);
      border-top: none;
      border-radius: 0 0 var(--r-lg) var(--r-lg);
      padding: 2rem;
      box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }

    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* ═══════════════ SECTION HEADER ═══════════════ */
    .sec-hdr {
      padding-bottom: 1.25rem;
      margin-bottom: 1.5rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 1rem;
    }
    .sec-title { font-size: 17px; font-weight: 600; color: var(--text); letter-spacing: -0.3px; margin-bottom: 3px; }
    .sec-desc  { font-size: 13px; color: var(--text-muted); line-height: 1.5; max-width: 540px; }
    .sec-badge {
      flex-shrink: 0;
      background: var(--teal-pale);
      border: 1px solid var(--teal-border);
      color: var(--teal-hover);
      border-radius: 20px;
      padding: 4px 12px;
      font-size: 11.5px;
      font-weight: 500;
      white-space: nowrap;
    }

    /* ═══════════════ FORM ELEMENTS ═══════════════ */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.25rem;
      margin-bottom: 1.25rem;
    }
    .fg { display: flex; flex-direction: column; gap: 6px; }
    .fg.full { grid-column: 1 / -1; }

    label {
      font-size: 12.5px;
      font-weight: 500;
      color: var(--text-mid);
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .lbl-hint {
      font-weight: 400;
      color: var(--text-faint);
      font-size: 12px;
    }

    input[type="text"],
    input[type="number"] {
      width: 100%;
      padding: 9px 12px;
      border: 1px solid var(--border-str);
      border-radius: var(--r-sm);
      font-family: 'DM Sans', sans-serif;
      font-size: 14px;
      color: var(--text);
      background: #fff;
      transition: border-color 0.15s, box-shadow 0.15s;
      outline: none;
    }
    input[type="text"]:focus,
    input[type="number"]:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 3px rgba(13,148,136,0.13);
    }
    input::placeholder { color: var(--text-faint); }

    /* ═══════════════ SKILLS ═══════════════ */
    .skills-wrap {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 1rem 1.125rem;
      margin-bottom: 1.25rem;
    }
    .skills-topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.875rem;
    }
    .skills-lbl  { font-size: 13px; font-weight: 500; color: var(--text-mid); }
    .skills-count {
      background: var(--navy);
      color: #fff;
      border-radius: 20px;
      padding: 2px 10px;
      font-size: 11.5px;
      font-weight: 500;
      min-width: 28px;
      text-align: center;
    }
    .skills-count.zero { background: var(--border-str); color: var(--text-muted); }

    #skills {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      min-height: 42px;
    }

    .skill-chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 12.5px;
      font-weight: 500;
      cursor: pointer;
      border: 1.5px solid var(--border-str);
      background: #fff;
      color: var(--text-mid);
      transition: border-color 0.14s, background 0.14s, color 0.14s;
      user-select: none;
    }
    .skill-chip:hover { border-color: var(--teal); color: var(--teal); background: var(--teal-pale); }
    .skill-chip.selected { background: var(--teal); border-color: var(--teal); color: #fff; }
    .chip-check { font-size: 10px; opacity: 0; }
    .skill-chip.selected .chip-check { opacity: 1; }

    .quickadd-row {
      margin-top: 0.875rem;
      padding-top: 0.875rem;
      border-top: 1px solid var(--border);
    }
    .quickadd-lbl { font-size: 11.5px; color: var(--text-muted); margin-bottom: 7px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
    .quickadd-btns { display: flex; flex-wrap: wrap; gap: 6px; }
    .qa-btn {
      padding: 4px 11px;
      border: 1px solid var(--border-str);
      border-radius: var(--r-sm);
      background: #fff;
      font-family: 'DM Sans', sans-serif;
      font-size: 12px;
      color: var(--text-mid);
      cursor: pointer;
      transition: all 0.14s;
    }
    .qa-btn:hover { border-color: var(--teal); color: var(--teal); background: var(--teal-pale); }

    /* ═══════════════ UPLOAD ZONE ═══════════════ */
    .upload-zone {
      border: 2px dashed var(--border-str);
      border-radius: var(--r);
      padding: 1.75rem 1.5rem;
      text-align: center;
      background: var(--bg);
      cursor: pointer;
      position: relative;
      transition: border-color 0.16s, background 0.16s;
    }
    .upload-zone:hover,
    .upload-zone.dragover { border-color: var(--teal); background: var(--teal-pale); }
    .upload-zone.has-files { border-color: var(--success); background: var(--success-bg); border-style: solid; }

    .upload-zone input[type="file"] {
      position: absolute;
      inset: 0;
      width: 100%; height: 100%;
      opacity: 0;
      cursor: pointer;
      border: none; padding: 0;
    }

    .uz-icon  { font-size: 30px; margin-bottom: 8px; display: block; }
    .uz-title { font-size: 14px; font-weight: 500; color: var(--text); margin-bottom: 3px; }
    .uz-hint  { font-size: 12px; color: var(--text-muted); }

    .fmt-row { display: flex; justify-content: center; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .fmt-tag {
      background: #fff;
      border: 1px solid var(--border-str);
      border-radius: 4px;
      padding: 2px 9px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-mid);
      letter-spacing: 0.4px;
    }

    /* ═══════════════ BUTTONS ═══════════════ */
    .action-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border);
      flex-wrap: wrap;
    }

    .btn-primary {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 11px 22px;
      background: var(--navy);
      color: #fff;
      border: none;
      border-radius: var(--r-sm);
      font-family: 'DM Sans', sans-serif;
      font-size: 14px; font-weight: 500;
      cursor: pointer;
      transition: background 0.16s, transform 0.1s;
      letter-spacing: -0.1px;
    }
    .btn-primary:hover { background: var(--navy-light); }
    .btn-primary:active { transform: scale(0.98); }

    .btn-teal {
      display: inline-flex; align-items: center; gap: 8px;
      padding: 11px 22px;
      background: var(--teal);
      color: #fff;
      border: none;
      border-radius: var(--r-sm);
      font-family: 'DM Sans', sans-serif;
      font-size: 14px; font-weight: 500;
      cursor: pointer;
      transition: background 0.16s, transform 0.1s;
    }
    .btn-teal:hover { background: var(--teal-hover); }
    .btn-teal:active { transform: scale(0.98); }

    .btn-ghost {
      display: inline-flex; align-items: center; gap: 7px;
      padding: 10px 18px;
      background: #fff;
      color: var(--text-mid);
      border: 1px solid var(--border-str);
      border-radius: var(--r-sm);
      font-family: 'DM Sans', sans-serif;
      font-size: 13.5px; font-weight: 500;
      cursor: pointer;
      transition: all 0.14s;
    }
    .btn-ghost:hover { border-color: var(--teal); color: var(--teal); background: var(--teal-pale); }

    /* ═══════════════ RESULT AREA ═══════════════ */
    .result-wrap {
      margin-top: 1.25rem;
    }
    .result-label {
      font-size: 11.5px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-faint);
      margin-bottom: 6px;
    }
    .result-box {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 1rem 1.25rem;
      min-height: 60px;
      font-size: 13.5px;
      color: var(--text-muted);
      font-style: italic;
    }
    .result-box:empty::before { content: 'Screening results and download links will appear here.'; }

    /* ═══════════════ NOTICE / INFO ═══════════════ */
    .info-box {
      background: var(--info-bg);
      border: 1px solid var(--info-border);
      border-radius: var(--r);
      padding: 0.875rem 1rem;
      font-size: 12.5px;
      color: #1e40af;
      line-height: 1.55;
      margin-bottom: 1.25rem;
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }
    .warn-box {
      background: var(--warning-bg);
      border: 1px solid #fcd34d;
      border-radius: var(--r);
      padding: 0.875rem 1rem;
      font-size: 12.5px;
      color: var(--warning);
      line-height: 1.55;
      margin-bottom: 1.25rem;
      display: flex;
      gap: 8px;
      align-items: flex-start;
    }

    .divider { height: 1px; background: var(--border); margin: 1.25rem 0; }

    /* ═══════════════ FOOTER ═══════════════ */
    .app-footer {
      text-align: center;
      padding: 1.5rem;
      font-size: 12px;
      color: var(--text-faint);
      border-top: 1px solid var(--border);
      margin-top: 1rem;
    }

    /* ═══════════════ RESPONSIVE ═══════════════ */
    @media (max-width: 860px) {
      .app-body { grid-template-columns: 1fr; padding: 1rem; gap: 1rem; }
      .sidebar { order: 2; position: static; }
      .main-panel { order: 1; }
      .form-grid { grid-template-columns: 1fr; }
      .tab-btn .tab-lbl { display: none; }
      .sec-hdr { flex-direction: column; align-items: flex-start; gap: 6px; }
      .header-pills .pill:last-child { display: none; }
    }
    @media (max-width: 480px) {
      .app-header { padding: 0 1rem; }
      .brand-sub { display: none; }
      .panel-body { padding: 1.25rem; }
      .action-row { flex-direction: column; align-items: stretch; }
      .btn-primary, .btn-teal, .btn-ghost { justify-content: center; }
    }
  </style>
</head>
<body>

<!-- ═══════════════════════════ HEADER ═══════════════════════════ -->
<header class="app-header">
  <div class="header-brand">
    <div class="brand-mark">TS</div>
    <div class="brand-text">
      <span class="brand-name">HR TalentScan</span>
      <span class="brand-sub">Resume Intelligence Platform</span>
    </div>
  </div>
  <div class="header-pills">
    <span class="pill accent">⚡ AI-Powered</span>
    <span class="pill">HR Screening System</span>
  </div>
</header>

<!-- ═══════════════════════════ BODY ═══════════════════════════ -->
<div class="app-body">

  <!-- ── SIDEBAR ────────────────────────────────────── -->
  <aside class="sidebar">

    <div class="sidebar-card">
      <div class="sidebar-heading">System Limits</div>
      <div class="stat-item">
        <span class="stat-icon">📄</span>
        <div class="stat-body">
          <div class="stat-val">1,000,000 files</div>
          <div class="stat-desc">Resume upload limit per batch</div>
        </div>
      </div>
      <div class="stat-item blue">
        <span class="stat-icon">📊</span>
        <div class="stat-body">
          <div class="stat-val">1,000,000</div>
          <div class="stat-desc">Candidate rows via CSV mode</div>
        </div>
      </div>
      <div class="stat-item purple">
        <span class="stat-icon">⬇️</span>
        <div class="stat-body">
          <div class="stat-val">Excel / CSV</div>
          <div class="stat-desc">Ranked results output format</div>
        </div>
      </div>
    </div>

    <div class="sidebar-card">
      <div class="sidebar-heading">Capabilities</div>
      <div class="feature-list">
        <div class="feat-row">
          <span class="feat-icon">📋</span>
          <span>Screen TXT, DOCX &amp; PDF resumes</span>
        </div>
        <div class="feat-row">
          <span class="feat-icon">📊</span>
          <span>Bulk CSV screening — up to 1M candidate rows</span>
        </div>
        <div class="feat-row">
          <span class="feat-icon">🔄</span>
          <span>Convert readable PDFs into structured CSV</span>
        </div>
        <div class="feat-row">
          <span class="feat-icon">⬇️</span>
          <span>Download ranked results as Excel workbook</span>
        </div>
        <div class="feat-row">
          <span class="feat-icon">🎯</span>
          <span>Skill matching, experience filtering &amp; scoring</span>
        </div>
      </div>
    </div>

    <div class="notice">
      <strong>ℹ️ Limit clarification:</strong> Resume file upload and CSV screening are
      both configured with a <strong>1,000,000 item limit</strong>. Actual performance
      depends on browser memory and your computer.
    </div>

  </aside>

  <!-- ── MAIN PANEL ─────────────────────────────────── -->
  <main class="main-panel">

    <div class="tab-bar">
      <button class="tab-btn active" id="tbtn-resume" onclick="switchTab('resume', this)">
        <span class="tab-icon">📋</span>
        <span class="tab-lbl">Resume Screening</span>
      </button>
      <button class="tab-btn" id="tbtn-csv" onclick="switchTab('csv', this)">
        <span class="tab-icon">📊</span>
        <span class="tab-lbl">CSV Screening</span>
      </button>
      <button class="tab-btn" id="tbtn-pdf" onclick="switchTab('pdf', this)">
        <span class="tab-icon">🔄</span>
        <span class="tab-lbl">PDF → CSV</span>
      </button>
    </div>

    <div class="panel-body">

      <!-- ═══════════ TAB 1 : RESUME SCREENING ═══════════ -->
      <div id="tab-resume" class="tab-pane active">

        <div class="sec-hdr">
          <div>
            <div class="sec-title">Resume Screening</div>
            <div class="sec-desc">
              Define your job requirements, select required skills, and upload up to 1,000,000
              resume files. The system will rank and score candidates automatically.
            </div>
          </div>
          <span class="sec-badge">Max 1,000,000 Files</span>
        </div>

        <!-- Job details -->
        <div class="form-grid">
          <div class="fg">
            <label for="jobTitle">Job Title</label>
            <input type="text" id="jobTitle" value="Full Stack Developer" placeholder="e.g. Senior Software Engineer" />
          </div>
          <div class="fg">
            <label for="minExperience">
              Minimum Experience
              <span class="lbl-hint">(years)</span>
            </label>
            <input type="number" id="minExperience" value="2" placeholder="e.g. 3" min="0" step="1" />
          </div>
          <div class="fg full">
            <label for="preferredSkills">
              Preferred Skills
              <span class="lbl-hint">— comma-separated, optional bonus skills</span>
            </label>
            <input type="text" id="preferredSkills" value="Docker" placeholder="e.g. AWS, Docker, Kubernetes, REST API" />
          </div>
        </div>

        <!-- Required skills -->
        <div class="skills-wrap">
          <div class="skills-topbar">
            <span class="skills-lbl">Required Skills — click chips to select</span>
            <span class="skills-count zero" id="selectedCount">0</span>
          </div>
          <div id="skills"></div>

          <div class="quickadd-row">
            <div class="quickadd-lbl">Quick-add skill sets</div>
            <div class="quickadd-btns">
              <button class="qa-btn" onclick="selectCommon('web')">🌐 Web Dev</button>
              <button class="qa-btn" onclick="selectCommon('data')">📊 Data Science</button>
              <button class="qa-btn" onclick="selectCommon('devops')">⚙️ DevOps</button>
              <button class="qa-btn" onclick="selectCommon('mobile')">📱 Mobile</button>
              <button class="qa-btn" onclick="selectCommon('backend')">🖥️ Backend</button>
              <button class="qa-btn" onclick="selectCommon('ml')">🤖 ML / AI</button>
              <button class="qa-btn" onclick="clearSkills()">✕ Clear all</button>
            </div>
          </div>
        </div>

        <!-- Extra skills -->
        <div class="fg">
          <label for="extraSkills">
            Additional Required Skills
            <span class="lbl-hint">— comma-separated, skills not in the list above</span>
          </label>
          <input type="text" id="extraSkills" placeholder="e.g. GraphQL, Terraform, Apache Kafka" />
        </div>

        <div class="divider"></div>

        <!-- Upload -->
        <div class="fg">
          <label>Upload Resume Files <span class="lbl-hint">— TXT, DOCX, or PDF — up to 1,000,000 files</span></label>
          <div class="upload-zone" id="uzResume">
            <input type="file" id="resumeFiles" multiple
              accept=".txt,.docx,.pdf"
              onchange="handleFileChange('resumeFiles','uzResume','uzResumeTitle')" />
            <span class="uz-icon">📂</span>
            <div class="uz-title" id="uzResumeTitle">Drag &amp; drop files here, or click to browse</div>
            <div class="uz-hint">One resume per file — each candidate's resume as a separate document</div>
            <div class="fmt-row">
              <span class="fmt-tag">PDF</span>
              <span class="fmt-tag">DOCX</span>
              <span class="fmt-tag">TXT</span>
            </div>
          </div>
        </div>

        <div class="action-row">
          <button class="btn-primary" onclick="screenBatch()">
            ▶ &nbsp;Run Candidate Screening
          </button>
          <button class="btn-ghost" onclick="resetUpload('resumeFiles','uzResume','uzResumeTitle','Drag &amp; drop files here, or click to browse')">
            ✕ Clear Files
          </button>
        </div>

        <div class="result-wrap">
          <div class="result-label">Output</div>
          <div class="result-box" id="out"></div>
        </div>

      </div>
      <!-- /tab-resume -->

      <!-- ═══════════ TAB 2 : CSV SCREENING ═══════════ -->
      <div id="tab-csv" class="tab-pane">

        <div class="sec-hdr">
          <div>
            <div class="sec-title">CSV Candidate Screening</div>
            <div class="sec-desc">
              Upload a structured CSV file containing candidate data. Ideal for high-volume
              recruitment pipelines — supports up to 1,000,000 candidate rows per file.
            </div>
          </div>
          <span class="sec-badge">Up to 1M Rows</span>
        </div>

        <div class="info-box">
          <span>📌</span>
          <span>
            Ensure your CSV includes columns for <strong>candidate name</strong>,
            <strong>skills</strong>, and <strong>years of experience</strong>.
            The screening engine maps these automatically. CSV mode supports up to 1,000,000 rows.
          </span>
        </div>

        <div class="fg">
          <label>Upload CSV File <span class="lbl-hint">— one candidate per row</span></label>
          <div class="upload-zone" id="uzCsv">
            <input type="file" id="csvDataFile" accept=".csv"
              onchange="handleFileChange('csvDataFile','uzCsv','uzCsvTitle')" />
            <span class="uz-icon">📊</span>
            <div class="uz-title" id="uzCsvTitle">Drag &amp; drop your CSV file here</div>
            <div class="uz-hint">Structured candidate data — up to 1,000,000 rows supported</div>
            <div class="fmt-row">
              <span class="fmt-tag">CSV</span>
            </div>
          </div>
        </div>

        <div class="action-row">
          <button class="btn-teal" onclick="screenCsvData()">
            ▶ &nbsp;Screen All Candidates
          </button>
          <button class="btn-ghost" onclick="resetUpload('csvDataFile','uzCsv','uzCsvTitle','Drag &amp; drop your CSV file here')">
            ✕ Clear File
          </button>
        </div>

        <div class="result-wrap">
          <div class="result-label">Output</div>
          <div class="result-box" id="csvScreenOut"></div>
        </div>

      </div>
      <!-- /tab-csv -->

      <!-- ═══════════ TAB 3 : PDF → CSV ═══════════ -->
      <div id="tab-pdf" class="tab-pane">

        <div class="sec-hdr">
          <div>
            <div class="sec-title">PDF to CSV Converter</div>
            <div class="sec-desc">
              Extract structured text from readable PDF data files and export to CSV format
              for downstream processing or CSV-mode screening.
            </div>
          </div>
          <span class="sec-badge">Text PDFs Only</span>
        </div>

        <div class="warn-box">
          <span>⚠️</span>
          <span>
            Only <strong>text-readable PDFs</strong> are supported. Scanned or image-based PDFs
            (where text cannot be selected) will not convert accurately. For image PDFs,
            pre-process with an OCR tool first.
          </span>
        </div>

        <div class="fg">
          <label>Upload PDF Data Files <span class="lbl-hint">— multiple files allowed</span></label>
          <div class="upload-zone" id="uzPdf">
            <input type="file" id="pdfDataFiles" multiple accept=".pdf"
              onchange="handleFileChange('pdfDataFiles','uzPdf','uzPdfTitle')" />
            <span class="uz-icon">🔄</span>
            <div class="uz-title" id="uzPdfTitle">Drag &amp; drop PDF files here</div>
            <div class="uz-hint">Each file will be parsed and exported as structured CSV rows</div>
            <div class="fmt-row">
              <span class="fmt-tag">PDF</span>
            </div>
          </div>
        </div>

        <div class="action-row">
          <button class="btn-teal" onclick="convertPdfToCsv()">
            🔄 &nbsp;Convert to CSV
          </button>
          <button class="btn-ghost" onclick="resetUpload('pdfDataFiles','uzPdf','uzPdfTitle','Drag &amp; drop PDF files here')">
            ✕ Clear Files
          </button>
        </div>

        <div class="result-wrap">
          <div class="result-label">Output</div>
          <div class="result-box" id="csvOut"></div>
        </div>

      </div>
      <!-- /tab-pdf -->

    </div><!-- /panel-body -->
  </main><!-- /main-panel -->

</div><!-- /app-body -->

<footer class="app-footer">
  HR TalentScan — HR AI Resume Ranking System &nbsp;·&nbsp; Final Year Project &nbsp;·&nbsp;
  All screening runs locally, no data sent to third-party services.
</footer>

<!-- ═══════════════════════════ JAVASCRIPT ═══════════════════════════ -->
<script>

  /* ── TAB SWITCHER ──────────────────────────────── */
  function switchTab(name, btn) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
  }

  /* ── SKILLS DATA ───────────────────────────────── */
  const ALL_SKILLS = [
    'Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'PHP', 'Ruby',
    'React', 'Vue.js', 'Angular', 'Node.js', 'Next.js', 'Django', 'FastAPI', 'Flask',
    'Spring Boot', 'Laravel', 'Express.js', 'ASP.NET',
    'SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Elasticsearch',
    'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP', 'CI/CD', 'Linux', 'Terraform', 'Ansible',
    'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Hugging Face',
    'Git', 'REST API', 'GraphQL', 'Microservices', 'Agile', 'Scrum',
    'Swift', 'Kotlin', 'React Native', 'Flutter',
    'HTML', 'CSS', 'Sass', 'Tailwind CSS', 'WebSockets'
  ];

  const COMMON_SETS = {
    web:     ['React', 'JavaScript', 'TypeScript', 'Node.js', 'HTML', 'CSS', 'Next.js'],
    data:    ['Python', 'SQL', 'Pandas', 'NumPy', 'Scikit-learn', 'PostgreSQL'],
    devops:  ['Docker', 'Kubernetes', 'CI/CD', 'AWS', 'Linux', 'Terraform', 'Ansible'],
    mobile:  ['Swift', 'Kotlin', 'React Native', 'Flutter'],
    backend: ['Python', 'Java', 'Node.js', 'REST API', 'PostgreSQL', 'Microservices', 'Docker'],
    ml:      ['Python', 'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy', 'Hugging Face']
  };

  let selectedSet = new Set();

  /* ── renderSkills ──────────────────────────────── */
  function renderSkills() {
    const container = document.getElementById('skills');
    container.innerHTML = '';
    ALL_SKILLS.forEach(skill => {
      const chip = document.createElement('span');
      chip.className = 'skill-chip' + (selectedSet.has(skill) ? ' selected' : '');
      chip.innerHTML = '<span class="chip-check">✓</span> ' + skill;
      chip.onclick = () => toggleSkill(skill, chip);
      container.appendChild(chip);
    });
    updateCount();
  }

  function toggleSkill(skill, chip) {
    if (selectedSet.has(skill)) {
      selectedSet.delete(skill);
      chip.classList.remove('selected');
    } else {
      selectedSet.add(skill);
      chip.classList.add('selected');
    }
    updateCount();
  }

  function updateCount() {
    const el = document.getElementById('selectedCount');
    el.textContent = selectedSet.size;
    el.className = 'skills-count' + (selectedSet.size === 0 ? ' zero' : '');
  }

  /* ── selectedSkills ────────────────────────────── */
  function selectedSkills() {
    const extra = (document.getElementById('extraSkills')?.value || '')
      .split(',')
      .map(x => x.trim())
      .filter(Boolean);
    return Array.from(new Set([...selectedSet, ...extra]));
  }

  /* ── selectCommon ──────────────────────────────── */
  function selectCommon(category) {
    const skills = COMMON_SETS[category] || [];
    skills.forEach(s => selectedSet.add(s));
    renderSkills();
  }

  function clearSkills() {
    selectedSet.clear();
    renderSkills();
  }

  /* ── FILE INPUT HELPERS ────────────────────────── */
  function handleFileChange(inputId, zoneId, titleId) {
    const input = document.getElementById(inputId);
    const zone  = document.getElementById(zoneId);
    const title = document.getElementById(titleId);
    if (!input || !input.files.length) return;
    const n = input.files.length;
    title.textContent = n === 1 ? input.files[0].name : n + ' files selected';
    zone.classList.add('has-files');
  }

  function resetUpload(inputId, zoneId, titleId, defaultText) {
    const input = document.getElementById(inputId);
    const zone  = document.getElementById(zoneId);
    const title = document.getElementById(titleId);
    if (input) input.value = '';
    if (zone)  zone.classList.remove('has-files');
    if (title) title.innerHTML = defaultText;
  }

  /* ── DRAG-OVER EFFECTS ─────────────────────────── */
  document.querySelectorAll('.upload-zone').forEach(zone => {
    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop',      () => zone.classList.remove('dragover'));
  });

  function screenBatch() {
    const out = document.getElementById('out');
    const files = document.getElementById('resumeFiles').files;
    const req = selectedSkills();
    if (!files.length) {
      alert('Please choose at least one resume file.');
      return;
    }
    if (files.length > 1000000) {
      alert('Maximum 1,000,000 resumes allowed.');
      return;
    }
    if (!req.length) {
      alert('Please select at least one required skill.');
      return;
    }
    const form = new FormData();
    for (const file of files) form.append('resumes', file);
    form.append('job_title', document.getElementById('jobTitle').value || 'Selected Job');
    form.append('required_skills', req.join(','));
    form.append('preferred_skills', document.getElementById('preferredSkills').value || '');
    form.append('min_experience_yrs', document.getElementById('minExperience').value || '0');
    out.style.fontStyle = 'normal';
    out.textContent = 'Screening ' + files.length + ' resume file(s). Please wait...';
    fetch('/screen-batch', { method: 'POST', body: form })
      .then(async res => {
        if (!res.ok) {
          const error = await res.json();
          throw new Error(JSON.stringify(error, null, 2));
        }
        return res.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'resume_screening_results.xlsx';
        a.click();
        URL.revokeObjectURL(url);
        out.textContent = 'Done. Excel file downloaded: resume_screening_results.xlsx';
      })
      .catch(err => { out.textContent = err.message || String(err); });
  }

  function convertPdfToCsv() {
    const out = document.getElementById('csvOut');
    const files = document.getElementById('pdfDataFiles').files;
    if (!files.length) {
      alert('Please choose at least one PDF file.');
      return;
    }
    const form = new FormData();
    for (const file of files) form.append('pdf_files', file);
    out.style.fontStyle = 'normal';
    out.textContent = 'Converting ' + files.length + ' PDF file(s) to CSV. Please wait...';
    fetch('/pdf-to-csv', { method: 'POST', body: form })
      .then(async res => {
        if (!res.ok) {
          const error = await res.json();
          throw new Error(JSON.stringify(error, null, 2));
        }
        return res.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pdf_data_output.csv';
        a.click();
        URL.revokeObjectURL(url);
        out.textContent = 'Done. CSV file downloaded: pdf_data_output.csv';
      })
      .catch(err => { out.textContent = err.message || String(err); });
  }

  function screenCsvData() {
    const out = document.getElementById('csvScreenOut');
    const input = document.getElementById('csvDataFile');
    const req = selectedSkills();
    if (!input.files.length) {
      alert('Please choose one CSV file.');
      return;
    }
    if (!req.length) {
      alert('Please select at least one required skill in Resume Screening first.');
      return;
    }
    const form = new FormData();
    form.append('csv_file', input.files[0]);
    form.append('job_title', document.getElementById('jobTitle').value || 'Selected Job');
    form.append('required_skills', req.join(','));
    form.append('preferred_skills', document.getElementById('preferredSkills').value || '');
    form.append('min_experience_yrs', document.getElementById('minExperience').value || '0');
    out.style.fontStyle = 'normal';
    out.textContent = 'Screening CSV rows. Please wait...';
    fetch('/screen-csv', { method: 'POST', body: form })
      .then(async res => {
        if (!res.ok) {
          const error = await res.json();
          throw new Error(JSON.stringify(error, null, 2));
        }
        return res.blob();
      })
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'csv_resume_screening_results.xlsx';
        a.click();
        URL.revokeObjectURL(url);
        out.textContent = 'Done. Excel file downloaded: csv_resume_screening_results.xlsx';
      })
      .catch(err => { out.textContent = err.message || String(err); });
  }

  /* ── INIT ──────────────────────────────────────── */
  renderSkills();

</script>
</body>
</html>
"""


SKILL_KEYWORDS = [
    "python", "javascript", "typescript", "node.js", "node", "react", "vue.js",
    "angular", "next.js", "html", "css", "sass", "tailwind css", "sql",
    "sqlite", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "express", "express.js", "rest api", "api", "graphql", "java", "c++",
    "c#", "go", "rust", "php", "ruby", "swift", "kotlin", "react native",
    "flutter", "spring boot", "laravel", "asp.net", "docker", "kubernetes",
    "aws", "azure", "gcp", "ci/cd", "linux", "terraform", "ansible", "git",
    "machine learning", "ml", "ai", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "hugging face", "flask", "fastapi",
    "django", "microservices", "agile", "scrum", "websockets",
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


def decode_pdf_literal_string(value):
    out = bytearray()
    i = 0
    while i < len(value):
        byte = value[i]
        if byte == 92 and i + 1 < len(value):
            i += 1
            escaped = value[i]
            mapping = {110: 10, 114: 13, 116: 9, 98: 8, 102: 12, 40: 40, 41: 41, 92: 92}
            if escaped in mapping:
                out.append(mapping[escaped])
            elif 48 <= escaped <= 55:
                octal = bytes([escaped])
                for _ in range(2):
                    if i + 1 < len(value) and 48 <= value[i + 1] <= 55:
                        i += 1
                        octal += bytes([value[i]])
                    else:
                        break
                out.append(int(octal, 8))
            else:
                out.append(escaped)
        else:
            out.append(byte)
        i += 1
    return decode_pdf_bytes(bytes(out))


def decode_pdf_bytes(value):
    if not value:
        return ""
    if value.startswith(b"\xfe\xff"):
        return value[2:].decode("utf-16-be", errors="ignore")
    if value.startswith(b"\xff\xfe"):
        return value[2:].decode("utf-16-le", errors="ignore")
    if len(value) > 2 and value[0] == 0 and value[2::2]:
        decoded = value.decode("utf-16-be", errors="ignore")
        if len(re.findall(r"[A-Za-z0-9]", decoded)) >= 2:
            return decoded
    return value.decode("latin-1", errors="ignore")


def extract_pdf_text_from_stream(stream):
    text_parts = []
    content = stream.replace(b"\\\r\n", b"").replace(b"\\\n", b"")
    blocks = re.findall(rb"BT(.*?)ET", content, flags=re.S) or [content]
    for block in blocks:
        block = re.sub(rb"\bT\*|\bTd\b|\bTD\b", b"\n", block)
        for literal in re.findall(rb"\((?:\\.|[^\\)])*\)", block, flags=re.S):
            text = decode_pdf_literal_string(literal[1:-1]).strip()
            if text:
                text_parts.append(text)
        for hex_value in re.findall(rb"<([0-9A-Fa-f\s]+)>", block):
            compact = re.sub(rb"\s+", b"", hex_value)
            if len(compact) < 4 or len(compact) % 2:
                continue
            try:
                text = decode_pdf_bytes(bytes.fromhex(compact.decode())).strip()
            except ValueError:
                continue
            if text and len(re.findall(r"[A-Za-z0-9]", text)) >= 2:
                text_parts.append(text)
    return "\n".join(text_parts)


def extract_text_from_pdf_streams(data):
    text_parts = []
    pattern = re.compile(rb"<<(?P<dict>.*?)>>\s*stream\r?\n(?P<body>.*?)\r?\nendstream", re.S)
    for match in pattern.finditer(data):
        stream_dict = match.group("dict")
        body = match.group("body").strip(b"\r\n")
        stream_data = body
        if b"FlateDecode" in stream_dict:
            try:
                stream_data = zlib.decompress(body)
            except zlib.error:
                continue
        extracted = extract_pdf_text_from_stream(stream_data)
        if extracted:
            text_parts.append(extracted)
    return "\n".join(text_parts)


def looks_like_pdf_internal_line(line):
    stripped = line.strip()
    if not stripped:
        return True
    internal_patterns = [
        r"^%?PDF-\d", r"^\d+\s+\d+\s+obj$", r"^endobj$", r"^stream$", r"^endstream$",
        r"^xref$", r"^trailer$", r"^startxref$", r"^/[^ ]+", r"^<<", r"^>>$",
        r"^\[?\d+\s+\d+\s+R\]?$", r"^[A-Za-z0-9+/]{20,}={0,2}$",
    ]
    return any(re.search(pattern, stripped) for pattern in internal_patterns)


def extract_text_from_pdf(data):
    try:
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        if text.strip():
            return text
    except Exception:
        pass

    stream_text = extract_text_from_pdf_streams(data)
    if stream_text.strip():
        return stream_text

    raw = data.decode("latin-1", errors="ignore")
    chunks = re.findall(r"[A-Za-z0-9@.+#,/()\- ]{4,}", raw)
    readable = [chunk.strip() for chunk in chunks if not looks_like_pdf_internal_line(chunk)]
    readable_text = "\n".join(readable)
    letters = len(re.findall(r"[A-Za-z]", readable_text))
    if letters < 20:
        return ""
    return readable_text


def extract_text_from_file_bytes(filename, data):
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "txt":
        return data.decode("utf-8", errors="ignore")
    if ext == "docx":
        return extract_text_from_docx(data)
    if ext == "pdf":
        return extract_text_from_pdf(data)
    raise ValueError("Only TXT, DOCX, and PDF files are supported")


def pdf_text_to_rows(filename, text):
    rows = []
    for line_number, line in enumerate(clean_text(text).splitlines(), start=1):
        line = line.strip()
        if not line or looks_like_pdf_internal_line(line):
            continue
        parts = re.split(r"\s{2,}|\t+|[,|;]+", line)
        parts = [part.strip() for part in parts if part.strip()]
        if not parts:
            continue
        rows.append([filename, line_number] + parts)
    if not rows and text.strip():
        words = re.findall(r"\S+", text)
        for index in range(0, len(words), 8):
            rows.append([filename, (index // 8) + 1] + words[index:index + 8])
    return rows


def rows_to_csv(headers, rows):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return output.getvalue()


def parse_csv_text(text):
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(StringIO(text), dialect=dialect)
    if reader.fieldnames:
        return list(reader), reader.fieldnames
    simple_reader = csv.reader(StringIO(text), dialect=dialect)
    rows = []
    for index, row in enumerate(simple_reader, start=1):
        rows.append({"row_number": str(index), "resume_text": " ".join(row)})
    return rows, ["row_number", "resume_text"]


def row_text_for_screening(row):
    priority_columns = [
        "resume_text", "text", "resume", "description", "summary", "profile",
        "skills", "experience", "education", "candidate", "name",
    ]
    lower_map = {key.lower().strip(): value for key, value in row.items() if value is not None}
    chosen = []
    for column in priority_columns:
        if lower_map.get(column):
            chosen.append(str(lower_map[column]))
    if chosen:
        return " ".join(chosen)
    return " ".join(str(value) for value in row.values() if value is not None)


def row_candidate_name(row, index):
    for key in ("name", "candidate_name", "candidate", "full_name"):
        for real_key, value in row.items():
            if real_key.lower().strip() == key and value:
                return str(value)
    return f"CSV Row {index}"


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


def add_common_headers(handler):
    request_id = getattr(handler, "request_id", None) or str(uuid.uuid4())
    handler.send_header("X-Request-ID", request_id)
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key")


def api_docs():
    return {
        "name": "HR AI Resume Ranking API",
        "version": APP_VERSION,
        "limits": {
            "max_request_bytes": MAX_REQUEST_BYTES,
            "max_resume_files_per_batch": MAX_RESUME_FILES,
            "max_csv_screening_rows": MAX_CSV_SCREENING_ROWS,
        },
        "public_endpoints": [
            {"method": "GET", "path": "/", "description": "Professional browser UI"},
            {"method": "GET", "path": "/health", "description": "Service health and runtime metadata"},
            {"method": "GET", "path": "/api/docs", "description": "Machine-readable route catalog"},
            {"method": "POST", "path": "/screen-resume", "description": "Screen one TXT, DOCX, or PDF resume"},
            {"method": "POST", "path": "/screen-batch", "description": "Screen up to 1,000,000 resume files and download XLSX"},
            {"method": "POST", "path": "/pdf-to-csv", "description": "Convert readable PDF data files into CSV"},
            {"method": "POST", "path": "/screen-csv", "description": "Screen CSV candidate rows and download XLSX"},
        ],
        "authenticated_endpoints": [
            {"method": "POST", "path": "/auth/register"},
            {"method": "POST", "path": "/auth/login"},
            {"method": "POST", "path": "/candidates"},
            {"method": "GET", "path": "/candidates"},
            {"method": "POST", "path": "/jobs"},
            {"method": "GET", "path": "/jobs"},
            {"method": "POST", "path": "/resumes/upload"},
            {"method": "GET", "path": "/resumes/<resume_id>"},
            {"method": "POST", "path": "/ranking/job/<job_id>/rank-candidate/<candidate_id>"},
        ],
    }


def json_response(handler, status, payload):
    data = json.dumps(payload, default=str).encode()
    handler.send_response(status)
    add_common_headers(handler)
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
    add_common_headers(handler)
    handler.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(content)))
    handler.end_headers()
    handler.wfile.write(content)


def csv_response(handler, filename, text):
    data = text.encode("utf-8-sig")
    handler.send_response(200)
    add_common_headers(handler)
    handler.send_header("Content-Type", "text/csv; charset=utf-8")
    handler.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def html_response(handler, status, html):
    data = html.encode("utf-8")
    handler.send_response(status)
    add_common_headers(handler)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def row_to_dict(row):
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


class MultipartItem:
    def __init__(self, name, value=b"", filename=None):
        self.name = name
        self.filename = filename
        self.file = BytesIO(value)
        self.value = value.decode("utf-8", errors="ignore")


class RequestTooLarge(Exception):
    pass


class MultipartForm:
    def __init__(self):
        self.items = {}

    def add(self, item):
        if item.name in self.items:
            existing = self.items[item.name]
            if isinstance(existing, list):
                existing.append(item)
            else:
                self.items[item.name] = [existing, item]
        else:
            self.items[item.name] = item

    def __contains__(self, key):
        return key in self.items

    def __getitem__(self, key):
        return self.items[key]

    def getvalue(self, key, default=None):
        item = self.items.get(key)
        if item is None:
            return default
        if isinstance(item, list):
            item = item[0]
        return item.value


def parse_header_value(header):
    parts = [part.strip() for part in header.split(";") if part.strip()]
    main = parts[0].lower() if parts else ""
    params = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        params[key.strip().lower()] = value.strip().strip('"')
    return main, params


def parse_multipart_form(handler):
    ctype, params = parse_header_value(handler.headers.get("Content-Type", ""))
    if ctype != "multipart/form-data":
        return None
    boundary = params.get("boundary")
    if not boundary:
        return None
    length = int(handler.headers.get("Content-Length", "0"))
    if length > MAX_REQUEST_BYTES:
        raise RequestTooLarge(f"Request body is too large. Maximum allowed size is {MAX_REQUEST_BYTES} bytes.")
    body = handler.rfile.read(length)
    boundary_bytes = b"--" + boundary.encode()
    form = MultipartForm()

    for part in body.split(boundary_bytes):
        part = part.strip()
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip()
        if b"\r\n\r\n" in part:
            raw_headers, value = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            raw_headers, value = part.split(b"\n\n", 1)
        else:
            continue
        value = value.rstrip(b"\r\n")
        headers = {}
        for line in raw_headers.decode("utf-8", errors="ignore").splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                headers[key.strip().lower()] = val.strip()
        disposition, disp_params = parse_header_value(headers.get("content-disposition", ""))
        if disposition != "form-data":
            continue
        name = disp_params.get("name")
        if not name:
            continue
        form.add(MultipartItem(name=name, value=value, filename=disp_params.get("filename")))
    return form


class App(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def handle_one_request(self):
        self.request_id = str(uuid.uuid4())
        super().handle_one_request()

    def send_json(self, status, payload):
        json_response(self, status, payload)

    def send_html(self, status, html):
        html_response(self, status, html)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise RequestTooLarge(f"Request body is too large. Maximum allowed size is {MAX_REQUEST_BYTES} bytes.")
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def do_OPTIONS(self):
        self.send_response(204)
        add_common_headers(self)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
                self.send_json(200, {
                    "status": "healthy",
                    "version": APP_VERSION,
                    "service": "hr-ai-resume-ranking-api",
                    "request_id": self.request_id,
                    "time": now(),
                    "limits": {
                        "max_request_bytes": MAX_REQUEST_BYTES,
                        "max_resume_files_per_batch": MAX_RESUME_FILES,
                        "max_csv_screening_rows": MAX_CSV_SCREENING_ROWS,
                    },
                })
            elif path == "/api/docs":
                self.send_json(200, api_docs())
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
        except RequestTooLarge as exc:
            status = 413
            self.send_json(413, {"error": "Request too large", "message": str(exc), "request_id": self.request_id})
        except Exception as exc:
            status = 500
            self.send_json(500, {"error": "Internal server error", "message": str(exc), "request_id": self.request_id})
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
            elif path == "/pdf-to-csv":
                self.handle_pdf_to_csv()
            elif path == "/screen-csv":
                self.handle_screen_csv()
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
        except RequestTooLarge as exc:
            status = 413
            self.send_json(413, {"error": "Request too large", "message": str(exc), "request_id": self.request_id})
        except Exception as exc:
            status = 500
            self.send_json(500, {"error": "Internal server error", "message": str(exc), "request_id": self.request_id})
        finally:
            self.log_request_row(status, start)

    def handle_upload(self):
        form = parse_multipart_form(self)
        if form is None:
            self.send_json(400, {"error": "multipart/form-data required"})
            return
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
        form = parse_multipart_form(self)
        if form is None:
            self.send_json(400, {"error": "multipart/form-data required"})
            return

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
        form = parse_multipart_form(self)
        if form is None:
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        files = form["resumes"] if "resumes" in form else []
        if not isinstance(files, list):
            files = [files]
        files = [item for item in files if item is not None and item.filename]

        if not files:
            self.send_json(400, {"error": "Please upload at least one resume"})
            return
        if len(files) > MAX_RESUME_FILES:
            self.send_json(400, {"error": f"Maximum {MAX_RESUME_FILES} resumes are allowed in one screening batch"})
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

    def handle_pdf_to_csv(self):
        form = parse_multipart_form(self)
        if form is None:
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        files = form["pdf_files"] if "pdf_files" in form else []
        if not isinstance(files, list):
            files = [files]
        files = [item for item in files if item is not None and item.filename]
        if not files:
            self.send_json(400, {"error": "Please upload at least one PDF file"})
            return

        rows = []
        max_columns = 0
        for file_item in files:
            filename = file_item.filename
            ext = Path(filename).suffix.lower().lstrip(".")
            if ext != "pdf":
                rows.append([filename, "", "ERROR", "Only PDF files are supported"])
                max_columns = max(max_columns, 2)
                continue
            try:
                text = extract_text_from_pdf(file_item.file.read())
                extracted_rows = pdf_text_to_rows(filename, text)
                if not extracted_rows:
                    rows.append([filename, "", "ERROR", "No readable text could be extracted"])
                    max_columns = max(max_columns, 2)
                    continue
                rows.extend(extracted_rows)
                max_columns = max(max_columns, max(len(row) - 2 for row in extracted_rows))
            except Exception as exc:
                rows.append([filename, "", "ERROR", str(exc)])
                max_columns = max(max_columns, 2)

        headers = ["source_file", "line_number"] + [f"column_{index}" for index in range(1, max_columns + 1)]
        normalized = []
        for row in rows:
            normalized.append(row + [""] * (len(headers) - len(row)))
        csv_response(self, "pdf_data_output.csv", rows_to_csv(headers, normalized))

    def handle_screen_csv(self):
        form = parse_multipart_form(self)
        if form is None:
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        file_item = form["csv_file"] if "csv_file" in form else None
        if file_item is None or not file_item.filename:
            self.send_json(400, {"error": "Please upload a CSV file"})
            return
        if Path(file_item.filename).suffix.lower() != ".csv":
            self.send_json(400, {"error": "Only CSV files are supported here"})
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

        text = file_item.file.read().decode("utf-8-sig", errors="ignore")
        csv_rows, fieldnames = parse_csv_text(text)
        if not csv_rows:
            self.send_json(400, {"error": "CSV file has no data rows"})
            return
        if len(csv_rows) > MAX_CSV_SCREENING_ROWS:
            self.send_json(400, {"error": f"Maximum {MAX_CSV_SCREENING_ROWS} CSV rows are allowed in one screening batch"})
            return

        headers = [
            "No", "CSV File", "Candidate/Row", "Status", "Candidate Email", "Phone",
            "Extracted Skills", "Years Experience", "Education", "Overall Score",
            "Skill Score", "Experience Score", "Education Score", "Keyword Score",
            "Decision", "Matched Required Skills", "Missing Required Skills",
            "Matched Preferred Skills", "Recommendation", "Source Text", "Error",
        ]
        result_rows = []
        for index, row in enumerate(csv_rows, start=1):
            try:
                source_text = row_text_for_screening(row)
                if not source_text.strip():
                    raise ValueError("No readable screening text found in this CSV row")
                parsed, cleaned = parse_resume_text(source_text)
                ranking = score_resume(parsed, required, preferred, min_exp, job_title)
                contact = parsed.get("contact", {})
                result_rows.append([
                    index,
                    file_item.filename,
                    row_candidate_name(row, index),
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
                    source_text[:500],
                    "",
                ])
            except Exception as exc:
                result_rows.append([index, file_item.filename, row_candidate_name(row, index), "ERROR", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", str(exc)])

        widths = [8, 26, 26, 14, 28, 18, 45, 18, 14, 15, 12, 18, 16, 14, 18, 35, 35, 35, 65, 60, 40]
        xlsx_response(self, "csv_resume_screening_results.xlsx", create_xlsx(headers, result_rows, widths))

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
