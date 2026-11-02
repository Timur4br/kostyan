import subprocess
import sys
from pathlib import Path
import json
import urllib.request

root = Path(__file__).resolve().parents[1]
try:
    with urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2) as response:
        healthy = json.load(response)
    if healthy.get('app') == 'iskra':
        print('Iskra is already running: http://127.0.0.1:8000', flush=True)
        sys.exit(0)
except (OSError, ValueError):
    pass
result = subprocess.run([sys.executable, str(root / 'scripts' / 'database.py'), 'start'], cwd=root)
if result.returncode:
    sys.exit(result.returncode)
print('Iskra: http://127.0.0.1:8000', flush=True)
print('API: http://127.0.0.1:8000/api/docs', flush=True)
print('Press Ctrl+C to stop the app. Stop-Database.cmd stops the project database.', flush=True)
try:
    result = subprocess.run([sys.executable, '-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000'], cwd=root)
    sys.exit(result.returncode)
except KeyboardInterrupt:
    pass
