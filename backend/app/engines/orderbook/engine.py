from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional

from app.models.domain import BookLevel, VisibleOrderBook


class OrderBookEngine:
    def __init__(self, rolling_window: int = 50) -> None:
        self.state: Dict[str, VisibleOrderBook] = {}
        self.spread_hist: Dict[str, deque] = {}
        self.depth_hist: Dict[str, deque] = {}
        self.rolling_window = rolling_window

    def _to_levels(self, row: dict, side: str) -> List[BookLevel]:
        levels: List[BookLevel] = []
        for i in [1, 2, 3]:
            p = row.get(f"{side}_price_{i}")
            v = row.get(f"{side}_volume_{i}")
            if p is None or v is None:
                continue
            if str(p) == "nan" or str(v) == "nan":
                continue
            try:
                pf, vf = float(p), float(v)
            except ValueError:
                continue
            if vf <= 0:
                continue
            levels.append(BookLevel(price=pf, volume=vf))
        return levels

    def update_from_snapshot(self, row: dict) -> VisibleOrderBook:
        product = row["product"]
        bids = self._to_levels(row, "bid")
        asks = self._to_levels(row, "ask")
        best_bid = bids[0].price if bids else None
        best_ask = asks[0].price if asks else None
        spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
        bid_depth = sum(b.volume for b in bids)
        ask_depth = sum(a.volume for a in asks)
        mid = (best_bid + best_ask) / 2 if spread is not None else row.get("mid_price")
        top_bv = bids[0].volume if bids else 0.0
        top_av = asks[0].volume if asks else 0.0
        top_imb = (top_bv - top_av) / max(top_bv + top_av, 1e-9)
        top3_imb = (bid_depth - ask_depth) / max(bid_depth + ask_depth, 1e-9)
        weighted_mid = None
        microprice = None
        if best_bid is not None and best_ask is not None:
            weighted_mid = (best_bid * ask_depth + best_ask * bid_depth) / max((bid_depth + ask_depth), 1e-9)
            microprice = (best_ask * top_bv + best_bid * top_av) / max(top_bv + top_av, 1e-9)

        spread_regime = "TIGHT" if spread is not None and spread <= 1 else "WIDE"
        book = VisibleOrderBook(
            product=product,
            timestamp=int(row["timestamp"]),
            day=int(row["day"]),
            bids=bids,
            asks=asks,
            best_bid=best_bid,
            best_ask=best_ask,
            spread=spread,
            mid_price=mid,
            weighted_mid=weighted_mid,
            microprice=microprice,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            top_imbalance=top_imb,
            top3_imbalance=top3_imb,
            book_pressure=top3_imb,
            depth_skew=top3_imb,
            spread_regime=spread_regime,
        )
        self.state[product] = book
        self.spread_hist.setdefault(product, deque(maxlen=self.rolling_window)).append(spread or 0)
        self.depth_hist.setdefault(product, deque(maxlen=self.rolling_window)).append(bid_depth + ask_depth)
        return book

    def get(self, product: str) -> Optional[VisibleOrderBook]:
        return self.state.get(product)
