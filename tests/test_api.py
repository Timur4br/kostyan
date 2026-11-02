from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from backend.app.main import create_app
from backend.app.models import DetectionEvent, SearchHistory


@pytest.fixture
def app(tmp_path):
    return create_app('sqlite:///' + (tmp_path / 'test.db').as_posix())


def test_seeded_data_search_and_video(app):
    with TestClient(app) as client:
        assert client.get('/api/health').json()['database'] == 'sqlite'
        assert len(client.get('/api/cameras').json()) == 3
        assert len(client.get('/api/objects').json()) == 6
        result = client.post('/api/search', json={'query': 'Где мои ключи?'}).json()
        assert result['count'] == 1
        assert result['items'][0]['id'] == 'keys'
        assert result['items'][0]['time'] == '14:32'
        video = client.get('/api/video-segments/' + str(result['items'][0]['video_segment_id'])).json()
        assert video['source_kind'] == 'synthetic'
        assert video['url'] is None
        assert client.get('/api/video-segments/999').status_code == 404


def test_search_validates_and_escapes_untrusted_queries(app):
    with TestClient(app) as client:
        for value in ['', '   ', 'a' * 301]:
            assert client.post('/api/search', json={'query': value}).status_code == 422
        assert client.post('/api/search', json={}).status_code == 422
        for value in ['зонтик', "'; DROP TABLE objects; --", '<script>alert(1)</script>']:
            result = client.post('/api/search', json={'query': value})
            assert result.status_code == 200
            assert result.json()['count'] == 0
        assert len(client.get('/api/objects').json()) == 6


def test_history_persists_after_application_restart(app):
    with TestClient(app) as client:
        client.post('/api/search', json={'query': 'Найди рюкзак'})
        with app.state.sessions() as session:
            saved = session.scalar(select(SearchHistory))
            assert saved.query == 'Найди рюкзак'
            assert saved.result_count == 1
    with TestClient(app) as client:
        history = client.get('/api/history').json()
        assert len(history) == 1
        assert history[0]['count'] == 1
        assert len(client.get('/api/objects').json()) == 6  # seed is idempotent
        assert client.delete('/api/history').status_code == 204
        assert client.get('/api/history').json() == []


def test_event_filters_and_latest_detection(app):
    with TestClient(app) as client:
        events = client.get('/api/events', params={'camera_id': 2}).json()
        assert len(events) == 2
        assert all(e['cam'] == 2 for e in events)
        assert len(client.get('/api/events', params={'camera_id': 2, 'q': 'бутылка'}).json()) == 1
        assert client.get('/api/events', params={'camera_id': -1}).status_code == 422
        assert client.get('/api/events', params={'q': 'a' * 301}).status_code == 422
        with app.state.sessions() as session:
            session.add(DetectionEvent(object_id='keys', camera_id=3, location_id=3, event_type_id=1, video_segment_id=3, observed_at=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc), confidence=.95, description='Новое обнаружение'))
            session.commit()
        result = client.post('/api/search', json={'query': 'ключи'}).json()
        assert result['count'] == 1
        assert result['items'][0]['place'] == 'Кухня'
        assert result['items'][0]['time'] == '16:00'
        assert len(client.get('/api/events').json()) == 7


def test_static_frontend_and_openapi(app):
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        assert client.get('/app.js').status_code == 200
        assert client.get('/api/docs').status_code == 200
        assert '/api/search' in client.get('/api/openapi.json').json()['paths']
