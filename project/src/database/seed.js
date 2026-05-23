// src/database/seed.js
// Seeds the database with sample users, skills taxonomy, candidates, and job postings.

require('dotenv').config();
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const { initDatabase } = require('./schema');

const db = initDatabase();

console.log('🌱  Seeding database...');

// ── Users ─────────────────────────────────────────────────────────────────────
const adminId = uuidv4();
const recruiterId = uuidv4();
const hashedPw = bcrypt.hashSync('Password123!', 10);

db.prepare(`INSERT OR IGNORE INTO users (id, email, password, name, role, api_key) VALUES
  (?, 'admin@hrpro.com', ?, 'Admin User', 'admin', ?),
  (?, 'recruiter@hrpro.com', ?, 'Jane Recruiter', 'recruiter', ?)`
).run(adminId, hashedPw, 'sk-admin-' + uuidv4(), recruiterId, hashedPw, 'sk-rec-' + uuidv4());

// ── Skills Taxonomy ───────────────────────────────────────────────────────────
const skills = [
  { name: 'Python',          category: 'programming', aliases: '["python3","py"]' },
  { name: 'JavaScript',      category: 'programming', aliases: '["js","es6","es2015"]' },
  { name: 'TypeScript',      category: 'programming', aliases: '["ts"]' },
  { name: 'Java',            category: 'programming', aliases: '["java8","java11"]' },
  { name: 'Go',              category: 'programming', aliases: '["golang"]' },
  { name: 'Rust',            category: 'programming', aliases: '[]' },
  { name: 'React',           category: 'framework',   aliases: '["reactjs","react.js"]' },
  { name: 'Node.js',         category: 'framework',   aliases: '["nodejs","node"]' },
  { name: 'FastAPI',         category: 'framework',   aliases: '[]' },
  { name: 'Django',          category: 'framework',   aliases: '[]' },
  { name: 'PostgreSQL',      category: 'database',    aliases: '["postgres","psql"]' },
  { name: 'MongoDB',         category: 'database',    aliases: '["mongo"]' },
  { name: 'Redis',           category: 'database',    aliases: '[]' },
  { name: 'AWS',             category: 'cloud',       aliases: '["amazon web services"]' },
  { name: 'GCP',             category: 'cloud',       aliases: '["google cloud"]' },
  { name: 'Azure',           category: 'cloud',       aliases: '["microsoft azure"]' },
  { name: 'Docker',          category: 'devops',      aliases: '[]' },
  { name: 'Kubernetes',      category: 'devops',      aliases: '["k8s"]' },
  { name: 'Machine Learning',category: 'domain',      aliases: '["ml"]' },
  { name: 'NLP',             category: 'domain',      aliases: '["natural language processing"]' },
  { name: 'Communication',   category: 'soft_skill',  aliases: '[]' },
  { name: 'Leadership',      category: 'soft_skill',  aliases: '[]' },
  { name: 'Agile',           category: 'tool',        aliases: '["scrum","kanban"]' },
  { name: 'Git',             category: 'tool',        aliases: '["github","gitlab"]' },
];

const insertSkill = db.prepare(
  `INSERT OR IGNORE INTO skills (id, name, category, aliases) VALUES (?, ?, ?, ?)`
);
for (const s of skills) insertSkill.run(uuidv4(), s.name, s.category, s.aliases);

// ── Job Postings ──────────────────────────────────────────────────────────────
const jobs = [
  {
    title: 'Senior Full-Stack Engineer',
    department: 'Engineering',
    location: 'Remote',
    employment_type: 'full_time',
    description: 'Build and scale our core product platform.',
    requirements: '5+ years full-stack development. Strong React and Node.js. PostgreSQL expertise.',
    nice_to_have: 'GraphQL, Kubernetes, prior startup experience.',
    salary_min: 130000, salary_max: 180000,
    required_skills: JSON.stringify(['React','Node.js','PostgreSQL','JavaScript','Git']),
    preferred_skills: JSON.stringify(['TypeScript','Docker','AWS','Redis']),
    min_experience_yrs: 5,
    status: 'open', created_by: adminId
  },
  {
    title: 'ML Engineer — NLP',
    department: 'AI Research',
    location: 'San Francisco, CA',
    employment_type: 'full_time',
    description: 'Design and deploy NLP models for our AI product suite.',
    requirements: '3+ years ML engineering. Python, PyTorch or TensorFlow. NLP experience required.',
    nice_to_have: 'LLM fine-tuning, RAG systems, MLOps.',
    salary_min: 150000, salary_max: 220000,
    required_skills: JSON.stringify(['Python','Machine Learning','NLP','Git']),
    preferred_skills: JSON.stringify(['AWS','Docker','FastAPI','PostgreSQL']),
    min_experience_yrs: 3,
    status: 'open', created_by: adminId
  },
  {
    title: 'DevOps / Cloud Engineer',
    department: 'Infrastructure',
    location: 'Austin, TX',
    employment_type: 'full_time',
    description: 'Own our cloud infrastructure and CI/CD pipeline.',
    requirements: 'Strong Kubernetes, Terraform, AWS. 4+ years DevOps.',
    nice_to_have: 'GCP, Datadog, Go.',
    salary_min: 120000, salary_max: 160000,
    required_skills: JSON.stringify(['Kubernetes','Docker','AWS','Git']),
    preferred_skills: JSON.stringify(['Go','Python','GCP','Azure']),
    min_experience_yrs: 4,
    status: 'open', created_by: recruiterId
  },
];

const insertJob = db.prepare(`
  INSERT OR IGNORE INTO job_postings
    (id, title, department, location, employment_type, description, requirements,
     nice_to_have, salary_min, salary_max, required_skills, preferred_skills,
     min_experience_yrs, status, created_by)
  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`);

for (const j of jobs) {
  insertJob.run(uuidv4(), j.title, j.department, j.location, j.employment_type,
    j.description, j.requirements, j.nice_to_have, j.salary_min, j.salary_max,
    j.required_skills, j.preferred_skills, j.min_experience_yrs, j.status, j.created_by);
}

console.log('✅  Seed complete.');
console.log('   Admin:     admin@hrpro.com / Password123!');
console.log('   Recruiter: recruiter@hrpro.com / Password123!');
