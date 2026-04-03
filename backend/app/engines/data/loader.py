from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from app.models.domain import Event, EventType

PRICE_REQUIRED = [
    "day", "timestamp", "product", "bid_price_1", "bid_volume_1", "ask_price_1", "ask_volume_1"
]
TRADE_REQUIRED = ["timestamp", "symbol", "price", "quantity"]


@dataclass
class DatasetBundle:
    dataset_id: str
    base_path: Path
    prices: pd.DataFrame
    trades: pd.DataFrame


class DataLoader:
    def __init__(self) -> None:
        self.loaded: Optional[DatasetBundle] = None

    def discover(self, directory: str) -> Dict[str, List[str]]:
        p = Path(directory)
        prices = sorted(str(x) for x in p.glob("prices*.csv"))
        trades = sorted(str(x) for x in p.glob("trades*.csv"))
        return {"prices": prices, "trades": trades}

    def _read_csv_flexible(self, file_path: str) -> pd.DataFrame:
        # Tutorial datasets are frequently `;` separated; use sniffer-based parsing.
        return pd.read_csv(file_path, sep=None, engine="python")

    def _empty_price_frame(self) -> pd.DataFrame:
        cols = PRICE_REQUIRED + [
            "bid_price_2", "bid_volume_2", "bid_price_3", "bid_volume_3",
            "ask_price_2", "ask_volume_2", "ask_price_3", "ask_volume_3",
        ]
        return pd.DataFrame(columns=cols)

    def _empty_trade_frame(self) -> pd.DataFrame:
        cols = TRADE_REQUIRED + ["day", "buyer", "seller", "currency"]
        return pd.DataFrame(columns=cols)

    def _read_prices(self, files: List[str]) -> pd.DataFrame:
        frames = []
        for f in files:
            df = self._read_csv_flexible(f)
            missing = [c for c in PRICE_REQUIRED if c not in df.columns]
            if missing:
                raise ValueError(f"Price file {f} missing columns: {missing}")
            for level in [2, 3]:
                for side in ["bid", "ask"]:
                    pcol = f"{side}_price_{level}"
                    vcol = f"{side}_volume_{level}"
                    if pcol not in df:
                        df[pcol] = pd.NA
                    if vcol not in df:
                        df[vcol] = pd.NA
            df["product"] = df["product"].astype(str).str.upper()
            frames.append(df)
        out = pd.concat(frames, ignore_index=True) if frames else self._empty_price_frame()
        if out.empty:
            return out
        out["day"] = out["day"].astype(int)
        out["timestamp"] = out["timestamp"].astype(int)
        return out

    def _read_trades(self, files: List[str]) -> pd.DataFrame:
        frames = []
        for f in files:
            df = self._read_csv_flexible(f)
            missing = [c for c in TRADE_REQUIRED if c not in df.columns]
            if missing:
                raise ValueError(f"Trade file {f} missing columns: {missing}")
            if "day" not in df.columns:
                df["day"] = 0
            if "buyer" not in df.columns:
                df["buyer"] = ""
            if "seller" not in df.columns:
                df["seller"] = ""
            if "currency" not in df.columns:
                df["currency"] = "USD"
            df["symbol"] = df["symbol"].astype(str).str.upper()
            frames.append(df)
        out = pd.concat(frames, ignore_index=True) if frames else self._empty_trade_frame()
        if out.empty:
            return out
        out["day"] = out["day"].astype(int)
        out["timestamp"] = out["timestamp"].astype(int)
        return out

    def load(self, dataset_id: str, directory: str) -> DatasetBundle:
        files = self.discover(directory)
        prices = self._read_prices(files["prices"])
        trades = self._read_trades(files["trades"])
        self.loaded = DatasetBundle(dataset_id=dataset_id, base_path=Path(directory), prices=prices, trades=trades)
        return self.loaded

    def build_events(self, products: Optional[List[str]] = None, days: Optional[List[int]] = None) -> List[Event]:
        if not self.loaded:
            raise RuntimeError("No dataset loaded")
        prices = self.loaded.prices
        trades = self.loaded.trades
        if products:
            products = [p.upper() for p in products]
            prices = prices[prices["product"].isin(products)]
            trades = trades[trades["symbol"].isin(products)]
        if days is not None and len(days) > 0:
            prices = prices[prices["day"].isin(days)]
            trades = trades[trades["day"].isin(days)]
        events: List[Event] = []
        for r in prices.to_dict(orient="records"):
            events.append(Event(event_type=EventType.BOOK_SNAPSHOT, timestamp=int(r["timestamp"]), day=int(r["day"]), product=r["product"], payload=r))
        for r in trades.to_dict(orient="records"):
            events.append(Event(event_type=EventType.TRADE_PRINT, timestamp=int(r["timestamp"]), day=int(r["day"]), product=r["symbol"], payload=r))
        events.sort(key=lambda e: (e.day, e.timestamp, 0 if e.event_type == EventType.BOOK_SNAPSHOT else 1))
        return events
