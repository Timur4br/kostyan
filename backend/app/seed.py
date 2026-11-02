from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import Integer, func, select, text

from .models import Camera, DetectionEvent, EventType, Location, ObjectType, TrackedObject, User, VideoSegment
from .database import Base

DEMO_OBJECTS = [
    ('keys', 'Ключи', 'ключ,keys', 1, '14:32', 98, 1, 'На столе, рядом с блокнотом', '#bfa66c', 515, 322),
    ('bag', 'Рюкзак', 'рюкзак,сумк,bag', 2, '14:28', 96, 2, 'У рабочего стола № 4', '#596e55', 565, 325),
    ('phone', 'Телефон', 'телефон,смартфон,phone', 3, '14:21', 99, 1, 'На стойке у кофемашины', '#40585c', 488, 318),
    ('bottle', 'Бутылка воды', 'бутыл,вод,bottle', 2, '14:15', 94, 1, 'На рабочем столе № 2', '#86a8a1', 450, 300),
    ('headphones', 'Наушники', 'наушник,headphone', 1, '14:08', 93, 2, 'На кресле рядом со столом', '#414d47', 600, 350),
    ('book', 'Блокнот', 'блокнот,тетрад,книг', 1, '13:54', 97, 1, 'На столе, возле ключей', '#ae8261', 445, 315),
]


def seed_demo(session):
    if session.scalar(select(User.id).limit(1)) is not None:
        return
    session.add(User(id=1, name='Локальный пользователь'))
    places = ['Переговорная', 'Рабочая зона', 'Кухня']
    session.add_all([Location(id=i, name=name, description='Демонстрационная комната') for i, name in enumerate(places, 1)])
    session.flush()
    session.add_all([Camera(id=i, location_id=i, name=name, resolution='2560 × 1440' if i == 2 else '1920 × 1080', fps=30 if i == 2 else 25, status='demo') for i, name in enumerate(places, 1)])
    session.add_all([EventType(id=1, name='Положили'), EventType(id=2, name='Оставили')])
    session.add_all([ObjectType(id=i, name=o[1], aliases=o[2]) for i, o in enumerate(DEMO_OBJECTS, 1)])
    session.flush()
    for i, (key, name, _, cam, time, confidence, kind, detail, color, x, y) in enumerate(DEMO_OBJECTS, 1):
        session.add(TrackedObject(id=key, object_type_id=i, name=name, color=color, demo_x=x, demo_y=y))
        session.add(VideoSegment(id=i, camera_id=cam, duration_seconds=12, source_kind='synthetic'))
        session.flush()
        observed = datetime.fromisoformat('2026-11-02T' + time + ':06').replace(tzinfo=ZoneInfo('Asia/Yekaterinburg')).astimezone(timezone.utc)
        session.add(DetectionEvent(id=i, object_id=key, camera_id=cam, location_id=cam, event_type_id=kind, video_segment_id=i, observed_at=observed, confidence=confidence / 100, description=detail))
    session.flush()
    if session.bind.dialect.name == 'postgresql':
        # Explicit demo IDs must not leave PostgreSQL sequences behind inserted rows.
        for table in Base.metadata.sorted_tables:
            column = table.c.get('id')
            if column is not None and isinstance(column.type, Integer):
                maximum = session.scalar(select(func.max(column)))
                if maximum is not None:
                    session.execute(text("SELECT setval(pg_get_serial_sequence(:table, 'id'), :maximum, true)"), {'table': table.name, 'maximum': maximum})
    session.commit()
