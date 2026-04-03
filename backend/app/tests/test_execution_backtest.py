from app.engines.backtest.engine import BacktestEngine
from app.models.domain import Event, EventType


def test_backtest_runs():
    events = [
        Event(event_type=EventType.BOOK_SNAPSHOT, day=-1, timestamp=1, product="EMERALDS", payload={"day": -1, "timestamp": 1, "product": "EMERALDS", "bid_price_1": 99, "bid_volume_1": 10, "ask_price_1": 101, "ask_volume_1": 10}),
        Event(event_type=EventType.BOOK_SNAPSHOT, day=-1, timestamp=2, product="EMERALDS", payload={"day": -1, "timestamp": 2, "product": "EMERALDS", "bid_price_1": 100, "bid_volume_1": 10, "ask_price_1": 102, "ask_volume_1": 10}),
    ]
    bt = BacktestEngine()
    run = bt.run(events, strategy_id="imbalance_follow", execution_model="balanced")
    assert run.run_id
    assert "total_pnl" in run.metrics
