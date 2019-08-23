from starlette.testclient import TestClient

from fact_sender import Task
from fact_sender import app

client = TestClient(app)

dummy_task = Task
dummy_task.target_phone = ''


def test_get_random_path():
    pass


def test_get_fact():
    pass


def test_send_fact():
    pass


def test_send_sms():
    pass


def test_warmup():
    response = client.get("/_ah/warmup")
    assert response.status_code == 200
    assert response.json() == {'Response Code': '418'}
