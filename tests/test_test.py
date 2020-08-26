import pytest
import sys
from .. import shorty


@pytest.fixture(scope='module')
def app():
    yield shorty.app.test_client()


def test_example(client):
    response = client.get("/_help")
    assert response.status_code == 200
