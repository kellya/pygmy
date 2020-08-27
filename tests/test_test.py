import pytest
import sys
sys.path.append('./')
sys.path.append('../')
import shorty


@pytest.fixture(scope='module')
def app():
    yield app


def test_example(client):
    response = client.get("/_help")
    assert response.status_code == 200
