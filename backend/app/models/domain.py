from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    BOOK_SNAPSHOT = "BOOK_SNAPSHOT"
    TRADE_PRINT = "TRADE_PRINT"
    STRATEGY_SUBMIT = "STRATEGY_SUBMIT"
    STRATEGY_CANCEL = "STRATEGY_CANCEL"
    FILL = "FILL"
    REJECT = "REJECT"
    TIMER_TICK = "TIMER_TICK"
    REPLAY_START = "REPLAY_START"
    REPLAY_PAUSE = "REPLAY_PAUSE"
    REPLAY_STEP = "REPLAY_STEP"
    REPLAY_SEEK = "REPLAY_SEEK"
    RUN_COMPLETE = "RUN_COMPLETE"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class BookLevel(BaseModel):
    price: float
    volume: float


class VisibleOrderBook(BaseModel):
    product: str
    timestamp: int
    day: int
    bids: List[BookLevel] = Field(default_factory=list)
    asks: List[BookLevel] = Field(default_factory=list)
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    mid_price: Optional[float] = None
    weighted_mid: Optional[float] = None
    microprice: Optional[float] = None
    bid_depth: float = 0.0
    ask_depth: float = 0.0
    top_imbalance: float = 0.0
    top3_imbalance: float = 0.0
    book_pressure: float = 0.0
    depth_skew: float = 0.0
    spread_regime: str = "UNKNOWN"


class TradePrint(BaseModel):
    timestamp: int
    day: int
    symbol: str
    price: float
    quantity: float
    buyer: str = ""
    seller: str = ""
    aggressor: str = "UNKNOWN"


class MarketSnapshot(BaseModel):
    day: int
    timestamp: int
    product: str
    book: VisibleOrderBook


class Event(BaseModel):
    event_type: EventType
    timestamp: int
    day: int
    product: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class StrategyOrder(BaseModel):
    order_id: str
    product: str
    side: OrderSide
    order_type: OrderType = OrderType.LIMIT
    price: float
    quantity: float
    timestamp: int
    status: OrderStatus = OrderStatus.OPEN
    filled_quantity: float = 0.0


class FillEvent(BaseModel):
    order_id: str
    product: str
    side: OrderSide
    price: float
    quantity: float
    timestamp: int
    passive: bool = False


class PositionState(BaseModel):
    product: str
    quantity: float = 0.0
    avg_price: float = 0.0


class PnLState(BaseModel):
    realized: float = 0.0
    unrealized: float = 0.0
    total: float = 0.0


class DebugFrame(BaseModel):
    timestamp: int
    day: int
    product: str
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    spread: Optional[float] = None
    imbalance: float = 0.0
    position: float = 0.0
    inventory: Dict[str, float] = Field(default_factory=dict)
    strategy_inputs: Dict[str, Any] = Field(default_factory=dict)
    strategy_outputs: Dict[str, Any] = Field(default_factory=dict)
    fills: List[FillEvent] = Field(default_factory=list)
    pnl_total: float = 0.0
    notes: List[str] = Field(default_factory=list)


class BacktestRun(BaseModel):
    run_id: str
    strategy_id: str
    execution_model: str
    products: List[str]
    days: List[int]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    debug_trace: List[DebugFrame] = Field(default_factory=list)
    fills: List[FillEvent] = Field(default_factory=list)


class StrategyParameter(BaseModel):
    name: str
    type: str
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    options: Optional[List[str]] = None
    tooltip: str = ""


class StrategyDefinition(BaseModel):
    strategy_id: str
    name: str
    category: str
    description: str
    parameters: List[StrategyParameter]
    source_code: str = ""


class RunArtifact(BaseModel):
    run_id: str
    summary_path: str
    metrics_csv_path: str
    fills_csv_path: str
    trace_jsonl_path: str


class ReplaySession(BaseModel):
    session_id: str
    running: bool = False
    speed: float = 1.0
    cursor: int = 0
    total_events: int = 0
