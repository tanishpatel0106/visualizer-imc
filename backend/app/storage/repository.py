from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class Repository:
    def __init__(self, path: str = "backend/app/storage/imc_terminal.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self):
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._conn() as c:
            c.execute("create table if not exists strategies(id text primary key, kind text, name text, path text, meta text)")
            c.execute("create table if not exists runs(id text primary key, strategy_id text, summary text, metrics text, artifacts text)")

    def save_strategy(self, strategy_id: str, kind: str, name: str, path: str, meta: Dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute("insert or replace into strategies(id,kind,name,path,meta) values(?,?,?,?,?)", (strategy_id, kind, name, path, json.dumps(meta)))

    def list_strategies(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("select id,kind,name,path,meta from strategies").fetchall()
        return [{"id": r[0], "kind": r[1], "name": r[2], "path": r[3], "meta": json.loads(r[4] or "{}") } for r in rows]

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("select id,kind,name,path,meta from strategies where id=?", (strategy_id,)).fetchone()
        if not r:
            return None
        return {"id": r[0], "kind": r[1], "name": r[2], "path": r[3], "meta": json.loads(r[4] or "{}")}

    def save_run(self, run_id: str, strategy_id: str, summary: Dict[str, Any], metrics: Dict[str, Any], artifacts: Dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute("insert or replace into runs(id,strategy_id,summary,metrics,artifacts) values(?,?,?,?,?)", (run_id, strategy_id, json.dumps(summary), json.dumps(metrics), json.dumps(artifacts)))

    def list_runs(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute("select id,strategy_id,summary,metrics,artifacts from runs order by rowid desc").fetchall()
        return [{"id": r[0], "strategy_id": r[1], "summary": json.loads(r[2] or "{}"), "metrics": json.loads(r[3] or "{}"), "artifacts": json.loads(r[4] or "{}") } for r in rows]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            r = c.execute("select id,strategy_id,summary,metrics,artifacts from runs where id=?", (run_id,)).fetchone()
        if not r:
            return None
        return {"id": r[0], "strategy_id": r[1], "summary": json.loads(r[2] or "{}"), "metrics": json.loads(r[3] or "{}"), "artifacts": json.loads(r[4] or "{}")}
