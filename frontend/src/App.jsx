import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [botStatus, setBotStatus] = useState(false)
  const [ibConnected, setIbConnected] = useState(false)
  const [ledger, setLedger] = useState({})
  const [logs, setLogs] = useState([])

  const fetchData = async () => {
    try {
      const [statusResponse, ledgerResponse, logsResponse] = await Promise.all([
        axios.get('/api/status'),
        axios.get('/api/ledger'),
        axios.get('/api/logs'),
      ])

      setBotStatus(Boolean(statusResponse.data?.running))
      setIbConnected(Boolean(statusResponse.data?.ib_connected))
      setLedger(ledgerResponse.data ?? {})
      setLogs(Array.isArray(logsResponse.data) ? logsResponse.data : [])
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    }
  }

  useEffect(() => {
    fetchData()

    const intervalId = setInterval(() => {
      fetchData()
    }, 3000)

    return () => {
      clearInterval(intervalId)
    }
  }, [])

  const startBot = async () => {
    try {
      await axios.post('/api/start')
      await fetchData()
    } catch (error) {
      console.error('Failed to start bot:', error)
    }
  }

  const stopBot = async () => {
    try {
      await axios.post('/api/stop')
      await fetchData()
    } catch (error) {
      console.error('Failed to stop bot:', error)
    }
  }

  const dotColorClass = botStatus ? 'bg-green-500' : 'bg-red-500'
  const statusText = botStatus ? 'Running' : 'Offline'

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">LlamaTrader Control Center</h1>
          <div className="flex flex-wrap items-center gap-3 text-sm text-gray-300">
            <div className="flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${dotColorClass}`}
                aria-hidden="true"
              ></span>
              <span>{statusText}</span>
            </div>
            <span
              className={`rounded-full border px-2 py-0.5 ${
                ibConnected
                  ? 'border-green-500/40 bg-green-500/10 text-green-300'
                  : 'border-red-500/40 bg-red-500/10 text-red-300'
              }`}
            >
              IB: {ibConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-6 p-6 lg:grid-cols-3">
        <div className="rounded-xl border border-gray-800 bg-gray-800/40 p-6 lg:col-span-2">
          <h2 className="mb-4 text-lg font-medium text-gray-100">Log Feed</h2>
          <div className="h-96 overflow-y-auto rounded-lg border border-gray-800 bg-gray-950/60 p-4">
            {logs.length > 0 ? (
              logs.map((line, index) => (
                <p
                  key={`${index}-${line}`}
                  className="mb-2 border-b border-gray-800/60 pb-2 font-mono text-sm text-gray-300 last:mb-0 last:border-b-0 last:pb-0"
                >
                  {line}
                </p>
              ))
            ) : (
              <p className="text-sm text-gray-500">No logs available.</p>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-800/40 p-6">
          <h2 className="mb-4 text-lg font-medium text-gray-100">Control Panel</h2>

          <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={startBot}
              className="rounded-lg bg-green-600 px-4 py-3 text-base font-semibold text-white transition hover:bg-green-500"
            >
              START BOT
            </button>
            <button
              type="button"
              onClick={stopBot}
              className="rounded-lg bg-red-600 px-4 py-3 text-base font-semibold text-white transition hover:bg-red-500"
            >
              STOP BOT
            </button>
          </div>

          <section className="rounded-lg border border-gray-800 bg-gray-950/60 p-4">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-300">Ledger</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex items-center justify-between gap-3 border-b border-gray-800/70 pb-2">
                <dt className="text-gray-400">Virtual Cash</dt>
                <dd className="font-medium text-gray-100">{ledger.virtual_cash ?? 'N/A'}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-gray-800/70 pb-2">
                <dt className="text-gray-400">Unrealized PnL</dt>
                <dd className="font-medium text-gray-100">{ledger.unrealized_pnl ?? 'N/A'}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-gray-800/70 pb-2">
                <dt className="text-gray-400">Realized PnL</dt>
                <dd className="font-medium text-gray-100">{ledger.realized_pnl ?? 'N/A'}</dd>
              </div>
              <div className="flex items-center justify-between gap-3 border-b border-gray-800/70 pb-2">
                <dt className="text-gray-400">Position Shares</dt>
                <dd className="font-medium text-gray-100">{ledger.position_shares ?? 'N/A'}</dd>
              </div>
              <div className="flex items-center justify-between gap-3">
                <dt className="text-gray-400">Total Commissions</dt>
                <dd className="font-medium text-gray-100">{ledger.total_commissions_paid ?? 'N/A'}</dd>
              </div>
            </dl>
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
