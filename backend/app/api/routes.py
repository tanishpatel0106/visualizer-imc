from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.platform_service import PlatformService

router = APIRouter()
svc = PlatformService()


class LoadDatasetReq(BaseModel):
    dataset_id: str = "default"
    path: str = "sample_data"


class BacktestReq(BaseModel):
    strategy_id: str
    params: Dict[str, Any] = {}
    execution_model: str = "balanced"
    products: List[str] = []
    days: List[int] = []


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/datasets")
def datasets():
    return svc.datasets()


@router.post("/datasets/load")
def load_dataset(req: LoadDatasetReq):
    try:
        return svc.load_dataset(req.dataset_id, req.path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/products")
def products():
    return svc.products()


@router.get("/days")
def days():
    return svc.days()


@router.get("/snapshots")
def snapshots(product: Optional[str] = None, day: Optional[int] = None, limit: int = 2000):
    return svc.snapshots(product, day, limit)


@router.get("/trades")
def trades(product: Optional[str] = None, day: Optional[int] = None, limit: int = 2000):
    return svc.trades(product, day, limit)


@router.post("/backtest/run")
def backtest_run(req: BacktestReq):
    return svc.run_backtest(req.strategy_id, req.params, req.execution_model, req.products, req.days)


@router.get("/backtest/{run_id}")
def backtest_get(run_id: str):
    run = svc.repo.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


@router.get("/backtest/{run_id}/metrics")
def backtest_metrics(run_id: str):
    run = svc.repo.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run["metrics"]


@router.get("/backtest/{run_id}/trace")
def backtest_trace(run_id: str):
    run = svc.repo.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    p = run["artifacts"].get("trace")
    return FileResponse(p)


@router.post("/strategies/upload")
async def upload_strategy(file: UploadFile = File(...)):
    if not file.filename.endswith(".py"):
        raise HTTPException(400, "Only .py")
    data = await file.read()
    try:
        return svc.upload_strategy(file.filename, data)
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.get("/strategies")
def list_strategies():
    return svc.repo.list_strategies()


@router.get("/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    s = svc.repo.get_strategy(strategy_id)
    if not s:
        raise HTTPException(404, "not found")
    return s


@router.get("/strategies/{strategy_id}/source")
def strategy_source(strategy_id: str):
    s = svc.repo.get_strategy(strategy_id)
    if not s:
        raise HTTPException(404, "not found")
    if s["path"]:
        return {"source": Path(s["path"]).read_text()}
    return {"source": "builtin strategy"}


@router.post("/strategies/{strategy_id}/run")
def strategy_run(strategy_id: str, req: BacktestReq):
    req.strategy_id = strategy_id
    return svc.run_backtest(req.strategy_id, req.params, req.execution_model, req.products, req.days)


@router.post("/runs/compare")
def runs_compare(run_ids: List[str]):
    runs = [svc.repo.get_run(x) for x in run_ids]
    return {"runs": [r for r in runs if r]}


@router.get("/runs")
def runs():
    return svc.repo.list_runs()


@router.get("/runs/{run_id}/artifacts")
def run_artifacts(run_id: str):
    run = svc.repo.get_run(run_id)
    if not run:
        raise HTTPException(404, "not found")
    return run["artifacts"]


@router.get("/runs/{run_id}/export")
def run_export(run_id: str):
    run = svc.repo.get_run(run_id)
    if not run:
        raise HTTPException(404, "not found")
    return run


@router.post("/replay/start")
def replay_start():
    svc.replay.running = True
    return svc.replay.model_dump()


@router.post("/replay/pause")
def replay_pause():
    svc.replay.running = False
    return svc.replay.model_dump()


@router.post("/replay/step")
def replay_step(step: int = 1):
    svc.replay.cursor = max(0, min(svc.replay.total_events - 1, svc.replay.cursor + step))
    return {"cursor": svc.replay.cursor, "event": svc.replay_events[svc.replay.cursor].model_dump() if svc.replay_events else None}


@router.post("/replay/seek")
def replay_seek(timestamp: int):
    idx = 0
    for i, e in enumerate(svc.replay_events):
        if e.timestamp >= timestamp:
            idx = i
            break
    svc.replay.cursor = idx
    return {"cursor": idx}


@router.websocket("/ws/replay")
async def ws_replay(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            if svc.replay_events:
                e = svc.replay_events[svc.replay.cursor]
                await ws.send_text(json.dumps({"session": svc.replay.model_dump(), "event": e.model_dump()}))
                if svc.replay.running:
                    svc.replay.cursor = min(svc.replay.total_events - 1, svc.replay.cursor + 1)
            await ws.receive_text()
    except Exception:
        await ws.close()
