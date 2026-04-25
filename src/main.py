import asyncio
import logging
import os
import subprocess
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
import yfinance as yf
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
import uvicorn
from ib_insync import IB, Stock, util
from ai_agent import LlamaTradingAgent
from analyst import get_technical_context
from broker import place_market_order
from news_fetcher import get_recent_news
from portfolio import get_portfolio_summary
from risk_manager import check_trade_viability
from shadow_ledger import ShadowLedger

util.patchAsyncio()

ib = IB()
agent = LlamaTradingAgent()
ledger = ShadowLedger()
bot_task = None
bot_running = False


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=5),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("ib_insync").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_wsl_host_ip():
    try:
        cmd = "ip route list default | awk '{print $3}'"
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except Exception:
        return "127.0.0.1"

async def fetch_price(symbol: str) -> float:
    ticker = yf.Ticker(symbol)
    return float(await asyncio.to_thread(lambda: ticker.fast_info["lastPrice"]))


async def execute_trading_cycle(
    ib: IB,
    agent: LlamaTradingAgent,
    target_symbol: str,
    ledger: ShadowLedger,
) -> None:
    try:
        portfolio = await get_portfolio_summary(ib)
        if (
            ledger.virtual_cash == 0.0
            and ledger.unrealized_pnl == 0.0
            and ledger.realized_pnl == 0.0
            and ledger.total_commissions_paid == 0.0
        ):
            ledger.virtual_cash = float(portfolio["AvailableFunds"])
            try:
                positions = await ib.reqPositionsAsync()
                for pos in positions:
                    if pos.contract.symbol == target_symbol and pos.position > 0:
                        ledger._position_shares = int(pos.position)
                        try:
                            avg_cost = float(pos.avgCost)
                        except (TypeError, ValueError, AttributeError):
                            avg_cost = 0.0
                        ledger._position_cost = float(pos.position * avg_cost)
            except Exception:
                logging.exception("Failed to sync initial positions to shadow ledger.")

        logging.info(
            (
                "Portfolio Status -> Net: $%.2f, Cash: $%.2f, Unrealized PnL: $%.2f, Realized PnL: $%.2f | "
                "Shadow Ledger -> Cash: $%.2f, Unrealized PnL: $%.2f, Realized PnL: $%.2f, Commissions: $%.2f"
            ),
            portfolio["NetLiquidation"],
            portfolio["AvailableFunds"],
            portfolio["UnrealizedPnL"],
            portfolio["RealizedPnL"],
            ledger.virtual_cash,
            ledger.unrealized_pnl,
            ledger.realized_pnl,
            ledger.total_commissions_paid,
        )

        current_price = await fetch_price(target_symbol)

        if current_price <= 0:
            logging.warning("Invalid price received.")
            return

        logging.info("%s current price is: $%s", target_symbol, current_price)
        real_context = await get_technical_context(target_symbol)
        news_context = await get_recent_news(target_symbol, limit=3)
        combined_context = f"TECHNICALS: {real_context} | RECENT NEWS: {news_context}"
        decision = agent.analyze_market(target_symbol, current_price, combined_context)

        logging.info(
            "Action: %s | Confidence: %s%% | Reasoning: %s",
            decision["decision"],
            decision["confidence"],
            decision["reasoning"],
        )

        if decision["decision"] == "BUY" and decision["confidence"] > 70:
            order_contract = Stock(target_symbol, "SMART", "USD")
            await ib.qualifyContractsAsync(order_contract)

            risk_assessment = await check_trade_viability(ib, order_contract, "BUY", current_price, 1)
            logging.info("Risk assessment: %s", risk_assessment["reason"])

            if not risk_assessment["approved"]:
                logging.warning("Trade blocked by risk manager.")
                return

            await place_market_order(ib, order_contract, "BUY", risk_assessment["quantity"])
            await asyncio.sleep(1)
            try:
                ledger.record_trade("BUY", risk_assessment["quantity"], current_price)
            except Exception:
                logging.exception("Shadow ledger failed to record executed trade.")
        elif decision["decision"] == "SELL" and decision["confidence"] > 70:
            order_contract = Stock(target_symbol, "SMART", "USD")
            await ib.qualifyContractsAsync(order_contract)

            risk_assessment = await check_trade_viability(ib, order_contract, "SELL", current_price, 1)
            logging.info("Risk assessment: %s", risk_assessment["reason"])

            if not risk_assessment["approved"]:
                logging.warning("Trade blocked by risk manager.")
                return

            await place_market_order(ib, order_contract, "SELL", risk_assessment["quantity"])
            await asyncio.sleep(1)
            try:
                ledger.record_trade("SELL", risk_assessment["quantity"], current_price)
            except Exception:
                logging.exception("Shadow ledger failed to record executed trade.")

    except Exception:
        logging.exception("Cycle error")


async def connect_ibkr():
    host = os.getenv("IBKR_HOST") or get_wsl_host_ip()
    port = int(os.getenv("IBKR_PORT", 7497))
    while True:
        try:
            logging.info("Connecting to IBKR at %s:%s...", host, port)
            await ib.connectAsync(host=host, port=port, clientId=77, timeout=10)
            logging.info("Connected to IBKR.")
            break
        except (asyncio.exceptions.TimeoutError, ConnectionRefusedError):
            logging.warning("IBKR is not ready yet. Retrying in 5 seconds...")
            await asyncio.sleep(5)

async def trading_loop():
    global bot_running
    target_symbol = "META"
    while bot_running:
        if not ib.isConnected():
            logging.warning("API is running, but IBKR is not connected yet. Waiting 10 seconds...")
            await asyncio.sleep(10)
            continue
        await execute_trading_cycle(ib, agent, target_symbol, ledger)
        logging.info("Sleeping for 5 minutes...")
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("--- STARTING TRADING BOT API ---")
    asyncio.create_task(connect_ibkr())
    yield
    global bot_running, bot_task
    bot_running = False
    if bot_task:
        bot_task.cancel()
    if ib.isConnected():
        ib.disconnect()
        logging.info("Session closed.")

app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")

@app.get("/status")
async def get_status():
    return {"running": bot_running, "ib_connected": ib.isConnected() if ib else False}

@app.post("/start")
async def start_bot():
    global bot_running, bot_task
    if not bot_running:
        bot_running = True
        bot_task = asyncio.create_task(trading_loop())
        return {"message": "Trading bot started"}
    return {"message": "Trading bot is already running"}

@app.post("/stop")
async def stop_bot():
    global bot_running, bot_task
    bot_running = False
    if bot_task:
        bot_task.cancel()
    return {"message": "Trading bot stopped"}

if __name__ == "__main__":
    try:
        configure_logging()
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except KeyboardInterrupt:
        logging.info("Process stopped manually.")