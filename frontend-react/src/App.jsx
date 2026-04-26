import React, { useState, useEffect } from 'react'
import DateSelection from './components/DateSelection'
import ReplayView from './components/ReplayView'
import './App.css'

const API_URL = 'http://127.0.0.1:8000'

function App() {
  const [view, setView] = useState('selection') // 'selection' or 'replay'
  const [sessionId, setSessionId] = useState(null)
  const [marketData, setMarketData] = useState([])

  useEffect(() => {
    // Fetch market history on mount
    fetch(`${API_URL}/market/history`)
      .then(res => res.json())
      .then(data => setMarketData(data))
      .catch(err => console.error('Failed to fetch market data:', err))
  }, [])

  const handleStartReplay = (startDate, sessionId) => {
    setSessionId(sessionId)
    setView('replay')
  }

  const handleExitReplay = () => {
    setSessionId(null)
    setView('selection')
  }

  return (
    <div className="app">
      {view === 'selection' ? (
        <DateSelection 
          marketData={marketData}
          onStartReplay={handleStartReplay}
          API_URL={API_URL}
        />
      ) : (
        <ReplayView 
          sessionId={sessionId}
          onExit={handleExitReplay}
          API_URL={API_URL}
        />
      )}
    </div>
  )
}

export default App
