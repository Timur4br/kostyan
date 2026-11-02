"""User-run upload to a separate GitHub branch; no force pushes or file removal."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REMOTE = 'https://github.com/AlexeyKobelev/kostyan.git'
SOURCE = ['.env.example', '.gitignore', 'README.md', 'Setup.cmd', 'Start.cmd',
          'Stop-Database.cmd', 'Publish-GitHub.cmd', 'requirements.txt',
          'requirements.lock.txt', 'compose.yaml', 'backend', 'frontend',
          'tests', 'scripts', 'docs', 'data/.gitkeep']


def git(*args, capture=False, check=True):
    # OpenSSL avoids Windows Schannel credential issues while keeping TLS verification.
    # This known project was created by the agent account. Trust this exact path
    # for this command only, without writing a global safe.directory exception.
    return subprocess.run(['git', '-c', 'safe.directory=' + ROOT.as_posix(),
                           '-c', 'http.sslBackend=openssl', *args], cwd=ROOT,
                          text=True, encoding='utf-8', errors='replace',
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None, check=check)


def main():
    print('Repository: ' + REMOTE, flush=True)
    print('Upload source only, on a separate branch. Main will stay unchanged.', flush=True)
    if not (ROOT / '.git').exists():
        git('init', '--initial-branch=main')
    remote = git('remote', 'get-url', 'origin', capture=True, check=False)
    if remote.returncode:
        git('remote', 'add', 'origin', REMOTE)
    elif remote.stdout.strip().removesuffix('.git') != REMOTE.removesuffix('.git'):
        raise RuntimeError('Origin points to another repository. Nothing uploaded.')

    git('fetch', '--no-tags', 'origin', 'main')
    head = git('rev-parse', '--verify', 'HEAD', capture=True, check=False)
    if head.returncode:
        files = git('ls-tree', '-r', '--name-only', 'FETCH_HEAD', capture=True).stdout.splitlines()
        if any(name != 'README.md' for name in files):
            raise RuntimeError('Remote now contains more than README.md. Review it before importing the project.')
        # On an unborn local branch only: adopt remote ancestry without changing working files.
        git('reset', '--mixed', 'FETCH_HEAD')
    else:
        ancestor = git('merge-base', '--is-ancestor', 'FETCH_HEAD', 'HEAD', check=False)
        if ancestor.returncode:
            raise RuntimeError('Local history differs from main. Reconcile it before publishing; no history was overwritten.')

    branch = 'iskra-backend-' + datetime.now().strftime('%Y%m%d-%H%M%S')
    git('switch', '-c', branch)
    identity = git('var', 'GIT_AUTHOR_IDENT', capture=True, check=False)
    if identity.returncode:
        print('Git needs the name and email to display on your commits.')
        name = input('Author name: ').strip()
        email = input('Author email (GitHub noreply address is also supported): ').strip()
        if not name or not email:
            raise RuntimeError('Author identity is required. Nothing uploaded.')
        git('config', 'user.name', name)
        git('config', 'user.email', email)

    git('add', '--', *SOURCE)
    staged = git('diff', '--cached', '--name-only', capture=True).stdout.splitlines()
    for name in staged:
        path = Path(name)
        if name == '.env' or '.venv' in path.parts or '__pycache__' in path.parts or '.pytest_cache' in path.parts or (name.startswith('data/') and name != 'data/.gitkeep') or name.endswith('.log'):
            raise RuntimeError('Excluded local data is staged: ' + name + '. Nothing uploaded.')
    print('Files prepared for commit:', flush=True)
    git('diff', '--cached', '--stat')
    if staged:
        git('commit', '-m', 'Add Iskra FastAPI backend, PostgreSQL and web interface')
    git('push', '--set-upstream', 'origin', branch)
    print('\nUpload complete. Branch:', branch, flush=True)
    print('Open: https://github.com/AlexeyKobelev/kostyan/tree/' + branch, flush=True)
    print('To review and merge: https://github.com/AlexeyKobelev/kostyan/compare/main...' + branch, flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print('\nUpload stopped:', exc, flush=True)
        print('No force push was performed. Keep the error text for troubleshooting.', flush=True)
        sys.exit(1)
