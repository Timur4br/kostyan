"""Manage only the PostgreSQL cluster owned by this project. No Windows service."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
import psycopg
from psycopg import sql


def configure():
    env = ROOT / '.env'
    if not env.exists():
        password = secrets.token_hex(24)
        env.write_text(f'POSTGRES_DB=iskra\nPOSTGRES_USER=iskra\nPOSTGRES_PASSWORD={password}\nPOSTGRES_PORT=54329\nDATABASE_URL=postgresql+psycopg://iskra:{password}@127.0.0.1:54329/iskra\n', encoding='utf-8')
    load_dotenv(env)


def pg_bin():
    if value := os.getenv('PG_BIN'):
        directory = Path(value)
        if not (directory / 'pg_ctl.exe').exists():
            raise RuntimeError('PG_BIN must point to a PostgreSQL bin directory.')
        return directory
    parent = Path(os.getenv('ProgramFiles', 'C:/Program Files')) / 'PostgreSQL'
    candidates = sorted(parent.glob('*/bin/pg_ctl.exe'), key=lambda p: tuple(int(s) for s in p.parents[1].name.split('.') if s.isdigit()), reverse=True)
    if not candidates:
        raise RuntimeError('PostgreSQL not found. Install PostgreSQL 17+ or set PG_BIN in .env. Docker alternative: docker compose up -d db.')
    return candidates[0].parent


def run(binary, *args, check=True):
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    # A background postgres can inherit pipe handles. A file avoids communicate() hanging.
    output_path = ROOT / 'data' / 'launcher.log'
    with output_path.open('wb') as output:
        result = subprocess.run([str(binary), *map(str, args)], cwd=ROOT, creationflags=flags, stdout=output, stderr=subprocess.STDOUT, timeout=30)
    output = output_path.read_bytes()
    if output:
        print(output.decode('utf-8', errors='replace'))
    if check and result.returncode:
        raise RuntimeError(f'{binary.name} failed with code {result.returncode}.')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    action = parser.parse_args().action
    configure()
    binaries = pg_bin()
    # Relative CLI paths avoid Windows code-page problems with the Cyrillic project name.
    data = Path('data') / 'postgres'
    os.chdir(ROOT)
    if action != 'start':
        if not (data / 'PG_VERSION').exists():
            print('Project PostgreSQL cluster has not been initialized.')
            return
        if action == 'status':
            with psycopg.connect(host='127.0.0.1', port=int(os.getenv('POSTGRES_PORT', '54329')), user=os.getenv('POSTGRES_USER', 'iskra'), password=os.environ['POSTGRES_PASSWORD'], dbname=os.getenv('POSTGRES_DB', 'iskra'), connect_timeout=5, options='-c statement_timeout=5000') as connection:
                connection.execute('SELECT 1')
            print('Project PostgreSQL is ready.')
            return
        args = ['-D', data, action]
        if action == 'stop':
            args += ['-m', 'fast', '-w', '-t', '15']
        result = run(binaries / 'pg_ctl.exe', *args, check=False)
        sys.exit(result.returncode)
    data.parent.mkdir(exist_ok=True)
    if not (data / 'PG_VERSION').exists():
        if data.exists() and any(data.iterdir()):
            raise RuntimeError('The project cluster directory is not empty. Preserve it and inspect before initialization.')
        password_file = Path('data') / '.pg-password.tmp'
        try:
            password_file.write_text(os.environ['POSTGRES_PASSWORD'] + '\n', encoding='utf-8')
            run(binaries / 'initdb.exe', '-D', data, '-U', os.getenv('POSTGRES_USER', 'iskra'), '--pwfile', password_file, '--auth-host=scram-sha-256', '--auth-local=scram-sha-256', '--encoding=UTF8', '--locale=C')
        finally:
            password_file.unlink(missing_ok=True)
    port = int(os.getenv('POSTGRES_PORT', '54329'))
    params = dict(host='127.0.0.1', port=port, user=os.getenv('POSTGRES_USER', 'iskra'), password=os.environ['POSTGRES_PASSWORD'], dbname='postgres', connect_timeout=5, options='-c statement_timeout=5000')
    import socket
    with socket.socket() as probe:
        probe.settimeout(2)
        running = probe.connect_ex(('127.0.0.1', port)) == 0
    if not running:
        run(binaries / 'pg_ctl.exe', '-D', data, '-l', Path('data') / 'postgres.log', '-o', f'-p {port} -h 127.0.0.1', '-w', 'start')
    with psycopg.connect(**params, autocommit=True) as connection:
        name = os.getenv('POSTGRES_DB', 'iskra')
        if not connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', (name,)).fetchone():
            connection.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    print(f'Project PostgreSQL ready at 127.0.0.1:{port}.')


if __name__ == '__main__':
    main()
