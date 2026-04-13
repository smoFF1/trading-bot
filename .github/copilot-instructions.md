# Project Guidelines

## Code Style
Follow PEP 8 for Python code. Use type hints where beneficial. Prefer async/await patterns for concurrency (ib_insync is async-native).

## Architecture
- **Async-first design**: All trading operations use asyncio for real-time market data and order execution
- **Component separation**: Broker (IB), AI (Gemini), Trading logic kept in separate modules
- **Event-driven**: Use message queues/events for order state management
- **Configuration**: Environment variables for secrets, config.py for settings

## Build and Test
```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Run tests
pytest tests/

# Start bot
python src/main.py
```

## Conventions
- **Security**: Never commit `.env` file. Use `.env.example` as template
- **Testing**: Mock IB Gateway and Gemini API for unit tests
- **Error handling**: Implement circuit breakers and reconnection logic
- **Logging**: Comprehensive logging for all trading operations
- **Paper trading first**: Always test with paper account before live trading

## Pitfalls to Avoid
- IB Gateway disconnections: Implement automatic reconnection with exponential backoff
- Gemini API rate limits: Batch requests and add retry logic
- Async errors: Ensure proper exception handling in coroutines
- Market hours validation: Check trading hours before order execution</content>
<parameter name="filePath">/home/roi/projects/algo-trading-bot/.github/copilot-instructions.md