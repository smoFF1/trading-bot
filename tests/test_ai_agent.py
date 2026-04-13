import os
import sys
from pathlib import Path

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