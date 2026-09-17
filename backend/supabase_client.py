"""
Supabase client for ZenoFest submission backend.

Writes one row per team to a single `event_submissions` table with a JSONB
form_data column so every tech event's fields fit the same table.
"""
import os
import uuid

from dotenv import load_dotenv
from supabase import create_client
from postgrest.types import ReturnMethod

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "").strip()

_client = None


def get_client():
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_ANON_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        _client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    return _client


def submit_event_data(team_id, team_name, email, tech_event, form_data):
    """Insert one submission row. Returns the new row's id (generated here so
    the anon role only needs INSERT, never SELECT/returning privileges)."""
    submission_id = str(uuid.uuid4())
    get_client().table("event_submissions").insert(
        {
            "id": submission_id,
            "team_id": team_id,
            "team_name": team_name,
            "email": email,
            "tech_event": tech_event,
            "form_data": form_data,
        },
        returning=ReturnMethod.minimal,
    ).execute()
    return submission_id