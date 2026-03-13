# AI Internship Discovery System

An automated pipeline that parses your resume, infers suitable roles, scrapes real internship listings from multiple job boards, scores them against your profile, and tracks everything in SQLite + Google Sheets.

**Zero API keys required.** Fully offline keyword-based matching — no LLM needed.

## Features

- **Resume Parsing** — Extracts skills, projects, experience, and education from PDF, DOCX, or TXT resumes using regex-based parsing
- **Role Inference** — Automatically determines suitable internship roles based on your skills and domains
- **Multi-Source Scraping** — Concurrently searches LinkedIn, Greenhouse, Lever, Hacker News Who's Hiring, and SimplifyJobs
- **Smart Matching** — Scores every listing against your resume (1-10) using keyword overlap with title bonuses
- **SQLite Storage** — Deduplicates and persists all results locally
- **Google Sheets Sync** — Optionally syncs matched jobs to a Google Sheet with a Status dropdown (Applied / Not relevant)
- **Application Generator** — Generates tailored cover letters and resume tips for your top matches

## Quick Start

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/JobSearch.git
cd JobSearch

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add your resume
cp ~/path/to/your_resume.docx resumes/

# Configure
cp .env.example .env
# Edit .env → set DEFAULT_RESUME to your resume filename

# Run
python main.py
```

## Usage

```bash
python main.py                                    # Use default resume
python main.py resumes/my_resume.pdf              # Specify a resume
python main.py --location "San Francisco, CA"     # Filter by location
python main.py --generate-apps --top 5            # Generate cover letters for top 5
```

## Sample Output

```
============================================================
  AI INTERNSHIP DISCOVERY SYSTEM
============================================================
  Resume: resumes/your_resume.docx
  Location: Anywhere
============================================================

[1/6] Parsing resume...
[2/6] Inferring suitable roles...
  → Data Science Intern
  → Software Engineer Intern
  → AI Engineer Intern
[3/6] Searching job boards (concurrent)...
  Found 165 total job listings
[4/6] Scoring jobs against resume...
  87 jobs passed matching threshold
[5/6] Storing results...
  SQLite: 65 new jobs added
  Google Sheets: 65 new jobs synced
[6/6] Skipping application generation (use --generate-apps to enable)

============================================================
  PIPELINE COMPLETE
============================================================
  Time: 20.1s
  Jobs found: 165
  Jobs matching: 87
============================================================
```

## Google Sheets Integration (Optional)

Sync results to a Google Sheet with a dropdown status tracker:

| Date Found | Company | Title | Location | Match Score | Job Link | Source | Status |
|------------|---------|-------|----------|-------------|----------|--------|--------|
| 2026-03-12 | TikTok | Backend Engineer Intern | San Jose, CA | 7 | [link] | LinkedIn | Applied |

See [SETUP.md](SETUP.md) for step-by-step Google Sheets configuration.

## Project Structure

```
JobSearch/
├── main.py                    # Pipeline orchestrator
├── resume_parser.py           # PDF/DOCX/TXT → structured JSON
├── role_inference.py          # Skill-based role inference
├── job_scraper.py             # Concurrent multi-source scraping
├── job_matcher.py             # Resume-job scoring engine
├── database.py                # SQLite storage & deduplication
├── job_tracker.py             # Google Sheets sync
├── application_generator.py   # Cover letter & resume tips
├── config.py                  # Settings & logging
├── requirements.txt
├── .env.example
├── SETUP.md                   # Setup guide
├── resumes/                   # Your resume(s) go here
├── applications/              # Generated materials
└── jobs.db                    # SQLite database (auto-created)
```

## How It Works

1. **Parse** — Extracts skills, programming languages, projects, education, and experience from your resume
2. **Infer** — Maps your profile to relevant internship role titles using keyword matching
3. **Search** — Hits 5 job sources concurrently with ThreadPoolExecutor
4. **Score** — Computes keyword overlap between your resume and each job description, with bonus points for title relevance
5. **Store** — Saves to SQLite (deduped) and optionally Google Sheets
6. **Generate** — Creates tailored cover letters and resume tips for your top N matches

## Tech Stack

- Python 3.10+
- `requests` + `BeautifulSoup4` for web scraping
- `pdfplumber` / `python-docx` for resume parsing
- `sqlite3` for local storage
- Google Sheets API (optional) for cloud tracking
- `ThreadPoolExecutor` for concurrent scraping

## License

MIT
