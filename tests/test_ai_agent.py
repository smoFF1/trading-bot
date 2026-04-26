import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

os.environ["GROQ_API_KEY"] = "test_dummy_key"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai_agent import LlamaTradingAgent


def test_extract_json_text_strips_code_fences():
    raw_response = "```json\n{\"decision\": \"BUY\"}\n```"

    assert LlamaTradingAgent._extract_json_text(raw_response) == '{"decision": "BUY"}'


def test_extract_json_text_returns_plain_text_unchanged():
    raw_response = '{"decision": "HOLD"}'

    assert LlamaTradingAgent._extract_json_text(raw_response) == raw_response


def test_validate_decision_data_accepts_valid_payload():
    data = {
        "decision": "SELL",
        "confidence": 82,
        "reasoning": "Momentum weakened after a strong run."
    }

    assert LlamaTradingAgent._validate_decision_data(data) == data


@pytest.mark.parametrize(
    "payload, expected_message",
    [
        ([], "Model response is not a JSON object"),
        ({"decision": "WAIT", "confidence": 50, "reasoning": "Invalid decision"}, "Invalid or missing decision value"),
        ({"decision": "BUY", "confidence": 101, "reasoning": "Too high"}, "Invalid or missing confidence value"),
        ({"decision": "BUY", "confidence": 50, "reasoning": "   "}, "Invalid or missing reasoning value"),
    ],
)
def test_validate_decision_data_rejects_invalid_payloads(payload, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        LlamaTradingAgent._validate_decision_data(payload)


def test_llama_trading_agent_raises_when_api_key_is_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GROQ_API_KEY is missing in .env file"):
        LlamaTradingAgent()


def test_analyze_market_returns_validated_decision_from_successful_api_response():
    agent = LlamaTradingAgent()
    agent.client = Mock()
    agent.client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content='{"decision": "BUY", "confidence": 87, "reasoning": "Strong setup"}'))]
    )

    result = agent.analyze_market("AAPL", 100.0, "Bullish context")

    assert result == {
        "decision": "BUY",
        "confidence": 87,
        "reasoning": "Strong setup",
    }


def test_analyze_market_returns_error_dict_when_api_call_fails():
    agent = LlamaTradingAgent()
    agent.client = Mock()
    agent.client.chat.completions.create.side_effect = Exception("boom")

    result = agent.analyze_market("AAPL", 100.0, "Bullish context")

    assert result["decision"] == "ERROR"
    assert result["confidence"] == 0
    assert "boom" in result["reasoning"]