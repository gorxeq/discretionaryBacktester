import React, { useState } from 'react'
import axios from 'axios'
import './StrategyPanel.css'

function StrategyPanel({ sessionId, API_URL, onStrategyExecuted }) {
  const [selectedDirection, setSelectedDirection] = useState(null)
  const [quantityMultiplier, setQuantityMultiplier] = useState(1)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)

  const strategyConfigs = [
    { direction: -2, label: '🔴 Strongly Bearish', desc: 'Naked Put Buy', color: '#f23645' },
    { direction: -1, label: '🟠 Moderately Bearish', desc: 'Bear Call Spread', color: '#ff6b35' },
    { direction: 0, label: '⚪ Directionless', desc: 'Naked Strangle', color: '#888888' },
    { direction: 1, label: '🟢 Moderately Bullish', desc: 'Bull Put Spread', color: '#089981' },
    { direction: 2, label: '🟢 Strongly Bullish', desc: 'Naked Call Buy', color: '#00d4aa' },
  ]

  const handleStrategySelect = async (direction) => {
    setSelectedDirection(direction)
    setLoading(true)

    try {
      const response = await axios.post(`${API_URL}/strategy/preview`, {
        session_id: sessionId,
        direction_state: direction,
        quantity_multiplier: quantityMultiplier
      })

      setPreview(response.data)
    } catch (error) {
      console.error('Failed to preview strategy:', error)
      alert('Failed to preview strategy')
    } finally {
      setLoading(false)
    }
  }

  const handleExecute = async () => {
    if (!selectedDirection) return

    setLoading(true)
    try {
      const response = await axios.post(`${API_URL}/strategy/execute`, {
        session_id: sessionId,
        direction_state: selectedDirection,
        quantity_multiplier: quantityMultiplier
      })

      if (response.data.status === 'ACTIVE') {
        alert('Strategy executed successfully!')
        setSelectedDirection(null)
        setPreview(null)
        onStrategyExecuted()
      }
    } catch (error) {
      console.error('Failed to execute strategy:', error)
      alert('Failed to execute strategy: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSkip = async () => {
    // Skip day - just advance
    onStrategyExecuted()
  }

  return (
    <div className="strategy-panel">
      <h3>🎯 Deploy Strategy</h3>
      <p className="caption">Select your directional conviction for today's market</p>

      <div className="strategy-buttons">
        {strategyConfigs.map(config => (
          <button
            key={config.direction}
            onClick={() => handleStrategySelect(config.direction)}
            className={`strategy-button ${selectedDirection === config.direction ? 'selected' : ''}`}
            style={{ borderColor: config.color }}
            disabled={loading}
          >
            <div className="strategy-label">{config.label}</div>
            <div className="strategy-desc">{config.desc}</div>
          </button>
        ))}
      </div>

      <div className="quantity-input">
        <label>Quantity Multiplier:</label>
        <input
          type="number"
          min="1"
          max="10"
          value={quantityMultiplier}
          onChange={(e) => {
            setQuantityMultiplier(parseInt(e.target.value) || 1)
            if (selectedDirection) {
              handleStrategySelect(selectedDirection)
            }
          }}
        />
      </div>

      {preview && (
        <div className="preview-panel">
          <h4>📋 Strategy Preview</h4>
          <div className="preview-info">
            <p><strong>Margin Required:</strong> ₹ {preview.margin_required.toLocaleString('en-IN')}</p>
            <p><strong>Legs:</strong></p>
            <ul>
              {preview.legs.map((leg, idx) => (
                <li key={idx}>
                  {leg.option_type} {leg.strike} x {leg.qty} (Expiry: {leg.expiry})
                </li>
              ))}
            </ul>
          </div>
          <button onClick={handleExecute} className="execute-button" disabled={loading}>
            ✅ Execute Strategy
          </button>
        </div>
      )}

      <button onClick={handleSkip} className="skip-button" disabled={loading}>
        ⏭️ Skip Day (No Strategy)
      </button>
    </div>
  )
}

export default StrategyPanel
