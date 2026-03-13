"""
Job Tracker — appends discovered jobs to a Google Sheet.
Falls back gracefully if Google Sheets is not configured.
"""

import os
from datetime import datetime

from config import GOOGLE_SHEET_ID, GOOGLE_SHEETS_CREDENTIALS, logger

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER_ROW = [
    "Date Found",
    "Company",
    "Title",
    "Location",
    "Type",
    "Match Score",
    "Job Link",
    "Source",
    "Status",
]

STATUS_OPTIONS = ["Applied", "Not relevant"]


def _sheets_available() -> bool:
    """Check if Google Sheets is configured."""
    if not GOOGLE_SHEET_ID:
        return False
    if not os.path.exists(GOOGLE_SHEETS_CREDENTIALS):
        return False
    return True


def _get_sheets_service():
    """Build and return the Google Sheets API service."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def _ensure_header(service, spreadsheet_id: str, sheet_name: str = "Sheet1"):
    """Add header row if the sheet is empty."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:I1")
        .execute()
    )
    values = result.get("values", [])
    if not values:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:I1",
            valueInputOption="RAW",
            body={"values": [HEADER_ROW]},
        ).execute()
        logger.info("Added header row to Google Sheet")
        # Add dropdown validation for the Status column (column I)
        _add_status_dropdown(service, spreadsheet_id, sheet_name)


def _add_status_dropdown(service, spreadsheet_id: str, sheet_name: str = "Sheet1"):
    """Add dropdown data validation for the Status column (column I, index 8)."""
    try:
        # Get the sheet ID (numeric) for the given sheet name
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = 0
        for s in spreadsheet.get("sheets", []):
            if s["properties"]["title"] == sheet_name:
                sheet_id = s["properties"]["sheetId"]
                break

        request_body = {
            "requests": [
                {
                    "setDataValidation": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,  # skip header
                            "startColumnIndex": 8,  # column I (0-indexed)
                            "endColumnIndex": 9,
                        },
                        "rule": {
                            "condition": {
                                "type": "ONE_OF_LIST",
                                "values": [{"userEnteredValue": v} for v in STATUS_OPTIONS],
                            },
                            "showCustomUi": True,
                            "strict": False,
                        },
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=request_body
        ).execute()
        logger.info("Added Status dropdown validation to Google Sheet")
    except Exception as e:
        logger.warning(f"Could not add dropdown validation: {e}")


def _get_existing_links(service, spreadsheet_id: str, sheet_name: str = "Sheet1") -> set:
    """Get all existing job links from the sheet to avoid duplicates."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!G:G")
        .execute()
    )
    values = result.get("values", [])
    return {row[0] for row in values if row}


def append_jobs_to_sheet(jobs: list[dict], sheet_name: str = "Sheet1") -> int:
    """Append new jobs to the Google Sheet. Returns count of rows added."""
    if not _sheets_available():
        logger.info("Google Sheets not configured — skipping sync")
        return 0

    try:
        service = _get_sheets_service()
    except Exception as e:
        logger.warning(f"Google Sheets auth failed: {e}")
        return 0

    try:
        _ensure_header(service, GOOGLE_SHEET_ID, sheet_name)
        existing_links = _get_existing_links(service, GOOGLE_SHEET_ID, sheet_name)
    except Exception as e:
        logger.warning(f"Google Sheets access failed: {e}")
        return 0

    rows = []
    for job in jobs:
        link = job.get("link", "")
        if link in existing_links:
            continue
        rows.append(
            [
                job.get("date_posted", datetime.now().strftime("%Y-%m-%d")),
                job.get("company", "Unknown"),
                job.get("title", "Unknown"),
                job.get("location", ""),
                job.get("type", "Internship"),
                job.get("match_score", 0),
                link,
                job.get("source", ""),
                "",  # Status — user picks from dropdown
            ]
        )

    if not rows:
        logger.info("No new jobs to append to Google Sheet")
        return 0

    try:
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range=f"{sheet_name}!A:I",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": rows},
        ).execute()
        logger.info(f"Appended {len(rows)} new jobs to Google Sheet")
        return len(rows)
    except Exception as e:
        logger.warning(f"Failed to append to Google Sheet: {e}")
        return 0


if __name__ == "__main__":
    if _sheets_available():
        print("✅ Google Sheets is configured and ready")
    else:
        print("⚠️  Google Sheets not configured. See SETUP.md for instructions.")
        if not GOOGLE_SHEET_ID:
            print("   Missing: GOOGLE_SHEET_ID in .env")
        if not os.path.exists(GOOGLE_SHEETS_CREDENTIALS):
            print(f"   Missing: {GOOGLE_SHEETS_CREDENTIALS}")
