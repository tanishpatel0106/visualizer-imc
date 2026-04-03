from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.engines.analytics.metrics import compute_metrics
from app.engines.execution.engine import ExecutionEngine, Portfolio
from app.engines.orderbook.engine import OrderBookEngine
from app.engines.strategies.builtins import StrategyContext, build_registry
from app.models.domain import BacktestRun, DebugFrame, EventType, FillEvent, OrderSide, StrategyOrder


class BacktestEngine:
    def __init__(self) -> None:
        self.registry = build_registry()

    def run(
        self,
        events: List,
        strategy_id: str,
        params: Optional[Dict[str, Any]] = None,
        execution_model: str = "balanced",
        position_limits: Optional[Dict[str, float]] = None,
    ) -> BacktestRun:
        params = params or {}
        position_limits = position_limits or {}
        strategy = self.registry[strategy_id]
        ob = OrderBookEngine()
        ex = ExecutionEngine(model=execution_model)
        pf = Portfolio()
        history: Dict[str, List[float]] = {}
        trace: List[DebugFrame] = []
        fills: List[FillEvent] = []
        equity: List[float] = []

        for ev in events:
            if ev.event_type == EventType.BOOK_SNAPSHOT:
                book = ob.update_from_snapshot(ev.payload)
                mid = float(book.mid_price or 0.0)
                history.setdefault(book.product, []).append(mid)
                pos = pf.positions.get(book.product, 0.0)
                ctx = StrategyContext(product=book.product, timestamp=book.timestamp, mid=mid, spread=float(book.spread or 0.0), microprice=float(book.microprice or mid), imbalance=float(book.top3_imbalance), position=pos, history=history[book.product])
                orders = strategy.decide(ctx, params)
                rejected = []
                accepted: List[StrategyOrder] = []
                for o in orders:
                    lim = position_limits.get(o.product, 1000)
                    projected = pos + (o.quantity if o.side == OrderSide.BUY else -o.quantity)
                    if abs(projected) > lim:
                        rejected.append(o.order_id)
                    else:
                        accepted.append(o)
                frame_fills: List[FillEvent] = []
                for o in accepted:
                    fs = ex.submit(o, book)
                    for f in fs:
                        ex.apply_fill(pf, f)
                    frame_fills.extend(fs)
                passive = ex.check_passive_fills(book)
                for f in passive:
                    ex.apply_fill(pf, f)
                frame_fills.extend(passive)
                fills.extend(frame_fills)
                unreal = sum(q * ((book.mid_price or 0.0) - pf.avg_price.get(prod, book.mid_price or 0.0)) for prod, q in pf.positions.items())
                total = pf.realized + unreal
                equity.append(total)
                trace.append(DebugFrame(timestamp=book.timestamp, day=book.day, product=book.product, best_bid=book.best_bid, best_ask=book.best_ask, spread=book.spread, imbalance=book.top3_imbalance, position=pos, inventory=pf.positions.copy(), strategy_inputs={"mid": mid, "imbalance": book.top3_imbalance}, strategy_outputs={"orders": [x.model_dump() for x in accepted], "rejected": rejected}, fills=frame_fills, pnl_total=total, notes=[] if not rejected else [f"rejected:{','.join(rejected)}"]))
            elif ev.event_type == EventType.TRADE_PRINT:
                b = ob.get(ev.product)
                if b:
                    passive = ex.check_passive_fills(b, trade_price=float(ev.payload["price"]), trade_qty=float(ev.payload["quantity"]))
                    for f in passive:
                        ex.apply_fill(pf, f)
                        fills.append(f)

        metrics = compute_metrics(equity_curve=equity, fills=fills, realized=pf.realized, unrealized=(equity[-1] - pf.realized if equity else 0.0), positions=pf.positions)
        return BacktestRun(run_id=str(uuid.uuid4()), strategy_id=strategy_id, execution_model=execution_model, products=sorted(list({e.product for e in events if e.product})), days=sorted(list({e.day for e in events})), metrics=metrics, debug_trace=trace, fills=fills)
