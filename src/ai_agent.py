import os
import json
import logging
from typing import Any
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class LlamaTradingAgent:
    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is missing in .env file")

        self.client = Groq(api_key=api_key)

        self.model_name = "llama-3.3-70b-versatile"

        self.system_prompt = """
        You are an expert algorithmic trading AI. Your goal is to analyze market data for a given stock and make a strict trading decision.
        You must evaluate BOTH technical indicators and recent news sentiment from the provided context.
        Decision guidance:
        - If news is overwhelmingly positive but RSI/technicals indicate overbought conditions, prefer "CAUTIOUS HOLD" or "BUY" with lower confidence.
        - If news is negative and technicals are bearish, increase confidence for a "SELL" decision.
        You must output ONLY a valid JSON object with the following structure:
        {
            "decision": "BUY" | "SELL" | "HOLD" | "CAUTIOUS HOLD",
            "confidence": 0-100,
            "reasoning": "A short explanation of why you made this decision."
        }
        Do not wrap the output in markdown code blocks. Just return the raw JSON.
        """

    @staticmethod
    def _extract_json_text(raw_text: str) -> str:
        text = raw_text.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        return text

    @staticmethod
    def _validate_decision_data(data: Any) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Model response is not a JSON object")

        decision = data.get("decision")
        confidence = data.get("confidence")
        reasoning = data.get("reasoning")

        if decision not in {"BUY", "SELL", "HOLD", "CAUTIOUS HOLD"}:
            raise ValueError("Invalid or missing decision value")

        if not isinstance(confidence, int) or not 0 <= confidence <= 100:
            raise ValueError("Invalid or missing confidence value")

        if not isinstance(reasoning, str) or not reasoning.strip():
            raise ValueError("Invalid or missing reasoning value")

        return data

    def analyze_market(self, ticker: str, current_price: float, market_context: str) -> dict:
        prompt = f"""
        --- MARKET DATA ---
        Ticker: {ticker}
        Current Price: ${current_price}
        Context / Recent Action: {market_context}

        Analyze this data and return the JSON decision.
        """

        try:
            logging.info("Asking Llama3 (via Groq) to analyze %s...", ticker)
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                model=self.model_name,    
                response_format={"type": "json_object"},
            )

            raw_text = chat_completion.choices[0].message.content or ""
            raw_text = self._extract_json_text(raw_text)
            decision_data = json.loads(raw_text)
            return self._validate_decision_data(decision_data)

        except Exception as e:
            logging.exception("Error communicating with Groq")
            return {
                "decision": "ERROR",
                "confidence": 0,
                "reasoning": str(e),
            }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = LlamaTradingAgent()
    fake_ticker = "META"
    fake_price = 626.87
    fake_context = (
        "The stock has dropped slightly today but overall tech sector is showing strong momentum. "
        "The RSI is around 45, indicating it is neither overbought nor oversold."
    )

    result = agent.analyze_market(fake_ticker, fake_price, fake_context)

    logging.info("--- LLAMA DECISION ---")
    logging.info(json.dumps(result, indent=4))