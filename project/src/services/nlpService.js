// src/services/nlpService.js
// ─────────────────────────────────────────────────────────────────────────────
//  NLP Pre-processing Pipeline
//  Handles: text extraction from PDF/DOCX/TXT, cleaning, normalisation,
//           keyword extraction, section detection
// ─────────────────────────────────────────────────────────────────────────────

const fs      = require('fs');
const path    = require('path');

// ── Text extraction ───────────────────────────────────────────────────────────

async function extractTextFromFile(filePath, fileType) {
  const buffer = fs.readFileSync(filePath);

  switch (fileType.toLowerCase()) {
    case 'pdf': {
      const pdfParse = require('pdf-parse');
      const data = await pdfParse(buffer);
      return data.text;
    }
    case 'docx': {
      const mammoth = require('mammoth');
      const result  = await mammoth.extractRawText({ buffer });
      return result.value;
    }
    case 'txt':
      return buffer.toString('utf-8');
    default:
      throw new Error(`Unsupported file type: ${fileType}`);
  }
}

// ── Text cleaning & normalisation ─────────────────────────────────────────────

function cleanText(rawText) {
  return rawText
    .replace(/\r\n/g, '\n')           // normalise line endings
    .replace(/\t/g, ' ')              // tabs → spaces
    .replace(/[ ]{2,}/g, ' ')         // collapse multiple spaces
    .replace(/\n{3,}/g, '\n\n')       // collapse excess blank lines
    .replace(/[^\x20-\x7E\n]/g, ' ')  // strip non-ASCII control chars
    .trim();
}

// ── Section detection ─────────────────────────────────────────────────────────
// Attempts to split a resume into logical sections.

const SECTION_PATTERNS = {
  contact:        /^(contact|personal info|personal details)/i,
  summary:        /^(summary|profile|objective|about me|overview)/i,
  experience:     /^(experience|work experience|employment|professional experience|work history)/i,
  education:      /^(education|academic|qualifications|degrees?)/i,
  skills:         /^(skills?|technical skills?|core competenc|technologies|stack|expertise)/i,
  certifications: /^(certif|licens|accreditation)/i,
  projects:       /^(projects?|portfolio|open.?source)/i,
  awards:         /^(awards?|honors?|achievements?|recognit)/i,
  languages:      /^(languages?|spoken)/i,
  references:     /^(references?)/i,
};

function detectSections(text) {
  const lines    = text.split('\n');
  const sections = {};
  let current    = 'header';
  let buffer     = [];

  for (const line of lines) {
    const trimmed = line.trim();
    let matched = false;

    for (const [section, pattern] of Object.entries(SECTION_PATTERNS)) {
      if (pattern.test(trimmed) && trimmed.length < 60) {
        if (buffer.length) sections[current] = buffer.join('\n').trim();
        current = section;
        buffer  = [];
        matched = true;
        break;
      }
    }

    if (!matched) buffer.push(line);
  }

  if (buffer.length) sections[current] = buffer.join('\n').trim();
  return sections;
}

// ── Basic keyword extraction (TF-IDF-like frequency scoring) ─────────────────

const STOP_WORDS = new Set([
  'a','an','the','and','or','but','in','on','at','to','for','of','with',
  'by','from','as','is','was','are','were','be','been','being','have',
  'has','had','do','does','did','will','would','could','should','may',
  'might','shall','can','need','dare','ought','used','it','its','this',
  'that','these','those','he','she','they','we','i','you','my','your',
  'our','their','his','her','more','also','both','such','other','than',
  'then','so','just','about','up','out','if','no','not','what','which',
]);

function extractKeywords(text, topN = 30) {
  const words   = text.toLowerCase().match(/\b[a-z][a-z+#.]{2,}\b/g) || [];
  const freq    = {};

  for (const w of words) {
    if (STOP_WORDS.has(w)) continue;
    freq[w] = (freq[w] || 0) + 1;
  }

  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([word, count]) => ({ word, count }));
}

// ── Email / Phone / URL extraction ────────────────────────────────────────────

function extractContactInfo(text) {
  const emailMatch = text.match(/[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/);
  const phoneMatch = text.match(/[\+]?[(]?[0-9]{1,4}[)]?[-\s.]?[(]?[0-9]{1,4}[)]?[-\s.]?[0-9]{3,4}[-\s.]?[0-9]{3,4}/);
  const linkedIn   = text.match(/linkedin\.com\/in\/[a-zA-Z0-9\-_%]+/i);
  const github     = text.match(/github\.com\/[a-zA-Z0-9\-_%]+/i);

  return {
    email:     emailMatch  ? emailMatch[0]  : null,
    phone:     phoneMatch  ? phoneMatch[0]  : null,
    linkedin:  linkedIn    ? 'https://' + linkedIn[0]  : null,
    github:    github      ? 'https://' + github[0]    : null,
  };
}

// ── Years-of-experience heuristic ────────────────────────────────────────────
//  Scans for year ranges (e.g. 2018 – 2023) and sums durations.

function estimateTotalExperience(text) {
  const currentYear = new Date().getFullYear();
  const yearRanges  = [...text.matchAll(/\b(20\d{2}|19\d{2})\s*[-–—to]+\s*(20\d{2}|19\d{2}|present|current|now)\b/gi)];
  let totalMonths   = 0;

  for (const match of yearRanges) {
    const start = parseInt(match[1]);
    const end   = /present|current|now/i.test(match[2]) ? currentYear : parseInt(match[2]);
    if (!isNaN(start) && !isNaN(end) && end >= start && end - start <= 40) {
      totalMonths += (end - start) * 12;
    }
  }

  return Math.round((totalMonths / 12) * 10) / 10; // rounded to 1 dp
}

// ── Master pre-processing function ───────────────────────────────────────────

async function preprocessResume(filePath, fileType) {
  const rawText          = await extractTextFromFile(filePath, fileType);
  const cleanedText      = cleanText(rawText);
  const sections         = detectSections(cleanedText);
  const keywords         = extractKeywords(cleanedText);
  const contactInfo      = extractContactInfo(cleanedText);
  const estimatedYears   = estimateTotalExperience(cleanedText);

  return {
    rawText,
    preprocessedText: cleanedText,
    sections,
    keywords,
    contactInfo,
    estimatedYears,
    wordCount: cleanedText.split(/\s+/).length,
    charCount: cleanedText.length,
  };
}

module.exports = {
  extractTextFromFile,
  cleanText,
  detectSections,
  extractKeywords,
  extractContactInfo,
  estimateTotalExperience,
  preprocessResume,
};
