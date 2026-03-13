"""
Configuration for the AI Internship Discovery System.
Loads environment variables and defines constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
RESUMES_DIR = BASE_DIR / "resumes"
APPLICATIONS_DIR = BASE_DIR / "applications"
LOGS_DIR = BASE_DIR / "logs"
DB_PATH = BASE_DIR / "jobs.db"

RESUMES_DIR.mkdir(exist_ok=True)
APPLICATIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# --- API Keys (Google Sheets is optional, no LLM API needed) ---
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# --- Matching ---
MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", "5"))

# --- Scraping ---
REQUEST_TIMEOUT = 10
REQUEST_DELAY = (0.5, 1.5)  # random delay range in seconds between requests
MAX_JOBS_PER_SOURCE = 30

# --- Resume ---
DEFAULT_RESUME = os.getenv("DEFAULT_RESUME", "resumes/Aarogya_Gyawali_Resume.docx")

# --- User Agent ---
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# --- Logging ---
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "discovery.log"),
    ],
)

logger = logging.getLogger("internship_discovery")
