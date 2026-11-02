import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {'connect_args': {'check_same_thread': False}} if url.startswith('sqlite') else {'connect_args': {'connect_timeout': 5}}
    engine = create_engine(url, pool_pre_ping=True, **kwargs)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def enable_foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine


def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def database_url():
    value = os.getenv('DATABASE_URL')
    if not value:
        raise RuntimeError('DATABASE_URL is missing. Run scripts/Setup.ps1 first.')
    return value
