import asyncio
import subprocess
import yfinance as yf
from ib_insync import IB, Stock, util
from ai_agent import LlamaTradingAgent
from analyst import get_technical_context
from broker import place_market_order
from risk_manager import check_trade_viability

util.patchAsyncio()


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
        current_price = await fetch_price(target_symbol)

        if current_price <= 0:
            print("⚠️  Invalid price received.")
            return

        print(f"📈 {target_symbol} current price is: ${current_price}")
        real_context = await get_technical_context(target_symbol)
        decision = agent.analyze_market(target_symbol, current_price, real_context)

        print(f"Action: {decision['decision']} | Confidence: {decision['confidence']}% | Reasoning: {decision['reasoning']}")

        if decision["decision"] == "BUY" and decision["confidence"] > 70:
            risk_assessment = await check_trade_viability(ib, target_symbol, "BUY", current_price, 1)
            print(f"Risk assessment: {risk_assessment['reason']}")

            if not risk_assessment["approved"]:
                print("❌ Trade blocked by risk manager.")
                return

            order_contract = Stock(target_symbol, "SMART", "USD")
            await ib.qualifyContractsAsync(order_contract)
            await place_market_order(ib, order_contract, "BUY", risk_assessment["quantity"])
            await asyncio.sleep(1)

    except Exception as e:
        print(f"⚠️  Cycle error: {e}")


async def main():
    print("🤖 --- STARTING TRADING BOT (DAEMON MODE) ---")

    ib = IB()
    windows_ip = get_wsl_host_ip()
    agent = LlamaTradingAgent()
    target_symbol = "META"

    try:
        print(f"⏳ Connecting to IBKR at {windows_ip}...")
        await ib.connectAsync(host=windows_ip, port=7497, clientId=77, timeout=15)
        print("✅ Connected to IBKR!")

        while True:
            await execute_trading_cycle(ib, agent, target_symbol)
            print("💤 Sleeping for 5 minutes...")
            await asyncio.sleep(300)

    finally:
        if ib.isConnected():
            ib.disconnect()
            print("🔌 Session closed.")

if __name__ == "__main__":
    try:
        util.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Process stopped manually.")