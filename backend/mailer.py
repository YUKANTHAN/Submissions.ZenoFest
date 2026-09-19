"""
Email sender for ZenoFest submission confirmations.
Uses SendGrid HTTP API (works on Render free tier — SMTP is blocked).
"""
import os
import base64
import json
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
MAIL_FROM_EMAIL = os.environ.get("MAIL_FROM_EMAIL", "pgyukanthan@gmail.com")
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "ZenoFest 2026")
MAIL_REPLY_TO = os.environ.get("MAIL_REPLY_TO", "pgyukanthan@gmail.com")


def is_configured():
    return bool(SENDGRID_API_KEY)


def _sendgrid_send(to_email, subject, html_body,
                   attachment_name=None, attachment_bytes=None):
    personalization = {
        "to": [{"email": to_email}],
        "subject": subject,
    }
    content = {"type": "text/html", "value": html_body}

    payload = {
        "personalizations": [personalization],
        "from": {"email": MAIL_FROM_EMAIL, "name": MAIL_FROM_NAME},
        "reply_to": {"email": MAIL_REPLY_TO, "name": MAIL_FROM_NAME},
        "content": [content],
    }

    if attachment_bytes is not None and attachment_name:
        encoded = base64.b64encode(attachment_bytes).decode("utf-8")
        payload["attachments"] = [{
            "content": encoded,
            "filename": attachment_name,
        }]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=data,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status


def send_confirmation_email(to_email, subject, html_body,
                            attachment_name=None, attachment_bytes=None):
    _sendgrid_send(to_email, subject, html_body, attachment_name, attachment_bytes)


def _esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(team, form_data, labels, submitted_at, team_id):
    team_id = team_id or team.get("team_id") or ""
    event = team.get("tech_event") or ""
    name = team.get("team_name") or "there"
    leader = team.get("leader_name") or ""
    return f"""
<div style="background-color:#f7f6f2;padding:32px 12px;font-family:Georgia,'Times New Roman',serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr><td align="center">
      <table role="presentation" width="500" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border-radius:8px;padding:34px 40px;">
        <tr>
          <td style="text-align:center;padding-bottom:22px;">
            <div style="font-size:26px;font-weight:bold;color:#6A0DAD;letter-spacing:5px;">ZENOFEST</div>
            <div style="font-size:13px;color:#9a9a9a;letter-spacing:8px;margin-top:4px;">2K26</div>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:14px;color:#333333;font-size:16px;line-height:1.7;">
            Hi{', ' + _esc(leader) if leader else ''}!
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:18px;color:#444444;font-size:14px;line-height:1.75;">
            We've received your entry for the <b style="color:#6A0DAD;">{_esc(event)}</b> event.
            Thanks for submitting — we can't wait to see what you've built!
          </td>
        </tr>
        <tr>
          <td style="padding:14px 18px;background:#f6f2fa;border-left:3px solid #6A0DAD;border-radius:4px;
                  margin:0 0 18px;color:#333333;font-size:14px;font-family:Arial,Helvetica,sans-serif;">
            <span style="color:#8A2BE2;font-weight:bold;">{_esc(name)}</span>
            &nbsp;&middot;&nbsp; {_esc(event)}
            &nbsp;&middot;&nbsp; Team ID: <b>{_esc(team_id)}</b>
          </td>
        </tr>
        <tr>
          <td style="padding:8px 0 4px;color:#444444;font-size:13.5px;line-height:1.7;">
            Your submission summary is attached to this mail. Please keep it handy and
            show it at the fest if required.
          </td>
        </tr>
        <tr>
          <td style="padding:24px 0 6px;color:#333333;font-size:14px;line-height:1.6;">
            Take care,<br/>
            <b>Yukanthan</b><br/>
            <span style="color:#777777;">ZenoFest 2K26 Organizing Team</span>
          </td>
        </tr>
        <tr>
          <td style="padding-top:22px;border-top:1px solid #e8e5dd;color:#9a9a9a;font-size:11.5px;
                  font-family:Arial,Helvetica,sans-serif;text-align:center;">
            Questions? Just reply to this email &middot; ZenoFest 2K26
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</div>"""


def send_unauthorized_notification(submission_email, team_id, team_name, tech_event,
                                   leader_name, college, submitted_at, form_data, field_labels):
    """Notify the organizer about a submission from an unregistered email."""
    if not is_configured():
        return
    rows = ""
    for key, value in (form_data or {}).items():
        label = field_labels.get(key, key.replace("_", " ").title())
        rows += f"<tr><td style='padding:4px 12px 4px 0;color:#6A0DAD;font-weight:bold;font-size:13px;white-space:nowrap;'>{_esc(label)}</td><td style='padding:4px 0;color:#333;font-size:13px;'>{_esc(value)}</td></tr>"

    html = f"""
<div style="background-color:#f7f6f2;padding:32px 12px;font-family:Georgia,'Times New Roman',serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
    <tr><td align="center">
      <table role="presentation" width="500" cellpadding="0" cellspacing="0" border="0"
             style="background:#ffffff;border-radius:8px;padding:34px 40px;">
        <tr>
          <td style="text-align:center;padding-bottom:22px;">
            <div style="font-size:26px;font-weight:bold;color:#6A0DAD;letter-spacing:5px;">ZENOFEST</div>
            <div style="font-size:13px;color:#9a9a9a;letter-spacing:8px;margin-top:4px;">2K26</div>
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:6px;color:#ff5722;font-size:18px;font-weight:bold;">
            ⚠ Unauthorized Submission Alert
          </td>
        </tr>
        <tr>
          <td style="padding-bottom:18px;color:#444444;font-size:14px;line-height:1.75;">
            A submission was received from an email <b>not found</b> in the registration records.
            Details below:
          </td>
        </tr>
        <tr>
          <td style="padding:14px 18px;background:#fff3e0;border-left:3px solid #ff9800;border-radius:4px;
                  margin:0 0 18px;font-size:14px;font-family:Arial,Helvetica,sans-serif;">
            <b style="color:#e65100;">Email:</b> {_esc(submission_email)}<br/>
            <b style="color:#e65100;">Event:</b> {_esc(tech_event)}<br/>
            <b style="color:#e65100;">Submitted At:</b> {_esc(submitted_at)}
          </td>
        </tr>
        <tr>
          <td style="padding:12px 0 6px;color:#333;font-size:14px;font-weight:bold;">Submission Data:</td>
        </tr>
        <tr>
          <td>
            <table role="presentation" cellpadding="0" cellspacing="0" border="0"
                   style="width:100%;font-family:Arial,Helvetica,sans-serif;">
              {rows}
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding-top:24px;border-top:1px solid #e8e5dd;color:#9a9a9a;font-size:11.5px;
                  font-family:Arial,Helvetica,sans-serif;text-align:center;">
            ZenoFest 2K26 — Unauthorized Submission Notification
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</div>"""

    _sendgrid_send(
        to_email=MAIL_FROM_EMAIL,
        subject=f"⚠ ZenoFest 2026 - Unauthorized Submission from {submission_email}",
        html_body=html,
    )