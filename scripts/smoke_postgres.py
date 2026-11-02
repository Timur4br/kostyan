"""Check the real project DB; remove only history entries created by this check."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from backend.app.main import create_app
from backend.app.models import SearchHistory

app = create_app()
history_id = None
with TestClient(app) as client:
    assert client.get('/api/health').json()['database'] == 'postgresql'
    assert len(client.get('/api/objects').json()) == 6
    try:
        response = client.post('/api/search', json={'query': 'Где мои ключи?'})
        assert response.status_code == 200
        data = response.json()
        history_id = data['history_id']
        assert data['count'] == 1 and data['items'][0]['time'] == '14:32'
        with app.state.sessions() as session:
            saved = session.get(SearchHistory, history_id)
            assert saved is not None and saved.result_count == 1
        assert len(client.get('/api/events?camera_id=2').json()) == 2
    finally:
        if history_id:
            with app.state.sessions() as session:
                session.execute(delete(SearchHistory).where(SearchHistory.id == history_id))
                session.commit()
with TestClient(app) as client:
    assert len(client.get('/api/objects').json()) == 6
print('PostgreSQL integration: OK. Search, persistence, filters and restart verified.')
