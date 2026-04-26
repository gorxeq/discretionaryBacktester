from typing import List, Dict
import numpy as np

class SummaryEngine:
    def calculate_summary(self, session_data: Dict) -> Dict:
        pnl_history = session_data.get("pnl_history", [])
        trades = session_data.get("trade_history", [])
        
        cumulative_pnl = session_data.get("total_pnl", 0.0)
        total_trades = len(trades)
        
        wins = [t for t in trades if t.get("realized_pnl", 0) > 0]
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        
        # Simple Sharpe calculation (daily returns approach)
        returns = [p.get("pnl", 0) for p in pnl_history if isinstance(p, dict)]
        sharpe = 0.0
        if len(returns) > 1:
            std = np.std(returns)
            if std > 0:
                sharpe = np.mean(returns) / std * np.sqrt(252) # Annualized

        return {
            "cumulative_pnl": cumulative_pnl,
            "total_trades": total_trades,
            "win_rate": f"{win_rate:.2f}%",
            "sharpe_ratio": f"{sharpe:.2f}",
            "trade_history": trades
        }
