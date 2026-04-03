# IMC Prosperity Terminal & Research Platform

Production-style local trading terminal for tutorial-round IMC Prosperity datasets, including replay, backtesting, strategy upload sandboxing, built-in strategy library, debugger/trace, analytics, and exportable artifacts.

## Architecture
- **Backend (FastAPI, Python 3.11+)**
  - Data ingestion + validation (`engines/data`)
  - Visible order book reconstruction (`engines/orderbook`)
  - Execution simulation with conservative/balanced/optimistic models (`engines/execution`)
  - Event-driven backtest + debug trace (`engines/backtest`)
  - Built-in strategy library (`engines/strategies`)
  - Uploaded strategy sandbox (`engines/sandbox`)
  - Analytics + exports (`engines/analytics`, `services/platform_service.py`)
  - SQLite persistence for strategies and runs (`storage/repository.py`)
- **Frontend (React + TS + Vite + Zustand)**
  - Terminal-like dark data-dense workspace
  - Order book ladder panel, trade tape, strategy library, run metrics, trace debugger
  - Keyboard-friendly style and status badges

## Features Implemented
1. **Historical CSV ingestion** with strict schema checks and NaN-tolerant optional depth levels.
2. **Visible top-3 order book reconstruction** + microstructure fields (spread, depth, imbalance, microprice, weighted mid, regimes).
3. **Event stream replay controls** (`/replay/start`, `/replay/pause`, `/replay/step`, `/replay/seek`, `/ws/replay`).
4. **Backtest engine** with aggressive and heuristic passive fills, partial fills, PnL/inventory accounting.
5. **Manual Python strategy upload** (Prosperity-compatible `Trader.run`) with AST-based blocked imports and controlled execution.
6. **Built-in one-click strategy library** across market making, mean reversion, momentum, microstructure, and relative-value templates.
7. **Terminal frontend** with dense workstation panels.
8. **Debugger / trace** frame stream with market state, orders, fills, and PnL progression.
9. **Analytics metrics** (PnL, drawdown, turnover, win rate, Sharpe-like, volatility, inventory stats).
10. **Saved runs + exports** (summary JSON, metrics CSV, fills CSV, trace JSONL).

## Execution Model Assumptions (Snapshot Honesty)
- Data is snapshot-level visible top-of-book/top-3, not full message feed.
- Aggressive crossing fills are guaranteed only up to visible top levels.
- Passive fill behavior is heuristic and explicitly selectable:
  - **Conservative**: immediate crossing only.
  - **Balanced**: touch + trade-supported passive fill logic.
  - **Optimistic**: permissive exploratory passive fill assumptions.
- Queue priority and hidden liquidity are modeled assumptions.

## Run Locally
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open: `http://localhost:5173`

## Load Sample Data
- Included in `sample_data/`.
- UI auto-calls `POST /datasets/load` with path `sample_data`.
- You can load custom tutorial round folders with:
```bash
curl -X POST localhost:8000/datasets/load -H 'Content-Type: application/json' -d '{"dataset_id":"round0","path":"/absolute/path/to/folder"}'
```

## Upload Strategy
- In UI (or API), upload `.py` implementing `class Trader` + `run(state)`.
- Example: `sample_strategies/manual_example.py`.

## Key API Endpoints
`/health`, `/datasets`, `/datasets/load`, `/products`, `/days`, `/snapshots`, `/trades`, `/replay/*`, `/backtest/run`, `/backtest/{id}`, `/backtest/{id}/metrics`, `/backtest/{id}/trace`, `/strategies/upload`, `/strategies`, `/strategies/{id}`, `/strategies/{id}/source`, `/strategies/{id}/run`, `/runs/compare`, `/runs`, `/runs/{id}/artifacts`, `/runs/{id}/export`.

## Extending
- Add adapters in `engines/data` for additional rounds/feeds.
- Add strategies by extending `engines/strategies` registry.
- Add microstructure metrics in `engines/orderbook` + `engines/analytics`.
- Add execution realism knobs in `engines/execution`.

## Limitations
- Passive fill and aggressor inference are heuristic under snapshot data constraints.
- Full-depth queue dynamics and hidden liquidity are not directly observable.
