from fastapi.testclient import TestClient
import sys
sys.path.append('sentiment_service')
from fastapi_sentiment import app

client = TestClient(app)

def test_score_basic():
    r = client.post('/score', json={"texts":["stock up on strong guidance","coin plunges after hack"]})
    assert r.status_code == 200
    data = r.json()
    assert 'scores' in data and len(data['scores']) == 2


def test_metrics_endpoint():
    r = client.get('/metrics')
    assert r.status_code in (200, 404)
