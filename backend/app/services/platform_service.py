from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.engines.backtest.engine import BacktestEngine
from app.engines.data.loader import DataLoader
from app.engines.strategies.builtins import build_registry
from app.engines.sandbox.runner import StrategySandbox
from app.models.domain import ReplaySession
from app.storage.repository import Repository


class PlatformService:
    def __init__(self) -> None:
        self.loader = DataLoader()
        self.backtester = BacktestEngine()
        self.repo = Repository()
        self.registry = build_registry()
        self.sandbox = StrategySandbox()
        self.replay = ReplaySession(session_id="default", running=False)
        self.replay_events = []

        for sid, s in self.registry.items():
            self.repo.save_strategy(sid, "builtin", s.name, "", {"category": s.category, "description": s.description, "parameters": [p.model_dump() for p in s.parameters]})

    def load_dataset(self, dataset_id: str, path: str) -> Dict[str, Any]:
        raw = Path(path)
        repo_root = Path(__file__).resolve().parents[3]
        candidates = [raw, repo_root / raw, repo_root / "sample_data"]
        resolved = next((p for p in candidates if p.exists()), raw)
        bundle = self.loader.load(dataset_id, str(resolved))
        self.replay_events = self.loader.build_events()
        self.replay.total_events = len(self.replay_events)
        return {"dataset_id": bundle.dataset_id, "prices": len(bundle.prices), "trades": len(bundle.trades)}

    def datasets(self) -> List[Dict[str, Any]]:
        return [{"id": self.loader.loaded.dataset_id, "path": str(self.loader.loaded.base_path)}] if self.loader.loaded else []

    def products(self) -> List[str]:
        if not self.loader.loaded:
            return []
        return sorted(self.loader.loaded.prices["product"].unique().tolist())

    def days(self) -> List[int]:
        if not self.loader.loaded:
            return []
        return sorted(self.loader.loaded.prices["day"].unique().tolist())

    def snapshots(self, product: Optional[str] = None, day: Optional[int] = None, limit: int = 2000):
        if not self.loader.loaded:
            return []
        df = self.loader.loaded.prices
        if product:
            df = df[df["product"] == product.upper()]
        if day is not None:
            df = df[df["day"] == day]
        return df.sort_values(["day", "timestamp"]).head(limit).to_dict(orient="records")

    def trades(self, product: Optional[str] = None, day: Optional[int] = None, limit: int = 2000):
        if not self.loader.loaded:
            return []
        df = self.loader.loaded.trades
        if product:
            df = df[df["symbol"] == product.upper()]
        if day is not None:
            df = df[df["day"] == day]
        return df.sort_values(["day", "timestamp"]).head(limit).to_dict(orient="records")

    def run_backtest(self, strategy_id: str, params: Dict[str, Any], execution_model: str, products: List[str], days: List[int]) -> Dict[str, Any]:
        if not self.loader.loaded:
            raise ValueError("No dataset loaded. Call /datasets/load first.")
        events = self.loader.build_events(products=products, days=days)
        if strategy_id.startswith("upload:"):
            run = self._run_uploaded(strategy_id, events, execution_model)
        else:
            run = self.backtester.run(events, strategy_id=strategy_id, params=params, execution_model=execution_model)
        artifacts = self._export_artifacts(run)
        self.repo.save_run(run.run_id, strategy_id, run.model_dump(exclude={"debug_trace", "fills"}), run.metrics, artifacts)
        return {"run": run.model_dump(), "artifacts": artifacts}

    def _run_uploaded(self, strategy_id: str, events, execution_model: str):
        # lightweight adapter to builtin engine using signal from uploaded strategy
        meta = self.repo.get_strategy(strategy_id)
        trader = self.sandbox.load(Path(meta["path"]))
        # map uploaded strategy into one-shot imbalance strategy by reading output orders each frame
        from app.engines.orderbook.engine import OrderBookEngine
        from app.engines.execution.engine import ExecutionEngine, Portfolio
        from app.models.domain import BacktestRun, DebugFrame, FillEvent, OrderSide, StrategyOrder, EventType
        import uuid

        ob = OrderBookEngine(); ex = ExecutionEngine(model=execution_model); pf = Portfolio(); trace=[]; fills=[]; eq=[]
        for ev in events:
            if ev.event_type != EventType.BOOK_SNAPSHOT:
                continue
            book = ob.update_from_snapshot(ev.payload)
            state = {"timestamp": book.timestamp, "product": book.product, "best_bid": book.best_bid, "best_ask": book.best_ask, "mid": book.mid_price, "position": pf.positions.get(book.product, 0), "book": ev.payload}
            out = self.sandbox.run(trader, state)
            frame_fills=[]
            for i, od in enumerate(out["orders"] if isinstance(out["orders"], list) else []):
                side = OrderSide.BUY if str(od.get("side", "BUY")).upper() == "BUY" else OrderSide.SELL
                order = StrategyOrder(order_id=f"{strategy_id}-{book.timestamp}-{i}", product=od.get("product", book.product), side=side, price=float(od.get("price", book.mid_price or 0)), quantity=float(abs(od.get("quantity", 0))), timestamp=book.timestamp)
                for f in ex.submit(order, book):
                    ex.apply_fill(pf, f); frame_fills.append(f)
            for f in ex.check_passive_fills(book):
                ex.apply_fill(pf, f); frame_fills.append(f)
            fills.extend(frame_fills)
            unreal = sum(q * ((book.mid_price or 0.0) - pf.avg_price.get(prod, book.mid_price or 0.0)) for prod, q in pf.positions.items())
            total = pf.realized + unreal; eq.append(total)
            trace.append(DebugFrame(timestamp=book.timestamp, day=book.day, product=book.product, best_bid=book.best_bid, best_ask=book.best_ask, spread=book.spread, imbalance=book.top3_imbalance, position=pf.positions.get(book.product, 0), inventory=pf.positions.copy(), strategy_inputs=state, strategy_outputs=out, fills=frame_fills, pnl_total=total, notes=[]))
        from app.engines.analytics.metrics import compute_metrics
        metrics=compute_metrics(eq,fills,pf.realized,(eq[-1]-pf.realized if eq else 0),pf.positions)
        return BacktestRun(run_id=str(uuid.uuid4()), strategy_id=strategy_id, execution_model=execution_model, products=sorted({e.product for e in events if e.product}), days=sorted({e.day for e in events}), metrics=metrics, debug_trace=trace, fills=fills)

    def _export_artifacts(self, run) -> Dict[str, str]:
        out_dir = Path("backend/app/storage/artifacts") / run.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        summary = out_dir / "summary.json"
        metrics = out_dir / "metrics.csv"
        fills = out_dir / "fills.csv"
        trace = out_dir / "trace.jsonl"
        summary.write_text(json.dumps(run.model_dump(exclude={"debug_trace", "fills"}), indent=2))
        with metrics.open("w", newline="") as f:
            w = csv.writer(f); w.writerow(["metric", "value"]); [w.writerow([k, v]) for k, v in run.metrics.items()]
        with fills.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["order_id", "product", "side", "price", "quantity", "timestamp", "passive"])
            w.writeheader(); [w.writerow(x.model_dump()) for x in run.fills]
        with trace.open("w") as f:
            for frame in run.debug_trace:
                f.write(json.dumps(frame.model_dump()) + "\n")
        return {"summary": str(summary), "metrics": str(metrics), "fills": str(fills), "trace": str(trace), "bundle_dir": str(out_dir)}

    def upload_strategy(self, name: str, content: bytes) -> Dict[str, Any]:
        strategy_id = f"upload:{uuid4()}"
        path = Path("backend/app/storage/uploaded_strategies")
        path.mkdir(parents=True, exist_ok=True)
        f = path / f"{strategy_id.replace(':','_')}.py"
        f.write_bytes(content)
        self.sandbox.validate(content.decode("utf-8"))
        self.repo.save_strategy(strategy_id, "upload", name, str(f), {})
        return {"id": strategy_id, "name": name}
