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

DEFAULT_DOCX_NAME = "ZenoFest2026_EventSubmissions.docx"
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
# Drive: DOCX read/write
# ---------------------------------------------------------------------------

def docx_exists():
    return bool(DRIVE_DOCX_FILE_ID)


def download_docx():
    """Return the DOCX bytes from Drive (raises HttpError if it doesn't exist)."""
    drive = get_drive_service()
    request = drive.files().get_media(fileId=DRIVE_DOCX_FILE_ID)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def upload_docx(docx_bytes):
    """Overwrite the existing DOCX with new content. Returns the file id."""
    drive = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype=DOCX_MIME, resumable=False)
    drive.files().update(
        fileId=DRIVE_DOCX_FILE_ID,
        media_body=media,
        supportsAllDrives=True,
    ).execute()
    return DRIVE_DOCX_FILE_ID


def create_docx(docx_bytes):
    """Create a new DOCX file (in DRIVE_FOLDER_ID if set, else the service
    account's own Drive). Returns the new file id."""
    drive = get_drive_service()
    media = MediaIoBaseUpload(io.BytesIO(docx_bytes), mimetype=DOCX_MIME, resumable=False)
    body = {
        "name": DEFAULT_DOCX_NAME,
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


def save_docx(docx_bytes):
    """Create or update the DOCX on Drive. Returns the file id."""
    if docx_exists():
        return upload_docx(docx_bytes)
    return create_docx(docx_bytes)


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
    "Project Title",
    "Figma Prototype Link",
    "Short Description",
    "Target Users",
    "Key Features / Screens",
    "Additional Links",
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
        form_data (dict with project_title, figma_link, short_description, target_users, key_features, additional_links)
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
            form_data.get("project_title", ""),     # Project Title
            form_data.get("figma_link", ""),        # Figma Prototype Link
            form_data.get("short_description", ""), # Short Description
            form_data.get("target_users", ""),      # Target Users
            form_data.get("key_features", ""),      # Key Features / Screens
            _format_additional_links(form_data),    # Additional Links
            submission.get("submitted_at", ""),     # Submitted At
            submission.get("email", ""),            # Email
        ]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("Failed to append UI/UX Design submission")
        return False