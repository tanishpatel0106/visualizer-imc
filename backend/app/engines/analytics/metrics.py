from __future__ import annotations

from typing import Dict, List
import numpy as np

from app.models.domain import FillEvent


def compute_metrics(equity_curve: List[float], fills: List[FillEvent], realized: float, unrealized: float, positions: Dict[str, float]) -> Dict:
    arr = np.array(equity_curve if equity_curve else [0.0], dtype=float)
    ret = np.diff(arr, prepend=arr[0])
    wins = ret[ret > 0]
    losses = ret[ret < 0]
    dd = np.maximum.accumulate(arr) - arr
    return {
        "total_pnl": float(realized + unrealized),
        "realized_pnl": float(realized),
        "unrealized_pnl": float(unrealized),
        "num_trades": len(fills),
        "turnover": float(sum(abs(f.price * f.quantity) for f in fills)),
        "avg_win": float(wins.mean()) if wins.size else 0.0,
        "avg_loss": float(losses.mean()) if losses.size else 0.0,
        "win_rate": float(len(wins) / max(len(wins) + len(losses), 1)),
        "max_drawdown": float(dd.max()) if dd.size else 0.0,
        "volatility_pnl": float(ret.std()) if ret.size else 0.0,
        "sharpe_like": float(ret.mean() / max(ret.std(), 1e-9)),
        "max_inventory": float(max([abs(x) for x in positions.values()] + [0.0])),
    }
