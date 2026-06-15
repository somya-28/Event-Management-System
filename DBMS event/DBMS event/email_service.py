#!/usr/bin/env python3
"""
Email Service for Guest Invitations
Sends QR code invitations with event details automatically
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from flask import current_app
import qrcode
import io


class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_username)

    def generate_qr_code(self, guest):
        """Generate QR code using the SAME token and JSON format that
        qr_service.verify_qr_code() expects, so the scanner can validate it."""
        import json

        # Use the token already stored in the DB (set during guest creation).
        # If somehow it's missing, generate one on the fly using the same algo.
        token = guest.qr_token
        if not token:
            import hashlib
            from datetime import datetime as _dt
            data = f"{guest.id}:{guest.event_id}:{_dt.utcnow().isoformat()}"
            token = hashlib.sha256(data.encode()).hexdigest()[:32]

        # Build the exact JSON structure verify_qr_code() parses
        qr_payload = json.dumps({
            "guest_id": guest.id,
            "event_id": guest.event_id,
            "token": token,
            "name": guest.name,
        })

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#2d2d2d", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def get_location_url(self, event):
        """Build a Google Maps URL for the event location"""
        if not event.location:
            return None
        # If we have coordinates, use them for a precise pin
        if hasattr(event, 'latitude') and hasattr(event, 'longitude') \
                and event.latitude and event.longitude:
            return (
                f"https://www.google.com/maps?q="
                f"{event.latitude},{event.longitude}"
            )
        # Otherwise search by address text
        import urllib.parse
        query = urllib.parse.quote(event.location)
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    def send_guest_invitation(self, guest, event, host_name):
        """Send invitation email to guest with QR code embedded in body"""
        if not guest.email:
            return False, "Guest email is required"

        try:
            # ── 1. Generate QR code ──────────────────────────────────────
            qr_buffer = self.generate_qr_code(guest)

            # ── 2. Build correct MIME tree ───────────────────────────────
            #   multipart/related
            #     └── multipart/alternative
            #           └── text/html   (references cid:qr_code)
            #     └── image/png  (Content-ID: qr_code)

            msg_root = MIMEMultipart('related')
            msg_root['Subject'] = f"🎉 You're Invited: {event.name}"
            msg_root['From'] = f"Nexus Event Planner <{self.from_email}>"
            msg_root['To'] = guest.email

            # Alternative wrapper (required so HTML renders properly)
            msg_alt = MIMEMultipart('alternative')
            msg_root.attach(msg_alt)

            # HTML part
            location_url = self.get_location_url(event)
            html_body = self.create_invitation_html(
                guest, event, host_name, location_url
            )
            msg_alt.attach(MIMEText(html_body, 'html', 'utf-8'))

            # Inline QR image (must come AFTER alternative in related)
            qr_image = MIMEImage(qr_buffer.getvalue(), _subtype='png')
            qr_image.add_header('Content-ID', '<qr_code>')
            qr_image.add_header(
                'Content-Disposition', 'inline', filename='checkin_qr.png'
            )
            msg_root.attach(qr_image)

            # ── 3. Send ──────────────────────────────────────────────────
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg_root)

            return True, "Invitation sent successfully"

        except Exception as e:
            return False, f"Failed to send invitation: {str(e)}"

    # ─────────────────────────────────────────────────────────────────────────
    def create_invitation_html(self, guest, event, host_name, location_url=None):
        """Create a beautiful, complete HTML invitation email"""

        # ── Event date / time strings ──────────────────────────────────
        try:
            date_str = event.event_date.strftime('%A, %B %d, %Y')
        except Exception:
            date_str = str(event.event_date)

        time_str = ''
        if event.event_time:
            try:
                time_str = event.event_time.strftime('%I:%M %p')
            except Exception:
                time_str = str(event.event_time)

        # ── Location block ─────────────────────────────────────────────
        location_html = ''
        if event.location:
            if location_url:
                location_html = f'''
                <tr>
                  <td class="detail-icon">📍</td>
                  <td class="detail-text">
                    <strong>Venue</strong><br>
                    {event.location}<br>
                    <a href="{location_url}" class="map-btn"
                       target="_blank">🗺️ Open in Google Maps</a>
                  </td>
                </tr>'''
            else:
                location_html = f'''
                <tr>
                  <td class="detail-icon">📍</td>
                  <td class="detail-text"><strong>Venue</strong><br>{event.location}</td>
                </tr>'''

        # ── Time row ───────────────────────────────────────────────────
        time_html = ''
        if time_str:
            time_html = f'''
                <tr>
                  <td class="detail-icon">🕐</td>
                  <td class="detail-text"><strong>Time</strong><br>{time_str}</td>
                </tr>'''

        # ── Guest count row ────────────────────────────────────────────
        guest_count_html = ''
        if guest.guest_count and guest.guest_count > 1:
            guest_count_html = f'''
                <tr>
                  <td class="detail-icon">👥</td>
                  <td class="detail-text">
                    <strong>Party Size</strong><br>{guest.guest_count} guests
                  </td>
                </tr>'''

        # ── Dietary row ────────────────────────────────────────────────
        dietary_html = ''
        if guest.dietary_requirements:
            dietary_html = f'''
                <tr>
                  <td class="detail-icon">🍽️</td>
                  <td class="detail-text">
                    <strong>Dietary Requirements</strong><br>{guest.dietary_requirements}
                  </td>
                </tr>'''

        # ── Description ────────────────────────────────────────────────
        desc_html = ''
        if event.description:
            desc_html = f'<p class="desc">{event.description}</p>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>You're Invited – {event.name}</title>
  <style>
    /* ── Reset ── */
    body, table, td, a {{ -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; }}
    table, td {{ mso-table-lspace:0pt; mso-table-rspace:0pt; }}
    img {{ -ms-interpolation-mode:bicubic; border:0; outline:none; text-decoration:none; }}

    body {{
      margin:0; padding:0;
      background-color:#f0f2f5;
      font-family: 'Segoe UI', Arial, sans-serif;
    }}

    /* ── Outer wrapper ── */
    .wrapper {{
      width:100%; background-color:#f0f2f5; padding:30px 0;
    }}

    /* ── Card ── */
    .card {{
      max-width:600px; margin:0 auto;
      background:#ffffff;
      border-radius:16px;
      overflow:hidden;
      box-shadow:0 8px 32px rgba(0,0,0,0.12);
    }}

    /* ── Header banner ── */
    .header {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding:40px 30px 30px;
      text-align:center;
      color:#ffffff;
    }}
    .header .emoji {{ font-size:48px; line-height:1; }}
    .header h1 {{
      margin:12px 0 4px;
      font-size:28px;
      font-weight:700;
      letter-spacing:-0.5px;
    }}
    .header .subtitle {{
      margin:0;
      font-size:15px;
      opacity:0.85;
    }}

    /* ── Body ── */
    .body {{ padding:32px 36px; }}
    .greeting {{
      font-size:20px;
      font-weight:600;
      color:#1a1a2e;
      margin:0 0 8px;
    }}
    .intro {{
      font-size:15px;
      color:#555;
      line-height:1.6;
      margin:0 0 28px;
    }}
    .desc {{
      font-size:14px;
      color:#666;
      line-height:1.65;
      background:#f8f9fc;
      border-left:3px solid #667eea;
      padding:12px 16px;
      border-radius:4px;
      margin:0 0 24px;
    }}

    /* ── Details table ── */
    .details-section {{ margin-bottom:28px; }}
    .section-title {{
      font-size:13px;
      font-weight:700;
      text-transform:uppercase;
      letter-spacing:1px;
      color:#667eea;
      margin:0 0 14px;
    }}
    .details-table {{ width:100%; border-collapse:collapse; }}
    .details-table tr {{ border-bottom:1px solid #f0f0f0; }}
    .details-table tr:last-child {{ border-bottom:none; }}
    .detail-icon {{
      padding:12px 14px 12px 0;
      font-size:20px;
      vertical-align:top;
      width:36px;
    }}
    .detail-text {{
      padding:12px 0;
      font-size:14px;
      color:#333;
      vertical-align:top;
      line-height:1.55;
    }}

    /* ── Map button ── */
    .map-btn {{
      display:inline-block;
      margin-top:7px;
      padding:7px 16px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color:#ffffff !important;
      text-decoration:none;
      border-radius:20px;
      font-size:13px;
      font-weight:600;
    }}

    /* ── QR section ── */
    .qr-section {{
      background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
      border:2px dashed #c5cdf8;
      border-radius:12px;
      padding:28px 20px;
      text-align:center;
      margin-bottom:28px;
    }}
    .qr-section h3 {{
      margin:0 0 6px;
      font-size:16px;
      color:#1a1a2e;
    }}
    .qr-section p {{
      margin:0 0 18px;
      font-size:13px;
      color:#777;
    }}
    .qr-section img {{
      width:180px;
      height:180px;
      border-radius:8px;
      border:3px solid #667eea;
      padding:6px;
      background:#fff;
    }}
    .qr-note {{
      display:block;
      margin-top:10px;
      font-size:12px;
      color:#999;
    }}

    /* ── Sign-off ── */
    .signoff {{
      font-size:14px;
      color:#555;
      line-height:1.6;
      margin:0 0 8px;
    }}
    .host-name {{ font-weight:700; color:#1a1a2e; }}

    /* ── Footer ── */
    .footer {{
      background:#f8f9fc;
      padding:20px 36px;
      text-align:center;
      border-top:1px solid #eee;
    }}
    .footer p {{
      margin:4px 0;
      font-size:12px;
      color:#aaa;
    }}
  </style>
</head>
<body>
<div class="wrapper">
  <div class="card">

    <!-- HEADER -->
    <div class="header">
      <div class="emoji">🎉</div>
      <h1>You're Invited!</h1>
      <p class="subtitle">A personal invitation just for you</p>
    </div>

    <!-- BODY -->
    <div class="body">
      <p class="greeting">Hello {guest.name},</p>
      <p class="intro">
        <strong>{host_name}</strong> cordially invites you to
        <strong>{event.name}</strong>. We'd love to have you join us for
        what promises to be a wonderful event!
      </p>

      {desc_html}

      <!-- EVENT DETAILS -->
      <div class="details-section">
        <p class="section-title">📋 Event Details</p>
        <table class="details-table">
          <tr>
            <td class="detail-icon">📅</td>
            <td class="detail-text"><strong>Date</strong><br>{date_str}</td>
          </tr>
          {time_html}
          {location_html}
          {guest_count_html}
          {dietary_html}
        </table>
      </div>

      <!-- QR CODE -->
      <div class="qr-section">
        <h3>📱 Your Check-in QR Code</h3>
        <p>Show this at the entrance for instant, contactless check-in</p>
        <img src="cid:qr_code" alt="Check-in QR Code">
        <span class="qr-note">🔒 This QR code is unique to you — please do not share it</span>
      </div>

      <!-- SIGN-OFF -->
      <p class="signoff">
        We look forward to celebrating with you!<br><br>
        Warm regards,<br>
        <span class="host-name">{host_name}</span>
      </p>
    </div>

    <!-- FOOTER -->
    <div class="footer">
      <p>This invitation was sent by the Event Management System</p>
      <p>If you have questions, please contact your event organiser directly.</p>
    </div>

  </div>
</div>
</body>
</html>"""


# Global email service instance
email_service = EmailService()
