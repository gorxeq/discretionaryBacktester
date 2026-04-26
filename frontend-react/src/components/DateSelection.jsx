import React, { useState } from 'react'
import axios from 'axios'
import './DateSelection.css'

function DateSelection({ marketData, onStartReplay, API_URL }) {
  const [selectedDate, setSelectedDate] = useState('')
  const [loading, setLoading] = useState(false)

  const uniqueDates = marketData.length > 0 
    ? [...new Set(marketData.map(d => d.date))].sort()
    : []

  const handleStart = async () => {
    if (!selectedDate) {
      alert('Please select a date')
      return
    }

    setLoading(true)
    try {
      const response = await axios.post(`${API_URL}/session/start`, {
        start_date: selectedDate
      })
      
      if (response.data.session_id) {
        onStartReplay(selectedDate, response.data.session_id)
      }
    } catch (error) {
      console.error('Failed to start session:', error)
      alert('Failed to start replay session. Make sure backend is running.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="date-selection">
      <div className="container">
        <h1>Nifty 50 - Strategy Simulator</h1>
        <div className="selection-panel">
          <h2>Select Start Date</h2>
          <select 
            value={selectedDate} 
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-select"
          >
            <option value="">Choose a date...</option>
            {uniqueDates.map(date => (
              <option key={date} value={date}>{date}</option>
            ))}
          </select>
          <button 
            onClick={handleStart} 
            disabled={!selectedDate || loading}
            className="start-button"
          >
            {loading ? 'Starting...' : '🚀 Start Bar Replay'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default DateSelection
