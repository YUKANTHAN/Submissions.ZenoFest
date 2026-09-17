# ZenoFest Event Data Submission Backend — Implementation Plan

## Context

The existing backend (`ZenoFestCsvAppend/backend`) handles registration: it syncs raw Google Form responses into an organized sheet, assigns team IDs (e.g. `ZFPE5`, `ZFUI7`), and sends confirmation emails.

This **new separate backend** handles a different concern: **post-registration event data submission**. Participants who already registered visit a form, validate their email against the organized sheet, fill out their tech-event-specific form, and the data is saved to Supabase + appended as a branded DOCX page in Google Drive.

Separate backend = crash isolation, independent deploys, no risk to registration emails.

---

## Project Structure

```
C:\Mini project\Submissions.ZenoFest\
├── backend/
│   ├── app.py                  # Flask app — routes + server
│   ├── events.py               # Event-specific form field definitions
│   ├── docx_builder.py         # Branded DOCX generation (python-docx)
│   ├── supabase_client.py      # Supabase insert helper
│   ├── google_client.py        # Google Sheets + Drive shared client
│   ├── requirements.txt
│   ├── render.yaml             # Render free-tier deploy config
│   ├── .env.example
│   └── .gitignore
└── frontend/
    └── index.html              # Single-page form (vanilla HTML/CSS/JS)
```

---

## Backend: `app.py` — Routes

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/` | Serve the HTML form |
| `POST` | `/api/validate-email` | Validate email against organized sheet, return team info + event |
| `POST` | `/api/submit` | Save form_data to Supabase + append branded page to DOCX on Drive |
| `GET` | `/health` | Health check |

### Flow Detail

#### 1. `POST /api/validate-email`
- Input: `{ "email": "user@example.com" }`
- Read organized sheet via Google Sheets API
- Find matching row by email column (index 6 based on `OUTPUT_HEADERS`: `Email` is at index 1)
- Return:
  ```json
  {
    "ok": true,
    "team_id": "ZFPE5",
    "team_name": "CodeCrushers",
    "tech_event": "Project Expo",
    "leader_name": "Arun",
    "college": "ABC Engineering"
  }
  ```
- If email not found: `{ "ok": false, "error": "Email not found in registrations" }`

#### 2. `POST /api/submit`
- Input:
  ```json
  {
    "email": "user@example.com",
    "team_id": "ZFPE5",
    "tech_event": "Project Expo",
    "form_data": { "project_title": "...", "description": "...", ... }
  }
  ```
- **Supabase**: Insert one row into `event_submissions` table
- **DOCX**: Fetch/create the shared DOCX file on Google Drive, append a branded page, upload back
- Return: `{ "ok": true, "submission_id": "uuid" }`

---

## `events.py` — Event Form Definitions

Each event maps to a list of form fields. This file is the single source of truth for:
- What fields each event's form shows
- The labels, input types, and validation for each field

```python
EVENT_FIELDS = {
    "Project Expo": [
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "description", "label": "Project Description", "type": "textarea", "required": True},
        {"name": "tech_stack", "label": "Tech Stack", "type": "text", "required": True},
        {"name": "github_link", "label": "GitHub Repository Link", "type": "url", "required": False},
        {"name": "demo_link", "label": "Demo / Video Link", "type": "url", "required": False},
    ],
    "UI/UX Design": [
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "description", "label": "Description", "type": "textarea", "required": True},
        {"name": "figma_link", "label": "Figma Prototype Link", "type": "url", "required": True},
        {"name": "design_tools", "label": "Tools Used", "type": "text", "required": False},
    ],
    "Logic Hunt": [
        {"name": "team_name_alias", "label": "Team Display Name", "type": "text", "required": True},
        {"name": "preferred_language", "label": "Preferred Programming Language", "type": "text", "required": True},
        {"name": "experience_level", "label": "Experience Level", "type": "select", "options": ["Beginner", "Intermediate", "Advanced"], "required": True},
    ],
}
```

**Action needed from you**: Provide the exact event names and their specific form fields. The above are placeholders.

---

## `docx_builder.py` — Branded DOCX

Uses `python-docx` to append a page per submission to a single DOCX file.

### Layout per page:
```
┌─────────────────────────────────────────┐
│          ★ ZENOFEST 2026 ★              │
│       Event Data Submission             │
│─────────────────────────────────────────│
│                                         │
│  Team ID:     ZFPE5                     │
│  Team Name:   CodeCrushers              │
│  Event:       Project Expo              │
│  Leader:      Arun                      │
│  College:     ABC Engineering           │
│  Submitted:   2026-09-17 14:30:00       │
│                                         │
│  ─── Submission Data ───                │
│                                         │
│  Project Title:  Smart Traffic          │
│  Description:   An IoT-based...         │
│  Tech Stack:    Python, Flask, React    │
│  GitHub:        https://github.com/...  │
│                                         │
│                           Page X of Y   │
└─────────────────────────────────────────┘
```

### Strategy:
- One file: `ZenoFest2026_EventSubmissions.docx` in a shared Drive folder
- On each submission: download the current DOCX from Drive → append page → upload back
- Uses Google Drive API to manage the file (upload new version / update)
- If the file doesn't exist yet, create it with a title page

---

## `supabase_client.py` — Supabase

### Table: `event_submissions`

```sql
CREATE TABLE event_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id TEXT NOT NULL,
    team_name TEXT,
    email TEXT NOT NULL,
    tech_event TEXT,
    submitted_at TIMESTAMPTZ DEFAULT now(),
    form_data JSONB
);
```

- Single table for all events
- `form_data` is JSONB — flexible per event
- RLS disabled for backend-only access (anon key used server-side only)

Helper:
```python
def submit_event_data(team_id, team_name, email, tech_event, form_data):
    client = get_supabase()
    result = client.table("event_submissions").insert({
        "team_id": team_id,
        "team_name": team_name,
        "email": email,
        "tech_event": tech_event,
        "form_data": form_data,
    }).execute()
    return result.data[0]["id"]
```

---

## `google_client.py` — Shared Google Client

Reuses the same service account auth pattern from the existing backend:
- Reads organized sheet to find team by email
- Manages DOCX file on Google Drive (download/upload)
- Handles inline service account JSON from env vars (same pattern as existing backend)

Key functions:
- `get_gspread_client()` — returns authorized gspread client
- `find_team_by_email(email)` — searches organized sheet, returns team info or None
- `download_docx_from_drive(file_id)` → bytes
- `upload_docx_to_drive(file_id, docx_bytes)` — update file content
- `create_docx_on_drive(folder_id, docx_bytes)` — create new file

---

## Frontend: `index.html`

Single-page, no framework. Three states:

1. **Email Entry** — user enters email, clicks "Verify"
2. **Form Display** — after validation, show event-specific fields dynamically
3. **Success** — confirmation message after submission

### Design:
- Dark theme matching ZenoFest branding (purple/cyan accents)
- Mobile-responsive
- Loads field definitions from `/api/form-fields/:event` or embeds them from the validation response
- No build tools needed — pure HTML/CSS/JS

---

## Environment Variables (.env)

```env
# Google Sheets + Drive
GOOGLE_SERVICE_ACCOUNT_JSON=
GOOGLE_SERVICE_ACCOUNT_PATH=service_account.json

# Organized sheet (from existing backend)
ORGANIZED_SHEET_ID=

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=

# Google Drive — folder ID for DOCX storage
DRIVE_FOLDER_ID=

# DOCX file ID (set after first creation, or leave blank to auto-create)
DRIVE_DOCX_FILE_ID=

# Server
PORT=8081
```

---

## Dependencies (`requirements.txt`)

```
flask>=2.3
gspread>=6.0
google-auth>=2.20
google-api-python-client>=2.100
google-auth-httplib2>=0.1
python-dotenv>=1.0
supabase>=2.0
python-docx>=1.1
requests>=2.31
```

---

## Deployment

- **Platform**: Render free tier (separate from existing backend)
- **Port**: 8081 (or whatever Render assigns)
- **Config**: `render.yaml` in the backend folder
- **Secrets**: Set via Render dashboard (env vars) or Render Secret Files for service account JSON

---

## Implementation Order

| Step | What | Files |
|------|------|-------|
| 1 | Scaffold project + deps | `requirements.txt`, `.env.example`, `.gitignore` |
| 2 | Google client (sheets read + Drive) | `google_client.py` |
| 3 | Event field definitions | `events.py` |
| 4 | Supabase client | `supabase_client.py` |
| 5 | DOCX builder | `docx_builder.py` |
| 6 | Flask routes (validate + submit) | `app.py` |
| 7 | Frontend form | `frontend/index.html` |
| 8 | Render deploy config | `render.yaml` |

---

## What You Need to Provide

1. **Event-specific form fields** per tech event (names, types, labels)
2. **Supabase URL + anon key**
3. **Service account JSON** (can reuse the same one from existing backend)
4. **Google Drive folder ID** for DOCX storage
5. Confirm the organized sheet ID (same as existing backend's `ORGANIZED_SHEET_ID`)
