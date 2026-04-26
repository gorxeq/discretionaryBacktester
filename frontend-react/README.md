# Options Strategy Replay - React Frontend

TradingView-style bar replay frontend built with React and lightweight-charts.

## Setup

1. Install Node.js (if not already installed)
2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The app will be available at http://localhost:3000

## Features

- TradingView-style candlestick charting with lightweight-charts
- Bar-by-bar replay functionality
- Strategy deployment with 5 directional options (-2 to +2)
- Real-time PnL tracking
- No double-click reset (disabled in chart config)

## Backend

Make sure the FastAPI backend is running on http://127.0.0.1:8000
