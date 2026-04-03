from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import math

from app.models.domain import OrderSide, StrategyDefinition, StrategyOrder, StrategyParameter


@dataclass
class StrategyContext:
    product: str
    timestamp: int
    mid: float
    spread: float
    microprice: float
    imbalance: float
    position: float
    history: List[float]


class BaseBuiltin:
    strategy_id: str = "base"
    name: str = "Base"
    category: str = "Template"
    description: str = ""
    parameters: List[StrategyParameter] = []

    def decide(self, ctx: StrategyContext, params: Dict[str, Any]) -> List[StrategyOrder]:
        return []

    def definition(self) -> StrategyDefinition:
        return StrategyDefinition(
            strategy_id=self.strategy_id,
            name=self.name,
            category=self.category,
            description=self.description,
            parameters=self.parameters,
            source_code=self.__class__.__name__,
        )


class SignalThresholdStrategy(BaseBuiltin):
    signal_name = "imbalance"
    def decide(self, ctx: StrategyContext, params: Dict[str, Any]) -> List[StrategyOrder]:
        threshold = float(params.get("threshold", 0.1))
        qty = float(params.get("qty", 5))
        limit_offset = float(params.get("limit_offset", 0))
        inv_limit = float(params.get("inventory_limit", 50))
        signal = self._signal(ctx)
        orders: List[StrategyOrder] = []
        if signal > threshold and ctx.position < inv_limit:
            orders.append(StrategyOrder(order_id=f"{self.strategy_id}-{ctx.timestamp}-b", product=ctx.product, side=OrderSide.BUY, price=ctx.mid + limit_offset, quantity=qty, timestamp=ctx.timestamp))
        elif signal < -threshold and ctx.position > -inv_limit:
            orders.append(StrategyOrder(order_id=f"{self.strategy_id}-{ctx.timestamp}-s", product=ctx.product, side=OrderSide.SELL, price=ctx.mid - limit_offset, quantity=qty, timestamp=ctx.timestamp))
        return orders

    def _signal(self, ctx: StrategyContext) -> float:
        return ctx.imbalance


def make_strategy(strategy_id: str, name: str, category: str, description: str, signal_name: str = "imbalance"):
    class _S(SignalThresholdStrategy):
        pass
    _S.strategy_id = strategy_id
    _S.name = name
    _S.category = category
    _S.description = description
    _S.signal_name = signal_name
    _S.parameters = [
        StrategyParameter(name="threshold", type="float", default=0.1, min=0.0, max=2.0, tooltip="Signal trigger threshold"),
        StrategyParameter(name="qty", type="float", default=5, min=1, max=200, tooltip="Order size"),
        StrategyParameter(name="limit_offset", type="float", default=0.0, min=-2, max=2, tooltip="Limit price offset around mid"),
        StrategyParameter(name="inventory_limit", type="float", default=50, min=1, max=500, tooltip="Inventory guardrail"),
    ]

    def _signal(self, ctx: StrategyContext) -> float:
        if signal_name == "momentum":
            if len(ctx.history) < 5:
                return 0.0
            return (ctx.history[-1] - ctx.history[-5]) / max(ctx.history[-5], 1e-9)
        if signal_name == "microprice":
            return (ctx.microprice - ctx.mid) / max(ctx.spread or 1.0, 1e-9)
        if signal_name == "spread_reversion":
            return -((ctx.spread or 0.0) - 1.0)
        if signal_name == "mean_rev":
            if len(ctx.history) < 20:
                return 0.0
            m = sum(ctx.history[-20:]) / 20
            return (m - ctx.mid) / max(m, 1e-9)
        if signal_name == "ema_cross":
            if len(ctx.history) < 20:
                return 0.0
            fast = sum(ctx.history[-5:]) / 5
            slow = sum(ctx.history[-20:]) / 20
            return (fast - slow) / max(slow, 1e-9)
        if signal_name == "burst":
            return math.tanh(abs(ctx.imbalance) * 2) * (1 if ctx.imbalance > 0 else -1)
        return ctx.imbalance

    _S._signal = _signal
    return _S


def build_registry() -> Dict[str, BaseBuiltin]:
    specs = [
        ("fixed_spread_mm", "Fixed Spread Market Maker", "Market Making", "Quotes around mid at fixed offsets", "spread_reversion"),
        ("inventory_skew_mm", "Inventory Skewed MM", "Market Making", "Skews quoting by inventory and imbalance", "imbalance"),
        ("adaptive_spread_mm", "Adaptive Spread MM", "Market Making", "Adjusts quotes to spread regime", "spread_reversion"),
        ("avellaneda_style_mm", "Reservation Price MM", "Market Making", "Approximate A-S reservation-price style maker", "microprice"),
        ("ladder_mm", "Ladder Maker", "Market Making", "Places staggered quotes around fair value", "mean_rev"),
        ("mid_mean_reversion", "Mid Mean Reversion", "Mean Reversion", "Trades pullback to rolling mean", "mean_rev"),
        ("vwap_reversion", "VWAP Reversion", "Mean Reversion", "Proxy VWAP reversion strategy", "mean_rev"),
        ("bollinger_reversion", "Bollinger Reversion", "Mean Reversion", "Mean reversion on spread from rolling band", "mean_rev"),
        ("zscore_fair_reversion", "Z-score Fair Reversion", "Mean Reversion", "Z-score style fair value reversion", "mean_rev"),
        ("spread_regime_reversion", "Spread Compression Reversion", "Mean Reversion", "Reverts temporary spread expansions", "spread_reversion"),
        ("ema_crossover", "EMA Crossover", "Momentum/Trend", "Fast/slow crossover trend follower", "ema_cross"),
        ("sma_crossover", "SMA Crossover", "Momentum/Trend", "Simple moving average crossover", "ema_cross"),
        ("breakout", "Breakout", "Momentum/Trend", "Breakout on short window highs/lows", "momentum"),
        ("rolling_momentum", "Rolling Return Momentum", "Momentum/Trend", "Momentum on rolling returns", "momentum"),
        ("tradeflow_momentum", "Trade-flow Momentum", "Momentum/Trend", "Uses imbalance as order-flow proxy", "imbalance"),
        ("microprice_momentum", "Microprice Momentum", "Momentum/Trend", "Microprice deviation trend", "microprice"),
        ("imbalance_follow", "Imbalance Follow", "Microstructure", "Follows top-level imbalance", "imbalance"),
        ("queue_pressure", "Queue Pressure", "Microstructure", "Queue pressure response", "imbalance"),
        ("spread_capture", "Spread Capture", "Microstructure", "Captures spread mean reversion", "spread_reversion"),
        ("aggressor_response", "Aggressor Response", "Microstructure", "Responds to aggressor proxy", "burst"),
        ("trade_burst", "Trade Burst Reaction", "Microstructure", "Responds to burstiness proxy", "burst"),
        ("cross_product_spread", "Cross Product Spread Template", "Relative", "Template for relative-value spreads", "mean_rev"),
        ("relative_value_template", "Relative Value Template", "Relative", "Template for multi-product extension", "mean_rev"),
    ]
    out: Dict[str, BaseBuiltin] = {}
    for sid, n, c, d, sig in specs:
        out[sid] = make_strategy(sid, n, c, d, sig)()
    return out
