from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import re

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from .database import Base, ROOT, database_url, make_engine, session_factory
from .models import Camera, DetectionEvent, EventType, Location, ObjectType, SearchHistory, TrackedObject, VideoSegment
from .seed import seed_demo

TZ = ZoneInfo('Asia/Yekaterinburg')
logger = logging.getLogger(__name__)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)

    @field_validator('query')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('Введите название предмета')
        return value


def get_session(request: Request):
    with request.app.state.sessions() as session:
        yield session


def local_date(value):
    # SQLite in tests drops offsets; production PostgreSQL preserves UTC timestamps.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(TZ)


def detection_rows(session):
    statement = select(DetectionEvent, TrackedObject, Location, EventType, ObjectType).join(TrackedObject, DetectionEvent.object_id == TrackedObject.id).join(Location, DetectionEvent.location_id == Location.id).join(EventType, DetectionEvent.event_type_id == EventType.id).join(ObjectType, TrackedObject.object_type_id == ObjectType.id).order_by(DetectionEvent.observed_at.desc(), DetectionEvent.id.desc())
    return session.execute(statement).all()


def serialize_detection(row):
    event, obj, place, kind, _ = row
    observed = local_date(event.observed_at)
    return dict(id=obj.id, event_id=event.id, name=obj.name, place=place.name, detail=event.description, cam=event.camera_id, time=observed.strftime('%H:%M'), observed_at=observed.isoformat(), date=observed.strftime('%d.%m.%Y'), confidence=round(event.confidence * 100), type=kind.name, color=obj.color, x=obj.demo_x, y=obj.demo_y, video_segment_id=event.video_segment_id)


def latest_objects(session):
    seen = set()
    result = []
    for row in detection_rows(session):
        if row[1].id not in seen:
            seen.add(row[1].id)
            result.append((serialize_detection(row), row[4].aliases))
    return result


def create_app(url=None):
    @asynccontextmanager
    async def lifespan(app):
        engine = make_engine(url or database_url())
        try:
            Base.metadata.create_all(engine)
            app.state.sessions = session_factory(engine)
            with app.state.sessions() as session:
                seed_demo(session)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title='Искра — API', version='0.1.0', description='Локальный прототип с PostgreSQL и демонстрационными обнаружениями. Распознавание видео пока не подключено.', lifespan=lifespan, docs_url='/api/docs', openapi_url='/api/openapi.json', redoc_url=None)

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.exception('Request failed: %s', request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={'detail': 'Ошибка сервера. Повторите запрос или проверьте журнал.'})

    @app.get('/api/health')
    def health(session: Session = Depends(get_session)):
        session.execute(text('SELECT 1'))
        return {'app': 'iskra', 'status': 'ok', 'database': session.bind.dialect.name, 'mode': 'demo', 'version': '0.1.0'}

    @app.get('/api/objects')
    def get_objects(session: Session = Depends(get_session)):
        return [item for item, _ in latest_objects(session)]

    @app.get('/api/cameras')
    def get_cameras(session: Session = Depends(get_session)):
        return [dict(id=c.id, name=c.name, label=f'CAM {c.id:02}', resolution=c.resolution, fps=c.fps, status=c.status, location_id=c.location_id) for c in session.scalars(select(Camera).order_by(Camera.id))]

    @app.get('/api/events')
    def get_events(camera_id: int | None = Query(None, gt=0), q: str = Query('', max_length=300), session: Session = Depends(get_session)):
        rows = [serialize_detection(row) for row in detection_rows(session)]
        return [r for r in rows if (camera_id is None or r['cam'] == camera_id) and q.casefold() in f"{r['name']} {r['place']} {r['type']}".casefold()]

    @app.post('/api/search')
    def search(body: SearchRequest, session: Session = Depends(get_session)):
        query = body.query.casefold().replace('ё', 'е')
        source = latest_objects(session)
        result = [obj for obj, aliases in source if any(alias in query for alias in aliases.split(','))]
        if not result and re.search(r'\b(все|вещи|предметы)\b', query):
            result = [obj for obj, _ in source]
        if not result:
            result = [obj for obj, _ in source if obj['place'].casefold()[:5] in query]
        history = SearchHistory(user_id=1, query=body.query, result_count=len(result), created_at=datetime.now(timezone.utc))
        session.add(history)
        session.commit()
        return {'query': body.query, 'items': result, 'count': len(result), 'history_id': history.id, 'search_mode': 'dictionary'}

    @app.get('/api/history')
    def get_history(limit: int = Query(50, ge=1, le=200), session: Session = Depends(get_session)):
        rows = session.scalars(select(SearchHistory).where(SearchHistory.user_id == 1).order_by(SearchHistory.created_at.desc(), SearchHistory.id.desc()).limit(limit))
        return [dict(id=h.id, query=h.query, count=h.result_count, date=local_date(h.created_at).strftime('%d.%m.%Y, %H:%M'), created_at=local_date(h.created_at).isoformat()) for h in rows]

    @app.delete('/api/history', status_code=204)
    def clear_history(session: Session = Depends(get_session)):
        session.execute(delete(SearchHistory).where(SearchHistory.user_id == 1))
        session.commit()

    @app.get('/api/video-segments/{segment_id}')
    def get_video(segment_id: int, session: Session = Depends(get_session)):
        video = session.get(VideoSegment, segment_id)
        if video is None:
            raise HTTPException(status_code=404, detail='Видеофрагмент не найден')
        return dict(id=video.id, camera_id=video.camera_id, duration=video.duration_seconds, source_kind=video.source_kind, url=None, notice='Синтетическая анимация. Реальная запись пока не подключена.')

    app.mount('/', StaticFiles(directory=ROOT / 'frontend', html=True), name='frontend')
    return app


app = create_app()
