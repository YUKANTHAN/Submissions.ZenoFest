"""
Google Sheets + Drive client for the ZenoFest submission backend.

Uses the same service-account auth pattern as the registration backend:
pass the JSON either as a local file or inline via GOOGLE_SERVICE_ACCOUNT_JSON.
"""
import io
import os

from dotenv import load_dotenv
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from google.auth.transport.requests import AuthorizedSession

load_dotenv()

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
SA_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT", "service_account.json")
SA_JSON_CONTENT = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
SA_JSON_PATH = os.environ.get("GOOGLE_SERVICE_ACCOUNT_PATH", SA_JSON)
ORGANIZED_SHEET_ID = os.environ.get("ORGANIZED_SHEET_ID", "").strip()
ORGANIZED_TAB_NAME = os.environ.get("ORGANIZED_TAB_NAME", "Sheet1").strip()
PROJECT_EXPO_SHEET_ID = os.environ.get("PROJECT_EXPO_SHEET_ID", "").strip()
PROJECT_EXPO_TAB_NAME = os.environ.get("PROJECT_EXPO_TAB_NAME", "Sheet1").strip()
UIUX_DESIGN_SHEET_ID = os.environ.get("UIUX_DESIGN_SHEET_ID", "").strip()
UIUX_DESIGN_TAB_NAME = os.environ.get("UIUX_DESIGN_TAB_NAME", "Sheet1").strip()
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "").strip()
DRIVE_DOCX_FILE_ID = os.environ.get("DRIVE_DOCX_FILE_ID", "").strip()
UIUX_DOCX_FILE_ID = os.environ.get("UIUX_DOCX_FILE_ID", "").strip()

DEFAULT_DOCX_NAME = "ZenoFest2026_EventSubmissions.docx"
UIUX_DOCX_NAME = "ZenoFest2026_UIUXDesignSubmissions.docx"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Write service account JSON to file once at module load if provided via env var
if SA_JSON_CONTENT:
    try:
        with open(SA_JSON_PATH, "w", encoding="utf-8") as fh:
            fh.write(SA_JSON_CONTENT)
    except Exception:
        pass  # fallback to existing file


def _credentials():
    return service_account.Credentials.from_service_account_file(SA_JSON_PATH, scopes=SCOPE)


def get_gspread_client():
    return gspread.authorize(_credentials())


def get_drive_service():
    return build("drive", "v3", credentials=_credentials())


# ---------------------------------------------------------------------------
# Sheets: team lookup by email
# ---------------------------------------------------------------------------

def make_team_id(tech_event, row_num):
    """Match the registration backend's team id format (ZFPEx, ZFUIx, ZFLHx)."""
    e = (tech_event or "").strip().lower()
    if "project" in e or "expo" in e:
        code = "PE"
    elif "logic" in e or "hunt" in e:
        code = "LH"
    elif "ui" in e or "ux" in e:
        code = "UI"
    else:
        initials = "".join(w[0] for w in str(tech_event).split() if w)[:2].upper()
        code = initials or "XX"
    return f"ZF{code}{int(row_num)}"


def find_team_by_email(email):
    """Search the organized sheet for a row matching `email`.
    Matches the `Email` column, column I (Leader Email, index 8), column Q (Member 2, index 16), column R (Member 3, index 17).
    Returns a dict with team info or None if not found."""
    email = (email or "").strip().lower()
    if not email or not ORGANIZED_SHEET_ID:
        return None

    ws = get_gspread_client().open_by_key(ORGANIZED_SHEET_ID).worksheet(ORGANIZED_TAB_NAME)

    def field(row, name):
        try:
            return row[headers.index(name)]
        except (ValueError, IndexError):
            return ""

    values = ws.get_all_values()
    if not values:
        return None
    headers = values[0]
    for i, row in enumerate(values[1:], start=2):
        row_email = (field(row, "Email") or "").strip().lower()
        # Leader Email is column I (index 8)
        leader_email = (row[8] if len(row) > 8 else "").strip().lower()
        # Member 2 email is column Q (index 16)
        member2_email = (row[16] if len(row) > 16 else "").strip().lower()
        # Member 3 email is column R (index 17)
        member3_email = (row[17] if len(row) > 17 else "").strip().lower()
        if email not in (row_email, leader_email, member2_email, member3_email):
            continue
        tech_event = field(row, "Tech Event")
        dept = field(row, "Department")
        year = field(row, "Year")
        dept_year = field(row, "Department & Year")
        if not dept_year and (dept or year):
            dept_year = " ".join(x for x in (dept, year) if x)
        # Use Team ID from sheet if present, otherwise generate using actual sheet row number
        sheet_team_id = field(row, "Team ID")
        team_id = sheet_team_id if sheet_team_id else make_team_id(tech_event, i)
        return {
            "email": email,
            "team_id": team_id,
            "team_name": field(row, "Team Name"),
            "tech_event": tech_event,
            "leader_name": field(row, "Leader Name"),
            "leader_contact": field(row, "Leader Contact"),
            "college": field(row, "College"),
            "team_size": field(row, "Team Size"),
            "dept_year": dept_year,
        }
    return None


# ---------------------------------------------------------------------------
# Drive: DOCX read/write (generic)
# ---------------------------------------------------------------------------

def _docx_exists(docx_file_id):
    return bool(docx_file_id)


def _download_docx(docx_file_id):
    drive = get_drive_service()
    # Check if it's a Google Doc (needs export) or .docx file
    file_info = drive.files().get(fileId=docx_file_id, fields="mimeType").execute()
    mime_type = file_info.get("mimeType", "")
    
    buffer = io.BytesIO()
    if mime_type == "application/vnd.google-apps.document":
        # Export Google Doc as .docx
        request = drive.files().export_media(fileId=docx_file_id, mimeType=DOCX_MIME)
    else:
        # Download .docx directly
        request = drive.files().get_media(fileId=docx_file_id)
    
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def _upload_docx(docx_bytes, docx_file_id):
    drive = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype=DOCX_MIME, resumable=False)
    drive.files().update(
        fileId=docx_file_id,
        media_body=media,
        supportsAllDrives=True,
    ).execute()
    return docx_file_id


def _create_docx(docx_bytes, docx_name):
    drive = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype=DOCX_MIME, resumable=False)
    body = {
        "name": docx_name,
        "mimeType": DOCX_MIME,
    }
    if DRIVE_FOLDER_ID:
        body["parents"] = [DRIVE_FOLDER_ID]
    file_ = drive.files().create(
        body=body,
        media_body=media,
        supportsAllDrives=True,
    ).execute()
    return file_.get("id")


def _save_docx(docx_bytes, docx_file_id, docx_name):
    if _docx_exists(docx_file_id):
        return _upload_docx(docx_bytes, docx_file_id)
    return _create_docx(docx_bytes, docx_name)


# Public wrappers for each event type
def docx_exists():
    """Check if main Event Submissions DOCX exists."""
    return _docx_exists(DRIVE_DOCX_FILE_ID)


def download_docx():
    """Download main Event Submissions DOCX."""
    return _download_docx(DRIVE_DOCX_FILE_ID)


def save_docx(docx_bytes):
    """Save to main Event Submissions DOCX."""
    return _save_docx(docx_bytes, DRIVE_DOCX_FILE_ID, DEFAULT_DOCX_NAME)


def uiux_docx_exists():
    """Check if UI/UX Design DOCX exists."""
    return _docx_exists(UIUX_DOCX_FILE_ID)


def uiux_download_docx():
    """Download UI/UX Design DOCX."""
    return _download_docx(UIUX_DOCX_FILE_ID)


def uiux_save_docx(docx_bytes):
    """Save to UI/UX Design DOCX."""
    return _save_docx(docx_bytes, UIUX_DOCX_FILE_ID, UIUX_DOCX_NAME)


# ---------------------------------------------------------------------------
# Sheets: Project Expo submission tracking
# ---------------------------------------------------------------------------

PROJECT_EXPO_HEADERS = [
    "Timestamp",
    "Team ID",
    "Team Name",
    "Leader Name",
    "Project Title",
    "GitHub URL",
    "Abstract URL",
    "PPT URL",
    "Additional Links",
    "Submitted At",
    "Email",
]


def _get_project_expo_worksheet():
    """Get the Project Expo worksheet, creating headers if needed."""
    if not PROJECT_EXPO_SHEET_ID:
        return None
    ws = get_gspread_client().open_by_key(PROJECT_EXPO_SHEET_ID).worksheet(PROJECT_EXPO_TAB_NAME)
    # Ensure headers exist
    existing = ws.row_values(1)
    if not existing or existing != PROJECT_EXPO_HEADERS:
        ws.update("A1", [PROJECT_EXPO_HEADERS])
    return ws


def _format_additional_links(form_data):
    """Format additional_links JSON array into a readable string."""
    import json
    links_str = form_data.get("additional_links", "")
    if not links_str:
        return ""
    try:
        links = json.loads(links_str)
        if isinstance(links, list):
            return "; ".join(f"{link.get('label', '')}: {link.get('url', '')}" for link in links if link.get('label') or link.get('url'))
    except (json.JSONDecodeError, TypeError):
        pass
    return links_str


def append_project_expo_submission(submission):
    """
    Append a Project Expo submission to the tracking spreadsheet.
    `submission` dict should contain:
        team_id, team_name, tech_event, leader_name, college, email, submitted_at,
        form_data (dict with project_title, github_url, abstract_link, ppt_link, additional_links)
    Returns True if successful, False otherwise.
    """
    if not PROJECT_EXPO_SHEET_ID:
        return False
    if submission.get("tech_event") != "Project Expo":
        return False  # Only track Project Expo submissions

    try:
        ws = _get_project_expo_worksheet()
        if not ws:
            return False

        form_data = submission.get("form_data") or {}
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

        row = [
            timestamp,                              # Timestamp
            submission.get("team_id", ""),          # Team ID
            submission.get("team_name", ""),        # Team Name
            submission.get("leader_name", ""),      # Leader Name
            form_data.get("project_title", ""),     # Project Title
            form_data.get("github_url", ""),        # GitHub URL
            form_data.get("abstract_link", ""),     # Abstract URL
            form_data.get("ppt_link", ""),          # PPT URL
            _format_additional_links(form_data),    # Additional Links
            submission.get("submitted_at", ""),     # Submitted At
            submission.get("email", ""),            # Email
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Failed to append Project Expo submission")
        return False


# ---------------------------------------------------------------------------
# Sheets: UI/UX Design submission tracking
# ---------------------------------------------------------------------------

UIUX_DESIGN_HEADERS = [
    "Timestamp",
    "Team ID",
    "Team Name",
    "Leader Name",
    "Problem Statement",
    "Project Title",
    "Short Description",
    "Figma Prototype Link",
    "Submitted At",
    "Email",
]


def _get_uiux_design_worksheet():
    """Get the UI/UX Design worksheet, creating headers if needed."""
    if not UIUX_DESIGN_SHEET_ID:
        return None
    ws = get_gspread_client().open_by_key(UIUX_DESIGN_SHEET_ID).worksheet(UIUX_DESIGN_TAB_NAME)
    existing = ws.row_values(1)
    if not existing or existing != UIUX_DESIGN_HEADERS:
        ws.update("A1", [UIUX_DESIGN_HEADERS])
    return ws


def append_uiux_design_submission(submission):
    """
    Append a UI/UX Design submission to the tracking spreadsheet.
    `submission` dict should contain:
        team_id, team_name, tech_event, leader_name, college, email, submitted_at,
        form_data (dict with problem_statement, project_title, short_description, figma_link)
    Returns True if successful, False otherwise.
    """
    if not UIUX_DESIGN_SHEET_ID:
        return False
    if submission.get("tech_event") != "UI/UX Design using Figma":
        return False

    try:
        ws = _get_uiux_design_worksheet()
        if not ws:
            return False

        form_data = submission.get("form_data") or {}
        from datetime import datetime, timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

        row = [
            timestamp,                              # Timestamp
            submission.get("team_id", ""),          # Team ID
            submission.get("team_name", ""),        # Team Name
            submission.get("leader_name", ""),      # Leader Name
            form_data.get("problem_statement", ""), # Problem Statement
            form_data.get("project_title", ""),     # Project Title
            form_data.get("short_description", ""), # Short Description
            form_data.get("figma_link", ""),        # Figma Prototype Link
            submission.get("submitted_at", ""),     # Submitted At
            submission.get("email", ""),            # Email
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Failed to append UI/UX Design submission")
        return False