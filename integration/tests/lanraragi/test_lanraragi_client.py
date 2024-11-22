import asyncio
import pytest

from catapult.lanraragi.client import LRRClient

@pytest.fixture()
def lrr_client():
    yield LRRClient('http://localhost:3000', lrr_api_key='lanraragi')

def test_get_shinobu_status(lrr_client: LRRClient):
    response = asyncio.run(lrr_client.get_shinobu_status())
    assert response.status_code == 200
    assert response.operation == 'shinobu_status'

def test_get_server_info(lrr_client: LRRClient):
    response = asyncio.run(lrr_client.get_server_info())
    assert response.status_code == 200
