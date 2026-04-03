from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from app.models.domain import FillEvent, OrderSide, OrderStatus, StrategyOrder, VisibleOrderBook


@dataclass
class Portfolio:
    cash: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)
    avg_price: Dict[str, float] = field(default_factory=dict)
    realized: float = 0.0


class ExecutionEngine:
    def __init__(self, model: str = "balanced", fees_bps: float = 0.0, allow_cross_levels: bool = True) -> None:
        self.model = model
        self.fees_bps = fees_bps
        self.allow_cross_levels = allow_cross_levels
        self.resting: Dict[str, List[StrategyOrder]] = {}

    def _fill(self, order: StrategyOrder, price: float, qty: float, ts: int, passive: bool = False) -> FillEvent:
        order.filled_quantity += qty
        order.status = OrderStatus.FILLED if order.filled_quantity >= order.quantity else OrderStatus.PARTIAL
        return FillEvent(order_id=order.order_id, product=order.product, side=order.side, price=price, quantity=qty, timestamp=ts, passive=passive)

    def apply_fill(self, pf: Portfolio, fill: FillEvent) -> None:
        sign = 1 if fill.side == OrderSide.BUY else -1
        px = fill.price
        qty = fill.quantity
        product = fill.product
        prev = pf.positions.get(product, 0.0)
        new = prev + sign * qty
        fee = abs(px * qty) * self.fees_bps / 10000.0
        pf.cash -= sign * px * qty + fee
        if prev == 0 or (prev > 0 and sign > 0) or (prev < 0 and sign < 0):
            old_avg = pf.avg_price.get(product, px)
            pf.avg_price[product] = (old_avg * abs(prev) + px * qty) / max(abs(prev) + qty, 1e-9)
        else:
            pnl_qty = min(abs(prev), qty)
            avg = pf.avg_price.get(product, px)
            if prev > 0:
                pf.realized += (px - avg) * pnl_qty
            else:
                pf.realized += (avg - px) * pnl_qty
            if abs(new) < 1e-9:
                pf.avg_price[product] = 0.0
            elif abs(qty) > abs(prev):
                pf.avg_price[product] = px
        pf.positions[product] = new

    def execute_aggressive(self, order: StrategyOrder, book: VisibleOrderBook) -> List[FillEvent]:
        fills: List[FillEvent] = []
        levels = book.asks if order.side == OrderSide.BUY else book.bids
        remaining = order.quantity - order.filled_quantity
        for i, lvl in enumerate(levels):
            if i > 0 and not self.allow_cross_levels:
                break
            crossable = order.price >= lvl.price if order.side == OrderSide.BUY else order.price <= lvl.price
            if not crossable and order.order_type != "MARKET":
                continue
            qty = min(remaining, lvl.volume)
            if qty <= 0:
                break
            fills.append(self._fill(order, lvl.price, qty, book.timestamp, passive=False))
            remaining -= qty
            if remaining <= 0:
                break
        return fills

    def submit(self, order: StrategyOrder, book: VisibleOrderBook) -> List[FillEvent]:
        fills = self.execute_aggressive(order, book)
        if order.status in [OrderStatus.OPEN, OrderStatus.PARTIAL] and order.filled_quantity < order.quantity:
            if self.model != "conservative":
                self.resting.setdefault(order.product, []).append(order)
        return fills

    def check_passive_fills(self, book: VisibleOrderBook, trade_price: float | None = None, trade_qty: float | None = None) -> List[FillEvent]:
        out: List[FillEvent] = []
        for o in list(self.resting.get(book.product, [])):
            remaining = o.quantity - o.filled_quantity
            if remaining <= 0:
                continue
            touch = (o.side == OrderSide.BUY and book.best_ask is not None and o.price >= book.best_ask) or (
                o.side == OrderSide.SELL and book.best_bid is not None and o.price <= book.best_bid
            )
            trade_support = trade_price is not None and ((o.side == OrderSide.BUY and o.price >= trade_price) or (o.side == OrderSide.SELL and o.price <= trade_price))
            allow = touch or (self.model in ["balanced", "optimistic"] and trade_support)
            if self.model == "optimistic" and not allow:
                allow = abs((book.mid_price or o.price) - o.price) <= 1
            if allow:
                q = remaining if trade_qty is None else min(remaining, trade_qty * (0.25 if self.model == "balanced" else 0.6))
                out.append(self._fill(o, o.price, q, book.timestamp, passive=True))
            if o.status == OrderStatus.FILLED:
                self.resting[book.product].remove(o)
        return out
