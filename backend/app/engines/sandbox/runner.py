from __future__ import annotations

import ast
import traceback
from pathlib import Path
from typing import Any, Dict, List

BLOCKED_IMPORTS = {"os", "subprocess", "socket", "pathlib", "requests", "httpx", "urllib"}


class StrategySandboxError(Exception):
    pass


class StrategySandbox:
    def validate(self, code: str) -> None:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name.split(".")[0] in BLOCKED_IMPORTS:
                        raise StrategySandboxError(f"Blocked import: {n.name}")
            if isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in BLOCKED_IMPORTS:
                    raise StrategySandboxError(f"Blocked import: {node.module}")
        if "class Trader" not in code:
            raise StrategySandboxError("Strategy must define class Trader")

    def load(self, path: Path):
        code = path.read_text()
        self.validate(code)
        g: Dict[str, Any] = {"__builtins__": {"abs": abs, "min": min, "max": max, "sum": sum, "len": len, "range": range, "float": float, "int": int, "dict": dict, "list": list}}
        l: Dict[str, Any] = {}
        try:
            exec(compile(code, str(path), "exec"), g, l)
        except Exception as exc:
            raise StrategySandboxError(f"Strategy compile error: {exc}")
        trader_cls = l.get("Trader") or g.get("Trader")
        if trader_cls is None:
            raise StrategySandboxError("Trader class missing")
        return trader_cls()

    def run(self, trader: Any, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = trader.run(state)
            if not isinstance(result, tuple) or len(result) != 3:
                raise StrategySandboxError("Trader.run must return (orders, conversions, trader_data)")
            orders, conversions, trader_data = result
            return {"orders": orders, "conversions": conversions, "trader_data": trader_data}
        except Exception:
            raise StrategySandboxError(traceback.format_exc())
