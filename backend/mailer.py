"""
Email sender for ZenoFest submission confirmations.
Uses SMTP (Gmail recommended) with an App Password.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "ZenoFest 2K26")


def is_configured():
    return bool(SMTP_USER and SMTP_PASSWORD)


def send_confirmation_email(to_email, subject, html_body,
                            attachment_name=None, attachment_bytes=None):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((MAIL_FROM_NAME, SMTP_USER))
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if attachment_bytes is not None:
        part = MIMEApplication(attachment_bytes, _subtype="pdf")
        part.add_header("Content-Disposition", "attachment", filename=attachment_name)
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


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

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"⚠ ZenoFest 2026 - Unauthorized Submission from {submission_email}"
    msg["From"] = formataddr((MAIL_FROM_NAME, SMTP_USER))
    msg["To"] = SMTP_USER
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)