"""Concurrent HTTP checks and persisted availability history."""
from __future__ import annotations

import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    expected_status: int = 200
    timeout: float = 5.0


@dataclass(frozen=True)
class Result:
    name: str
    url: str
    timestamp: str
    ok: bool
    status: int | None
    latency_ms: float
    error: str | None = None


def read_targets(path: str | Path) -> list[Target]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("targets"), list):
        raise ValueError("Config must contain a 'targets' list")
    targets: list[Target] = []
    for entry in data["targets"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str) or not isinstance(entry.get("url"), str):
            raise ValueError("Each target needs string 'name' and 'url'")
        url = entry["url"]
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"Invalid HTTP URL for {entry['name']}")
        timeout = float(entry.get("timeout", 5.0))
        status = int(entry.get("expected_status", 200))
        if not (0 < timeout <= 120) or not (100 <= status <= 599):
            raise ValueError("timeout must be between 0 and 120; status between 100 and 599")
        targets.append(Target(entry["name"], url, status, timeout))
    if not targets:
        raise ValueError("At least one target is required")
    return targets


def check(target: Target) -> Result:
    start = time.perf_counter()
    status = None
    error = None
    try:
        request = Request(target.url, method="GET", headers={"User-Agent": "uptime-sentinel/0.1"})
        with urlopen(request, timeout=target.timeout) as response:
            status = response.status
    except HTTPError as exc:
        status = exc.code
        error = str(exc)
        exc.close()
    except (URLError, TimeoutError, OSError) as exc:
        error = str(exc)
    return Result(
        name=target.name,
        url=target.url,
        timestamp=datetime.now(timezone.utc).isoformat(),
        ok=status == target.expected_status,
        status=status,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
        error=error if status != target.expected_status else None,
    )


def check_all(targets: list[Target], max_workers: int = 5) -> list[Result]:
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(targets)))) as pool:
        return list(pool.map(check, targets))


def initialize_db(db_path: str | Path) -> None:
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            ok INTEGER NOT NULL,
            status INTEGER,
            latency_ms REAL NOT NULL,
            error TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_checks_name_timestamp ON checks(name, timestamp)")


def save_results(db_path: str | Path, results: list[Result]) -> None:
    initialize_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.executemany(
            "INSERT INTO checks (timestamp, name, url, ok, status, latency_ms, error) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r.timestamp, r.name, r.url, int(r.ok), r.status, r.latency_ms, r.error) for r in results],
        )


def summarize(db_path: str | Path) -> list[dict]:
    initialize_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        rows = conn.execute("""SELECT name, COUNT(*), SUM(ok), ROUND(AVG(latency_ms), 2)
                              FROM checks GROUP BY name ORDER BY name""").fetchall()
    return [{"name": name, "checks": total, "successes": successes,
             "uptime_percent": round(successes * 100 / total, 2), "avg_latency_ms": latency}
            for name, total, successes, latency in rows]
