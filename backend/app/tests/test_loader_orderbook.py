import pandas as pd
from app.engines.data.loader import DataLoader
from app.engines.orderbook.engine import OrderBookEngine
import pytest


def test_loader_schema_validation(tmp_path):
    p = tmp_path / "prices_round_0_day_-1.csv"
    t = tmp_path / "trades_round_0_day_-1.csv"
    pd.DataFrame([
        {"day": -1, "timestamp": 1, "product": "EMERALDS", "bid_price_1": 99, "bid_volume_1": 10, "ask_price_1": 101, "ask_volume_1": 12}
    ]).to_csv(p, index=False)
    pd.DataFrame([
        {"day": -1, "timestamp": 1, "symbol": "EMERALDS", "price": 100, "quantity": 2}
    ]).to_csv(t, index=False)
    l = DataLoader()
    b = l.load("x", str(tmp_path))
    assert len(b.prices) == 1
    ev = l.build_events()
    assert len(ev) == 2


def test_orderbook_metrics():
    ob = OrderBookEngine()
    b = ob.update_from_snapshot({"day": -1, "timestamp": 1, "product": "EMERALDS", "bid_price_1": 99, "bid_volume_1": 10, "bid_price_2": 98, "bid_volume_2": 5, "bid_price_3": 97, "bid_volume_3": 5, "ask_price_1": 101, "ask_volume_1": 10, "ask_price_2": 102, "ask_volume_2": 8, "ask_price_3": 103, "ask_volume_3": 8})
    assert b.spread == 2
    assert b.bid_depth == 20
    assert b.ask_depth == 26


def test_semicolon_csv_parsing_and_missing_trade_day(tmp_path):
    p = tmp_path / "prices_round_0_day_-1.csv"
    t = tmp_path / "trades_round_0_day_-1.csv"
    p.write_text(
        "day;timestamp;product;bid_price_1;bid_volume_1;ask_price_1;ask_volume_1\n"
        "-1;0;EMERALDS;9992;14;10008;14\n"
    )
    t.write_text(
        "timestamp;buyer;seller;symbol;currency;price;quantity\n"
        "3200;;;EMERALDS;XIRECS;9992.0;8\n"
    )
    l = DataLoader()
    b = l.load("semi", str(tmp_path))
    assert list(b.prices["product"])[0] == "EMERALDS"
    assert int(list(b.trades["day"])[0]) == -1


def test_load_raises_when_no_files(tmp_path):
    l = DataLoader()
    with pytest.raises(ValueError):
        l.load("none", str(tmp_path))
