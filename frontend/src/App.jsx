import { useEffect, useState } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [status, setStatus] = useState(false)
  const [ibConnected, setIbConnected] = useState(false)
  const [ledger, setLedger] = useState({})
  const [logs, setLogs] = useState([])

  const updateDashboard = async () => {
    try {
      const statusResponse = await axios.get('/api/status')
      setStatus(Boolean(statusResponse.data?.running))
      setIbConnected(Boolean(statusResponse.data?.ib_connected))

      const ledgerResponse = await axios.get('/api/ledger')
      setLedger(ledgerResponse.data ?? {})

      const logsResponse = await axios.get('/api/logs')
      setLogs(Array.isArray(logsResponse.data) ? logsResponse.data : [])
    } catch {
    }
  }

  useEffect(() => {
    updateDashboard()

    const intervalId = setInterval(() => {
      updateDashboard()
    }, 3000)

    return () => {
      clearInterval(intervalId)
    }
  }, [])

  const handleStart = async () => {
    try {
      await axios.post('/api/start')
      await updateDashboard()
    } catch (error) {
      console.error('Failed to start bot:', error)
    }
  }

  const handleStop = async () => {
    try {
      await axios.post('/api/stop')
      await updateDashboard()
    } catch (error) {
      console.error('Failed to stop bot:', error)
    }
  }

  const dotColorClass = status ? 'bg-green-500' : 'bg-red-500'
  const statusText = status ? 'Running' : 'Offline'

  const getPnLColor = (value) => {
    const numValue = Number(value)
    if (isNaN(numValue) || Math.abs(numValue) < 0.005) return 'text-gray-100'
    return numValue > 0 ? 'text-green-400' : 'text-red-400'
  }

  const formatPnL = (value) => {
    const numValue = Number(value)
    if (isNaN(numValue) || Math.abs(numValue) < 0.005) return '$0.00'
    return `${numValue > 0 ? '+' : ''}$${numValue.toFixed(2)}`
  }

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
              onClick={handleStart}
              className="rounded-lg bg-green-600 px-4 py-3 text-base font-semibold text-white transition hover:bg-green-500"
            >
              START BOT
            </button>
            <button
              type="button"
              onClick={handleStop}
              className="rounded-lg bg-red-600 px-4 py-3 text-base font-semibold text-white transition hover:bg-red-500"
            >
              STOP BOT
            </button>
          </div>

          <section className="rounded-lg border border-gray-800 bg-gray-950/60 p-4">
            <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-300">Shadow Ledger</h3>
            <ul className="space-y-3">
              <li className="flex justify-between"><span className="text-gray-400">Cash:</span> <span>${ledger.virtual_cash?.toFixed(2) || '0.00'}</span></li>

              <li className="flex justify-between">
                <span className="text-gray-400">Unrealized PnL:</span>
                <span className={getPnLColor(ledger.unrealized_pnl)}>
                  {formatPnL(ledger.unrealized_pnl)}
                  {ledger.position_cost > 0 && ledger.unrealized_pnl !== undefined &&
                    ` (${((ledger.unrealized_pnl / ledger.position_cost) * 100).toFixed(2)}%)`}
                </span>
              </li>

              <li className="flex justify-between">
                <span className="text-gray-400">Realized PnL:</span>
                <span className={getPnLColor(ledger.realized_pnl)}>
                  {formatPnL(ledger.realized_pnl)}
                </span>
              </li>

              <li className="flex justify-between"><span className="text-gray-400">Commissions:</span> <span className="text-red-400">${ledger.total_commissions_paid?.toFixed(2) || '0.00'}</span></li>
              <li className="flex justify-between"><span className="text-gray-400">Shares:</span> <span>{ledger.position_shares || 0}</span></li>
            </ul>
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
