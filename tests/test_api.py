import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import src.main as main


_httpx_client_init = httpx.Client.__init__


def _patched_httpx_client_init(self, *args, app=None, **kwargs):
    return _httpx_client_init(self, *args, **kwargs)


@pytest.fixture(autouse=True)
def reset_main_state():
    with patch.object(main.ib, "isConnected", return_value=False), patch.object(
        main,
        "connect_ibkr",
        new=AsyncMock(return_value=None),
    ):
        main.bot_running = False
        main.bot_task = None
        yield
        main.bot_running = False
        main.bot_task = None


@pytest.fixture
def client(reset_main_state):
    with patch.object(httpx.Client, "__init__", new=_patched_httpx_client_init):
        with TestClient(main.app) as test_client:
            yield test_client


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_status_returns_running_and_ib_connection_state(client):
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json() == {"running": False, "ib_connected": False}


def test_start_starts_once_and_rejects_second_start(client):
    def _mock_create_task(coro):
        coro.close()
        return Mock()

    with patch("src.main.asyncio.create_task", side_effect=_mock_create_task) as mock_create_task:
        first_response = client.post("/start")
        second_response = client.post("/start")

    assert first_response.status_code == 200
    assert first_response.json() == {"message": "Trading bot started"}
    assert second_response.status_code == 200
    assert second_response.json() == {"message": "Trading bot is already running"}
    mock_create_task.assert_called_once()


def test_stop_stops_running_bot(client):
    main.bot_running = True
    main.bot_task = Mock()

    response = client.post("/stop")

    assert response.status_code == 200
    assert response.json() == {"message": "Trading bot stopped"}
    assert main.bot_running is False
    main.bot_task.cancel.assert_called_once()