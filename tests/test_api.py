import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, mock_open, patch

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
        main.ledger.virtual_cash = 0.0
        main.ledger.unrealized_pnl = 0.0
        main.ledger.realized_pnl = 0.0
        main.ledger.total_commissions_paid = 0.0
        main.ledger._position_shares = 0
        main.ledger._position_cost = 0.0
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
    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json() == {"running": False, "ib_connected": False}


def test_start_starts_once_and_rejects_second_start(client):
    def _mock_create_task(coro):
        coro.close()
        return Mock()

    with patch("src.main.asyncio.create_task", side_effect=_mock_create_task) as mock_create_task:
        first_response = client.post("/api/start")
        second_response = client.post("/api/start")

    assert first_response.status_code == 200
    assert first_response.json() == {"message": "Trading bot started"}
    assert second_response.status_code == 200
    assert second_response.json() == {"message": "Trading bot is already running"}
    mock_create_task.assert_called_once()


def test_stop_stops_running_bot(client):
    main.bot_running = True
    main.bot_task = Mock()

    response = client.post("/api/stop")

    assert response.status_code == 200
    assert response.json() == {"message": "Trading bot stopped"}
    assert main.bot_running is False
    main.bot_task.cancel.assert_called_once()


def test_ledger_returns_initial_state(client):
    response = client.get("/api/ledger")

    assert response.status_code == 200
    assert response.json() == {
        "virtual_cash": 0.0,
        "unrealized_pnl": 0.0,
        "realized_pnl": 0.0,
        "total_commissions_paid": 0.0,
        "position_shares": 0,
        "position_cost": 0.0,
    }


def test_portfolio_returns_summary_from_account_values(client):
    account_values = [
        Mock(tag="NetLiquidation", value="100000"),
        Mock(tag="AvailableFunds", value="40000"),
        Mock(tag="UnrealizedPnL", value="1200.5"),
        Mock(tag="RealizedPnL", value="-50.25"),
    ]

    with patch.object(main.ib, "accountValues", return_value=account_values):
        response = client.get("/api/portfolio")

    assert response.status_code == 200
    assert response.json() == {
        "NetLiquidation": 100000.0,
        "AvailableFunds": 40000.0,
        "UnrealizedPnL": 1200.5,
        "RealizedPnL": -50.25,
    }


def test_logs_returns_last_50_lines(client):
    all_lines = [f"line {index}\n" for index in range(1, 61)]

    with patch("builtins.open", mock_open(read_data="".join(all_lines))):
        response = client.get("/api/logs")

    assert response.status_code == 200
    assert response.json() == [f"line {index}" for index in range(11, 61)]