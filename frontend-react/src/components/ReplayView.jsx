import React, { useState, useEffect, useRef } from 'react'
import { createChart, ColorType } from 'lightweight-charts'
import axios from 'axios'
import StrategyPanel from './StrategyPanel'
import './ReplayView.css'

function ReplayView({ sessionId, onExit, API_URL }) {
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  
  const [replayState, setReplayState] = useState('INIT')
  const [visibleCandles, setVisibleCandles] = useState([])
  const [currentDate, setCurrentDate] = useState('')
  const [totalPnL, setTotalPnL] = useState(0)
  const [dailyPnL, setDailyPnL] = useState(0)
  const [activeStrategy, setActiveStrategy] = useState(null)
  const [loading, setLoading] = useState(false)

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0c0d10' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1e222d' },
        horzLines: { color: '#1e222d' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 600,
      handleScale: {
        axisPressedMouseMove: false,
        axisDoubleClickReset: false,
      },
      handleScroll: {
        horzTouchDrag: false,
        vertTouchDrag: false,
      },
    })

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#089981',
      downColor: '#f23645',
      borderVisible: false,
      wickUpColor: '#089981',
      wickDownColor: '#f23645',
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries

    return () => {
      chart.remove()
    }
  }, [])

  // Update chart when candles change
  useEffect(() => {
    if (!seriesRef.current || visibleCandles.length === 0) return

    const chartData = visibleCandles.map(candle => ({
      time: candle.time,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }))

    seriesRef.current.setData(chartData)
    
    if (chartRef.current) {
      chartRef.current.timeScale().fitContent()
    }
  }, [visibleCandles])

  // Load initial session state
  useEffect(() => {
    if (!sessionId) return

    const loadSession = async () => {
      try {
        // Get session state - we'll need to call next to initialize
        await handleNext()
      } catch (error) {
        console.error('Failed to load session:', error)
      }
    }

    loadSession()
  }, [sessionId])

  const handleNext = async () => {
    if (loading) return
    setLoading(true)

    try {
      const response = await axios.post(`${API_URL}/session/next`, {
        session_id: sessionId
      })

      const data = response.data
      setReplayState(data.state)
      
      if (data.spot_candle) {
        const candle = data.spot_candle
        const candleData = {
          time: candle.date,
          open: candle.open,
          high: candle.high,
          low: candle.low,
          close: candle.close,
        }

        setCurrentDate(candle.date)
        
        // Update visible candles
        setVisibleCandles(prev => {
          const lastCandle = prev[prev.length - 1]
          if (lastCandle && lastCandle.time === candle.date) {
            // Update existing candle
            return [...prev.slice(0, -1), candleData]
          } else {
            // Add new candle
            return [...prev, candleData]
          }
        })

        // Update PnL
        if (data.total_pnl !== undefined) setTotalPnL(data.total_pnl)
        if (data.daily_pnl !== undefined) setDailyPnL(data.daily_pnl)
        
        // Update active strategy
        if (data.active_positions && data.active_positions.length > 0) {
          setActiveStrategy(data.active_positions[0])
        } else {
          setActiveStrategy(null)
        }
      }
    } catch (error) {
      console.error('Failed to advance:', error)
      alert('Failed to advance. Check backend connection.')
    } finally {
      setLoading(false)
    }
  }

  const handleStrategyExecuted = () => {
    // Refresh state after strategy execution
    // The strategy will be reflected in next API call
  }

  return (
    <div className="replay-view">
      <div className="replay-header">
        <div className="header-left">
          <h2>📊 Replay: {currentDate || 'Loading...'}</h2>
          <span className="state-badge">{replayState}</span>
        </div>
        <button onClick={onExit} className="exit-button">🚪 Exit Replay</button>
      </div>

      <div className="pnl-panel">
        <div className="pnl-metric">
          <label>Daily PnL</label>
          <span className={dailyPnL >= 0 ? 'positive' : 'negative'}>
            ₹ {dailyPnL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="pnl-metric">
          <label>Cumulative PnL</label>
          <span className={totalPnL >= 0 ? 'positive' : 'negative'}>
            ₹ {totalPnL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="pnl-metric">
          <label>Position</label>
          <span>{activeStrategy ? '🟢 ACTIVE' : '⚪ FLAT'}</span>
        </div>
      </div>

      <div className="chart-container" ref={chartContainerRef}></div>

      <div className="replay-controls">
        {replayState === 'DAY_OPEN_REVEALED' && (
          <StrategyPanel
            sessionId={sessionId}
            API_URL={API_URL}
            onStrategyExecuted={handleStrategyExecuted}
          />
        )}

        {activeStrategy && (
          <div className="active-strategy">
            <p>Active Strategy: {activeStrategy.direction_state} | Entry: {activeStrategy.entry_time}</p>
          </div>
        )}

        <button 
          onClick={handleNext} 
          disabled={loading}
          className="next-button"
        >
          {loading ? 'Loading...' : '⏭️ NEXT CANDLE →'}
        </button>
      </div>
    </div>
  )
}

export default ReplayView
