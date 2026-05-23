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


def extract_contact(text):
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"\+?\d[\d\s.-]{8,}\d", text)
    return {
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
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


def json_response(handler, status, payload):
    data = json.dumps(payload, default=str).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
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
            if path == "/health":
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
            if path == "/auth/register":
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
        raw_text = data.decode("utf-8", errors="ignore") if ext == "txt" else ""
        try:
            parsed, cleaned = parse_resume_text(raw_text)
            status = "completed" if raw_text.strip() else "failed"
            error = None if raw_text.strip() else "Text extraction for PDF/DOCX requires external parser library."
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
