# AI Internship Discovery System — Setup Guide

## Quick Start (No Setup Needed!)

```bash
cd ~/Desktop/JobSearch
source .venv/bin/activate
python main.py
```

That's it! The system uses your resume at `resumes/Aarogya_Gyawali_Resume.docx` by default.

### Options

```bash
python main.py                                    # Default resume
python main.py resumes/other_resume.pdf           # Custom resume
python main.py --location "San Francisco, CA"     # Filter by location
python main.py --generate-apps --top 5            # Generate cover letters for top 5
```

---

## Google Sheets Integration (Optional)

Sync discovered jobs to a Google Sheet for easy tracking.

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Sheets API**:
   - Go to APIs & Services → Library
   - Search "Google Sheets API" → Enable

### Step 2: Create a Service Account

1. Go to APIs & Services → Credentials
2. Click **Create Credentials** → **Service Account**
3. Name it (e.g., `internship-tracker`) → Click Done
4. Click the service account → **Keys** tab → **Add Key** → **JSON**
5. Save the downloaded JSON file as `credentials.json` in this project folder

### Step 3: Create and Share a Google Sheet

1. Create a new Google Sheet in your Google Drive
2. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit`
3. Share the sheet with the service account email
   (found in `credentials.json` under `client_email`)
   — give it **Editor** access

### Step 4: Update .env

```bash
GOOGLE_SHEETS_CREDENTIALS=credentials.json
GOOGLE_SHEET_ID=paste-your-actual-sheet-id-here
```

### Step 5: Test

```bash
python job_tracker.py
# Should print: "Google Sheets is configured and ready"
```

---

## Customization (.env)

```bash
# Minimum match score (1-10, lower = more results)
MIN_MATCH_SCORE=5

# Default resume path
DEFAULT_RESUME=resumes/Aarogya_Gyawali_Resume.docx
```

---

## Project Structure

```
JobSearch/
├── main.py                    # Pipeline orchestrator
├── resume_parser.py           # PDF/DOCX/TXT → structured JSON
├── role_inference.py          # Keyword-based role inference
├── job_scraper.py             # Concurrent multi-source scraping
├── job_matcher.py             # Resume-job scoring
├── database.py                # SQLite storage
├── job_tracker.py             # Google Sheets sync
├── application_generator.py   # Cover letter & resume tips
├── config.py                  # Settings & logging
├── requirements.txt
├── .env / .env.example
├── SETUP.md
├── resumes/                   # Your resume goes here
├── applications/              # Generated materials
├── logs/                      # Log files
└── jobs.db                    # SQLite database (auto-created)
```
