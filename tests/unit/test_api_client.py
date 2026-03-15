import pytest
import requests

from src.api_client import ApiClient


@pytest.fixture
def api_client():
    client = ApiClient(base_url="https://fake-api.com")
    return client


@pytest.fixture
def mock_session(mocker):
    mock_response = mocker.Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"some_item": "some_value"}

    mock_session = mocker.Mock()
    mock_session.__enter__ = mocker.Mock(return_value=mock_session)
    mock_session.__exit__ = mocker.Mock(return_value=False)

    mocker.patch("src.api_client.requests.Session", return_value=mock_session)
    return mock_session, mock_response


def test_api_client_creation(api_client):
    assert isinstance(api_client, ApiClient)
    assert api_client.base_url == "https://fake-api.com"


@pytest.mark.parametrize("base_url, headers", [
    ("https://fake-api.com", {"Some_item": "some_value"}),
    ("https://fake-api.com", None),
])
def test_api_client_headers(base_url, headers):
    client = ApiClient(base_url, headers)
    assert client.headers["Accept"] == "application/json"


def test_get_json(mock_session, api_client):
    session, response = mock_session
    session.get.return_value = response

    assert api_client.get_json() == {"some_item": "some_value"}


@pytest.mark.parametrize("exc", [
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
])
def test_get_json_exceptions(mock_session, api_client, mocker, exc, caplog):
    mocker.patch("src.api_client.time.sleep")

    session, response = mock_session
    session.get.side_effect = exc

    with pytest.raises(exc):
        with caplog.at_level("WARNING"):
            api_client.get_json()

    assert session.get.call_count == 3
    assert "Ошибка сети (попытка 1/3)" in caplog.text
    assert "Ошибка сети (попытка 2/3)" in caplog.text
