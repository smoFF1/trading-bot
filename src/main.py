import asyncio
import logging
import subprocess
from logging.handlers import RotatingFileHandler
import yfinance as yf
from ib_insync import IB, Stock, util
from ai_agent import LlamaTradingAgent
from analyst import get_technical_context
from broker import place_market_order
from portfolio import get_portfolio_summary
from risk_manager import check_trade_viability

util.patchAsyncio()


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


async def execute_trading_cycle(ib: IB, agent: LlamaTradingAgent, target_symbol: str) -> None:
    try:
        portfolio = await get_portfolio_summary(ib)
        logging.info(
            "Portfolio Status -> Net: $%.2f, Cash: $%.2f, Unrealized PnL: $%.2f, Realized PnL: $%.2f",
            portfolio["NetLiquidation"],
            portfolio["AvailableFunds"],
            portfolio["UnrealizedPnL"],
            portfolio["RealizedPnL"],
        )

        current_price = await fetch_price(target_symbol)

        if current_price <= 0:
            logging.warning("Invalid price received.")
            return

        logging.info("%s current price is: $%s", target_symbol, current_price)
        real_context = await get_technical_context(target_symbol)
        decision = agent.analyze_market(target_symbol, current_price, real_context)

        logging.info(
            "Action: %s | Confidence: %s%% | Reasoning: %s",
            decision["decision"],
            decision["confidence"],
            decision["reasoning"],
        )

        if decision["decision"] == "BUY" and decision["confidence"] > 70:
            risk_assessment = await check_trade_viability(ib, target_symbol, "BUY", current_price, 1)
            logging.info("Risk assessment: %s", risk_assessment["reason"])

            if not risk_assessment["approved"]:
                logging.warning("Trade blocked by risk manager.")
                return

            order_contract = Stock(target_symbol, "SMART", "USD")
            await ib.qualifyContractsAsync(order_contract)
            await place_market_order(ib, order_contract, "BUY", risk_assessment["quantity"])
            await asyncio.sleep(1)

    except Exception:
        logging.exception("Cycle error")


async def main():
    logging.info("--- STARTING TRADING BOT (DAEMON MODE) ---")

    ib = IB()
    windows_ip = get_wsl_host_ip()
    agent = LlamaTradingAgent()
    target_symbol = "META"

    try:
        logging.info("Connecting to IBKR at %s...", windows_ip)
        await ib.connectAsync(host=windows_ip, port=7497, clientId=77, timeout=15)
        logging.info("Connected to IBKR.")

        while True:
            await execute_trading_cycle(ib, agent, target_symbol)
            logging.info("Sleeping for 5 minutes...")
            await asyncio.sleep(300)

    finally:
        if ib.isConnected():
            ib.disconnect()
            logging.info("Session closed.")

if __name__ == "__main__":
    try:
        configure_logging()
        util.run(main())
    except KeyboardInterrupt:
        logging.info("Process stopped manually.")