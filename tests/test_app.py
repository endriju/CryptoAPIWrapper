import pytest
from unittest.mock import patch
import json
from app import crypto_app, shelf, queue

app = crypto_app({'TESTING': True, 'DEBUG': True, 'CRYPTO_API_KEY': 'DUMMY_API_KEY', 'BACKGROUND_TASK': False})


# TODO rewrite app using create_app to enable mocking
# @pytest.fixture
# def app(mocker):
#     mocker.patch("app.crypto_sign_call", return_value = {
#         "last_status_code": 502,
#         "retry_in_seconds": 36,
#         "success": False,
#         "value": "Error 502: Failed to sign message due to simulated service degradation.\n"
#     })
#     return app


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_response_fields(client):
    r = client.get('/crypto/sign?message=test')
    assert is_json(r.data)
    assert b'message' in r.data
    assert b'success' in r.data
    assert b'last_status_code' in r.data
    assert b'value' in r.data


def test_when_response_in_shelf(client):
    shelf.clear()
    assert len(shelf.keys()) == 0
    r1 = client.get('/crypto/sign?message=test2')
    assert len(shelf.keys()) == 1
    assert is_json(r1.data)


def is_json(json_value):
  try:
    json.loads(json_value)
  except ValueError as ex:
    return False
  return True