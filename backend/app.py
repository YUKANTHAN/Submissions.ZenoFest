"""
ZenoFest Event Data Submission Backend
======================================
Separate Flask service (isolated from the registration backend).

Flow:
  1. Participant enters email at the hosted form.
  2. POST /api/validate-email  → looks up the team in the organized sheet.
  3. The form shows event-specific fields.
  4. POST /api/submit → saves to Supabase and appends a branded page to the
     shared DOCX on Google Drive.
"""
import os
import json
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

import events as events_mod
import google_client as gc
import docx_builder
import pdf_builder
import mailer
import supabase_client as supabase

load_dotenv()

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=None)
CORS(app)


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/events")
def event_fields():
    """Return all event form definitions (used by the frontend to render forms)."""
    return jsonify(events_mod.get_all_events()), 200


@app.post("/api/validate-email")
def validate_email():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "Enter a valid email address"}), 400

    try:
        team = gc.find_team_by_email(email)
    except Exception as exc:
        app.logger.exception("organised-sheet lookup failed")
        return jsonify({"ok": False, "error": "Could not reach the registered teams sheet. Try again shortly."}), 502

    if not team:
        return jsonify({"ok": False, "error": "This email is not registered for ZenoFest 2026."}), 404

    event = team.get("tech_event") or ""
    if not event:
        return jsonify({"ok": False, "error": "Registration record has no tech event assigned."}), 404

    fields = events_mod.get_event_fields(event)
    team.pop("email", None)
    return jsonify({
        "ok": True,
        "team": team,
        "form_fields": fields or [],
    }), 200


@app.post("/api/submit")
def submit():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    team = body.get("team") or {}
    form_data = body.get("form_data") or {}
    is_unverified = body.get("is_unverified", False)

    if not email:
        return jsonify({"ok": False, "error": "Missing email"}), 400
    if not form_data:
        return jsonify({"ok": False, "error": "Missing form data"}), 400

    tech_event = team.get("tech_event") or ""
    fields = events_mod.get_event_fields(tech_event)
    if fields is None:
        return jsonify({"ok": False, "error": f"Unknown event: {tech_event}"}), 400

    # Basic required-field validation against the event definition.
    missing = [f["label"] for f in fields if f.get("required") and not str(form_data.get(f["name"], "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": "Missing required fields: " + ", ".join(missing)}), 400

    # Length cap on large-text fields (textarea). Short text stays unlimited.
    too_long = []
    for f in fields:
        limit = f.get("max_length")
        if limit and len(str(form_data.get(f["name"], "")).strip()) > limit:
            too_long.append(f"{f['label']} (max {limit} chars)")
    if too_long:
        return jsonify({"ok": False, "error": "Too long: " + "; ".join(too_long)}), 400

    team_id = team.get("team_id") or ""
    team_name = team.get("team_name") or ""
    leader_name = team.get("leader_name") or ""
    college = team.get("college") or ""
    ist = timezone(timedelta(hours=5, minutes=30))
    submitted_at = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")

    # 1) Save to Supabase (optional — don't block the rest of the flow if it fails).
    import uuid as _uuid
    submission_id = str(_uuid.uuid4())
    db_status = "saved"
    try:
        submission_id = supabase.submit_event_data(
            team_id=team_id,
            team_name=team_name,
            email=email,
            tech_event=tech_event,
            form_data=form_data,
        )
    except Exception as exc:
        app.logger.exception("supabase insert failed (continuing without DB)")
        db_status = f"failed: {exc}"

    # 2) Append to the branded DOCX on Drive.
    docx_error = None
    try:
        # Choose the correct DOCX based on event
        is_uiux = tech_event == "UI/UX Design using Figma"
        docx_exists_fn = gc.uiux_docx_exists if is_uiux else gc.docx_exists
        download_docx_fn = gc.uiux_download_docx if is_uiux else gc.download_docx
        save_docx_fn = gc.uiux_save_docx if is_uiux else gc.save_docx

        existing = None
        if docx_exists_fn():
            existing = download_docx_fn()
        labels = {f["name"]: f["label"] for f in fields}
        new_bytes = docx_builder.append_submission(existing, {
            "team_id": team_id,
            "team_name": team_name,
            "tech_event": tech_event,
            "leader_name": leader_name,
            "college": college,
            "email": email,
            "submitted_at": submitted_at,
            "form_data": form_data,
            "field_labels": labels,
        })
        save_docx_fn(new_bytes)
    except Exception as exc:
        app.logger.exception("docx append failed")
        docx_error = str(exc)

    # 3) Email the team their own branded PDF (only for Project Expo).
    mail_status = "not_configured"
    if mailer.is_configured() and tech_event == "Project Expo":
        try:
            pdf_bytes = pdf_builder.build_submission_pdf({
                "team_id": team_id,
                "team_name": team_name,
                "tech_event": tech_event,
                "leader_name": leader_name,
                "college": college,
                "email": email,
                "submitted_at": submitted_at,
                "form_data": form_data,
                "field_labels": {f["name"]: f["label"] for f in fields},
            })
            subject = f"ZenoFest 2026 - Event Data Submitted ({team_id})"
            html = mailer.build_html(team, form_data, {f["name"]: f["label"] for f in fields},
                                     submitted_at, team_id)
            mailer.send_confirmation_email(
                to_email=email,
                subject=subject,
                html_body=html,
                attachment_name=pdf_builder.pdf_filename(team_id, tech_event),
                attachment_bytes=pdf_bytes,
            )
            mail_status = "sent"
        except Exception as exc:
            app.logger.exception("email send failed")
            mail_status = f"failed: {exc}"
    elif tech_event != "Project Expo":
        mail_status = "skipped_not_project_expo"

    # 4) Notify organizer about unauthorized submissions.
    if is_unverified and mailer.is_configured():
        try:
            labels = {f["name"]: f["label"] for f in fields}
            mailer.send_unauthorized_notification(
                submission_email=email,
                team_id=team_id,
                team_name=team_name,
                tech_event=tech_event,
                leader_name=leader_name,
                college=college,
                submitted_at=submitted_at,
                form_data=form_data,
                field_labels=labels,
            )
        except Exception as exc:
            app.logger.exception("unauthorized notification failed")

    # 5) Append to Project Expo tracking spreadsheet (if Project Expo event).
    project_expo_status = "skipped"
    try:
        submission_record = {
            "team_id": team_id,
            "team_name": team_name,
            "tech_event": tech_event,
            "leader_name": leader_name,
            "college": college,
            "email": email,
            "submitted_at": submitted_at,
            "form_data": form_data,
        }
        if gc.append_project_expo_submission(submission_record):
            project_expo_status = "appended"
        else:
            project_expo_status = "not_applicable_or_failed"
    except Exception as exc:
        app.logger.exception("Project Expo sheet append failed")
        project_expo_status = f"failed: {exc}"

    # 6) Append to UI/UX Design tracking spreadsheet (if UI/UX Design event).
    uiux_status = "skipped"
    try:
        if gc.append_uiux_design_submission(submission_record):
            uiux_status = "appended"
        else:
            uiux_status = "not_applicable_or_failed"
    except Exception as exc:
        app.logger.exception("UI/UX Design sheet append failed")
        uiux_status = f"failed: {exc}"

    return jsonify({
        "ok": True,
        "submission_id": submission_id,
        "submitted_at": submitted_at,
        "db_status": db_status,
        "docx_status": "appended" if not docx_error else f"failed: {docx_error}",
        "mail_status": mail_status,
        "project_expo_status": project_expo_status,
        "uiux_design_status": uiux_status,
    }), 200


@app.get("/api/ppt-template")
def ppt_template():
    """Download the PPT template for Project Expo."""
    from flask import send_file
    ppt_path = os.path.join(os.path.dirname(__file__), "..", "Project_expo_template_ppt.pptx")
    ppt_path = os.path.normpath(ppt_path)
    if not os.path.exists(ppt_path):
        return jsonify({"ok": False, "error": "PPT template not found"}), 404
    return send_file(ppt_path, as_attachment=True,
                     download_name="ZenoFest Project Expo PPT Template.pptx",
                     mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@app.get("/health")
def health():
    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8081"))
    app.run(host="0.0.0.0", port=port, threaded=True)