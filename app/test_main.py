import pytest
import json
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_index(client):
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'service' in data


def test_liveness(client):
    response = client.get('/health/live')
    assert response.status_code == 200
    assert json.loads(response.data)['status'] == 'alive'


def test_readiness_redis_down(client):
    with patch('app.main.get_redis', return_value=None):
        response = client.get('/health/ready')
        assert response.status_code == 503


def test_readiness_redis_up(client):
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    with patch('app.main.get_redis', return_value=mock_redis):
        response = client.get('/health/ready')
        assert response.status_code == 200


def test_counter_get(client):
    mock_redis = MagicMock()
    mock_redis.get.return_value = '42'
    with patch('app.main.get_redis', return_value=mock_redis):
        response = client.get('/counter')
        assert response.status_code == 200
        assert json.loads(response.data)['counter'] == 42


def test_counter_post(client):
    mock_redis = MagicMock()
    mock_redis.incr.return_value = 43
    with patch('app.main.get_redis', return_value=mock_redis):
        response = client.post('/counter')
        assert response.status_code == 200
        assert json.loads(response.data)['counter'] == 43


def test_counter_redis_down(client):
    with patch('app.main.get_redis', return_value=None):
        response = client.get('/counter')
        assert response.status_code == 503


def test_metrics(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b'http_requests_total' in response.data