import pytest
from app import crypto_app


@pytest.fixture
def client():
    app = crypto_app({'TESTING': True, 'DEBUG': True, 'CRYPTO_API_KEY': 'ed98eecf8e94d2629cd7979c059c74b8', 'BACKGROUND_TASK': False})

    with app.test_client() as client:
        yield client


def test_empty_shelf(client):
    """Start with an empty shelf database."""
    r = client.get('/crypto/sign?message=test')
    assert b'No entries here so far' in r.data


def test_request(client):
    """Start with an empty shelf database."""

    r = client.get('/')
    assert b'No entries here so far' in r.data



def test_request2(client):
    """Start with an empty shelf database."""

    r = client.get('/')
    assert False


