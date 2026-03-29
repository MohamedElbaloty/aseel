"""
Google Sheets integration for saving check-in data.
"""
import os
import json
import logging
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Timestamp",
    "Employee Name",
    "Employee ID",
    "Client Name",
    "Account Number",
    "Product",
    "Visit Reason",
    "Meeting Type",
    "Account Manager Present",
    "Admin Manager Present",
    "Meeting Date & Time",
    "Meeting Objective",
    "Next Visit Date",
    "Notes",
    "Follow-up Actions",
]


def get_sheets_service():
    """Initialize and return Google Sheets service."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON is not set in .env")

    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service


def ensure_headers(service, spreadsheet_id: str, sheet_name: str = "Check-ins"):
    """Create sheet headers if not already present."""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:Z1")
            .execute()
        )
        existing = result.get("values", [])
        if not existing:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()
            logger.info("Headers created in Google Sheet.")
    except Exception as e:
        logger.warning(f"Could not ensure headers: {e}")


def save_to_sheet(data: dict, employee_name: str, employee_id: str) -> bool:
    """
    Save extracted check-in data to Google Sheets.
    Returns True on success, False on failure.
    """
    try:
        service = get_sheets_service()
        spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Check-ins")

        ensure_headers(service, spreadsheet_id, sheet_name)

        def fmt_bool(val):
            if val is True:
                return "Yes"
            if val is False:
                return "No"
            return ""

        def fmt_date(dt_str):
            if not dt_str:
                return ""
            try:
                dt = datetime.fromisoformat(dt_str)
                return dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                return dt_str

        actions = data.get("follow_up_actions") or []
        actions_str = " | ".join(actions) if actions else ""

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            employee_name,
            employee_id,
            data.get("client_name") or "",
            data.get("account_number") or "",
            data.get("product") or "",
            data.get("visit_reason") or "",
            data.get("meeting_type") or "",
            fmt_bool(data.get("account_manager_present")),
            fmt_bool(data.get("admin_manager_present")),
            fmt_date(data.get("meeting_datetime")),
            data.get("meeting_objective") or "",
            fmt_date(data.get("next_visit_date")),
            data.get("notes") or "",
            actions_str,
        ]

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        logger.info(f"Check-in saved to Google Sheets for {employee_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to save to Google Sheets: {e}")
        return False
