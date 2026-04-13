import asyncio
import subprocess
import yfinance as yf
from ib_insync import IB, Stock, util
from ai_agent import LlamaTradingAgent
from broker import place_market_order

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


async def main():
    print("🤖 --- STARTING TRADING BOT ---")

    ib = IB()
    windows_ip = get_wsl_host_ip()
    agent = LlamaTradingAgent()
    target_symbol = "META"

    try:
        print(f"⏳ Connecting to IBKR at {windows_ip}...")
        await ib.connectAsync(host=windows_ip, port=7497, clientId=77, timeout=15)
        print("✅ Connected to IBKR!")

        current_price = await fetch_price(target_symbol)

        if current_price > 0:
            print(f"📈 {target_symbol} current price is: ${current_price}")
            context = "The market is experiencing high volatility. Tech stocks are generally strong today."
            decision = agent.analyze_market(target_symbol, current_price, context)

            print("\n🎯 --- FINAL DECISION ---")
            print(f"Action: {decision['decision']}")
            print(f"Confidence: {decision['confidence']}%")
            print(f"Reasoning: {decision['reasoning']}")

            if decision["decision"] == "BUY" and decision["confidence"] > 70:
                order_contract = Stock(target_symbol, "SMART", "USD")
                await ib.qualifyContractsAsync(order_contract)
                await place_market_order(ib, order_contract, "BUY", 1)
                await asyncio.sleep(1)

        else:
            print("❌ Stopping logic because valid price was not found.")

    except Exception as e:
        print(f"❌ System Error: {e}")
    finally:
        if ib.isConnected():
            ib.disconnect()
            print("🔌 Session closed.")

if __name__ == "__main__":
    try:
        util.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Process stopped manually.")