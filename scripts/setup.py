import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
requirements = root / ('requirements.lock.txt' if (root / 'requirements.lock.txt').exists() else 'requirements.txt')
subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(requirements)], cwd=root, check=True)
subprocess.run([sys.executable, str(root / 'scripts' / 'database.py'), 'start'], cwd=root, check=True)
print('Setup complete. Run Start.cmd. Application: http://127.0.0.1:8000')
