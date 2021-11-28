import pytest
from app import crypto_app


@pytest.fixture
def client():
    app = crypto_app({'TESTING': True, 'DEBUG': True, 'CRYPTO_API_KEY': 'DUMMY_API_KEY', 'BACKGROUND_TASK': False})

    with app.test_client() as client:
        yield client


def test_empty_shelf(client):
    """Verify response structure."""
    r = client.get('/crypto/sign?message=test')
    assert b'success' in r.data
    assert b'last_status_code' in r.data
    assert b'value' in r.data
