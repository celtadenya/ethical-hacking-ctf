# 🔐 Ethical Hacking CTF Writeup
Coventry University - 7072SCN Ethical Hacking and Penetration Testing

3-target CTF assessment. All flags captured.

## Overview

| Assessment | User | Root | Techniques |
|------------|------|------|------------|
| [sqli-file-upload](sqli-file-upload/writeup.md) | ✅ | ✅ | SQL injection, MIME bypass, sudo ftp |
| [blind-sqli-imagetragick](blind-sqli-imagetragick/writeup.md) | ✅ | ✅ | Boolean blind SQLi, CVE-2016-3714, sudo convert |
| [xss-cicd-privesc](xss-cicd-privesc/writeup.md) | ✅ | ✅ | CVE-2024-42008, pytest injection, git hook |

## What I used

`nmap` `gobuster` `ffuf` `burp suite` `python3` `netcat` `ssh` `curl` `gtfobins`

## Skills

- Web exploitation - SQLi, XSS, file upload bypass, MIME manipulation
- CVE exploitation - CVE-2024-42008 (Roundcube XSS), CVE-2016-3714 (ImageTragick)
- Recon - port scanning, directory brute force, vhost enumeration
- Privilege escalation - sudo misconfigs, SUID binaries, GTFOBins
- CI/CD abuse - pytest conftest.py injection, git hook execution
- Python scripting - custom XSS exfiltration payload (smtplib + HTTP listener)
- Burp Suite - request interception, MIME type manipulation

## Structure

```
ethical-hacking-ctf/
├── report.docx
├── sqli-file-upload/
│   └── writeup.md
├── blind-sqli-imagetragick/
│   └── writeup.md
└── xss-cicd-privesc/
    ├── writeup.md
    ├── xss_payload.py
    ├── conftest.py
    └── pre-commit
```

## Summaries

**[sqli-file-upload](sqli-file-upload/writeup.md)**

Ran nmap and gobuster on the target. Login page was injectable, `' OR 1=1--` got me straight into the admin panel. Upload function only accepted images so I used Burp to intercept the request, renamed the file to `shell.php.jpg`, swapped the Content-Type to `image/jpeg` and prepended JPEG magic bytes before the PHP payload. Server accepted it. Renamed it to `shell.php` through the admin panel and had RCE. Root came from `sudo ftp`, typed `!/bin/bash` at the ftp prompt and got a root shell.

**[blind-sqli-imagetragick](blind-sqli-imagetragick/writeup.md)**

Login form had boolean-based blind SQLi. Slowly pulled credentials out of the database, cracked the MD5 hash on crackstation, SSH'd in with the same password, classic reuse. Avatar upload on the profile page was running ImageMagick 6.9.2-10, vulnerable to CVE-2016-3714 (ImageTragick). Crafted a malicious image file to copy a PHP reverse shell into the web directory and got a www-data shell. Root via `sudo convert` with URL injection.

**[xss-cicd-privesc](xss-cicd-privesc/writeup.md)**

Found Roundcube 1.6.6 running on the target, unpatched CVE-2024-42008. Sent a malicious HTML email that injected a CSS animation into the body tag. When the victim opened it, their entire inbox got silently exfiltrated to my listener. Found SSH credentials in one of the emails. Once inside, noticed the CI/CD pipeline ran pytest from `/tmp` as admin, dropped a malicious `conftest.py` there and triggered the webhook to get a SUID bash. Root came from a `NOPASSWD: git commit` sudo rule, configured a malicious pre-commit hook and the flag wrote itself to `/tmp`.

## Report

Full pentest report with recon, CVSS v3.1 risk ratings, payloads and mitigations: [`report.docx`](report.pdf)

## Disclaimer

Done in an authorised academic lab as part of university coursework. Don't use any of this on systems you don't own.