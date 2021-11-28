import pytest
from app import crypto_app


@pytest.fixture
def client():

    app = crypto_app({'TESTING': True})

    with app.test_client() as client:
        yield client

