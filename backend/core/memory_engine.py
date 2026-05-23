"""
memory_engine.py — Persistent Memory Layer for the Adaptive Intelligence System
Wraps SQLite for all prediction, outcome, setup stats, and weight storage.
Maintains a RAM cache of recent predictions for fast read access.
"""
import sqlite3
import json
import logging
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# ── Database location ─────────────────────────────────────────────────────────
_DB_PATH = Path(__file__).parent.parent / "data" / "adaptive_memory.db"

# ── Default adaptive weights ──────────────────────────────────────────────────
DEFAULT_WEIGHTS: Dict[str, float] = {
    "TA_WEIGHT":           0.70,
    "NEWS_WEIGHT":         0.30,
    "RSI_MULTIPLIER":      1.00,
    "MACD_MULTIPLIER":     1.00,
    "EMA_MULTIPLIER":      1.00,
    "MOMENTUM_MULTIPLIER": 1.00,
    "BB_MULTIPLIER":       1.00,
}

# Weight bounds — we never allow weights to drift beyond these limits
WEIGHT_BOUNDS: Dict[str, tuple] = {
    "TA_WEIGHT":           (0.55, 0.85),
    "NEWS_WEIGHT":         (0.15, 0.45),
    "RSI_MULTIPLIER":      (0.50, 1.50),
    "MACD_MULTIPLIER":     (0.50, 1.50),
    "EMA_MULTIPLIER":      (0.50, 1.50),
    "MOMENTUM_MULTIPLIER": (0.50, 1.50),
    "BB_MULTIPLIER":       (0.50, 1.50),
}


class MemoryEngine:
    """
    Thread-safe SQLite wrapper with an in-memory prediction cache.
    All DB operations are protected by a single re-entrant lock.
    """

    def __init__(self, db_path: Path = _DB_PATH, ram_cache_size: int = 200):
        self._db_path = db_path
        self._lock = threading.RLock()
        self._ram_cache: deque = deque(maxlen=ram_cache_size)  # most recent predictions
        self._weights_cache: Dict[str, float] = {}             # key → current value

        self._init_db()
        self._seed_default_weights()
        self._reload_weights_cache()
        logger.info(f"[MemoryEngine] Initialized. DB at {self._db_path}")

    # ── Schema initialisation ─────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with self._get_conn() as conn:
                conn.executescript("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol              TEXT NOT NULL,
                    timestamp           TEXT NOT NULL,
                    bias                TEXT NOT NULL,
                    confidence_score    REAL NOT NULL,
                    technical_score     REAL NOT NULL,
                    news_score          REAL NOT NULL,
                    rsi_value           REAL,
                    macd_signal         TEXT,
                    ema_trend           TEXT,
                    momentum_signal     TEXT,
                    bb_signal           TEXT,
                    market_regime       TEXT,
                    atr_pct             REAL,
                    price_at_prediction REAL NOT NULL,
                    active_setups       TEXT DEFAULT '[]'
                );

                CREATE INDEX IF NOT EXISTS idx_predictions_symbol
                    ON predictions(symbol);
                CREATE INDEX IF NOT EXISTS idx_predictions_timestamp
                    ON predictions(timestamp);

                CREATE TABLE IF NOT EXISTS outcomes (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id     INTEGER NOT NULL REFERENCES predictions(id),
                    horizon           TEXT NOT NULL,
                    price_at_outcome  REAL NOT NULL,
                    price_change_pct  REAL NOT NULL,
                    outcome           TEXT NOT NULL,
                    evaluated_at      TEXT NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_outcomes_unique
                    ON outcomes(prediction_id, horizon);

                CREATE TABLE IF NOT EXISTS setup_stats (
                    setup_name        TEXT NOT NULL,
                    symbol            TEXT NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    correct_count     INTEGER DEFAULT 0,
                    incorrect_count   INTEGER DEFAULT 0,
                    neutral_count     INTEGER DEFAULT 0,
                    win_rate          REAL DEFAULT 0.0,
                    avg_return_pct    REAL DEFAULT 0.0,
                    last_updated      TEXT,
                    PRIMARY KEY (setup_name, symbol)
                );

                CREATE TABLE IF NOT EXISTS adaptive_weights (
                    weight_key    TEXT NOT NULL,
                    symbol        TEXT NOT NULL DEFAULT 'GLOBAL',
                    value         REAL NOT NULL,
                    default_value REAL NOT NULL,
                    last_updated  TEXT,
                    PRIMARY KEY (weight_key, symbol)
                );

                CREATE TABLE IF NOT EXISTS weight_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    weight_key  TEXT NOT NULL,
                    symbol      TEXT NOT NULL,
                    old_value   REAL NOT NULL,
                    new_value   REAL NOT NULL,
                    reason      TEXT NOT NULL,
                    changed_at  TEXT NOT NULL
                );
                """)
        logger.info("[MemoryEngine] Schema initialised.")

    def _seed_default_weights(self):
        """Insert default weights only if the table is empty."""
        with self._lock:
            with self._get_conn() as conn:
                for key, val in DEFAULT_WEIGHTS.items():
                    conn.execute("""
                        INSERT OR IGNORE INTO adaptive_weights
                            (weight_key, symbol, value, default_value, last_updated)
                        VALUES (?, 'GLOBAL', ?, ?, ?)
                    """, (key, val, val, datetime.now(timezone.utc).isoformat()))

    def _reload_weights_cache(self):
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT weight_key, value FROM adaptive_weights WHERE symbol='GLOBAL'"
                ).fetchall()
                self._weights_cache = {r["weight_key"]: r["value"] for r in rows}

    # ── Prediction storage ────────────────────────────────────────────────────

    def store_prediction(self, snapshot: dict) -> int:
        """
        Persist a prediction snapshot.  Returns the new row id.
        snapshot must include all columns from the predictions table.
        """
        with self._lock:
            with self._get_conn() as conn:
                cur = conn.execute("""
                    INSERT INTO predictions
                        (symbol, timestamp, bias, confidence_score, technical_score,
                         news_score, rsi_value, macd_signal, ema_trend,
                         momentum_signal, bb_signal, market_regime, atr_pct,
                         price_at_prediction, active_setups)
                    VALUES
                        (:symbol, :timestamp, :bias, :confidence_score, :technical_score,
                         :news_score, :rsi_value, :macd_signal, :ema_trend,
                         :momentum_signal, :bb_signal, :market_regime, :atr_pct,
                         :price_at_prediction, :active_setups)
                """, snapshot)
                row_id = cur.lastrowid
                snapshot["id"] = row_id
                self._ram_cache.append(snapshot)
                return row_id

    def get_predictions(self, symbol: str, limit: int = 20) -> List[dict]:
        """Return the most recent N predictions for a symbol."""
        with self._lock:
            # Try RAM cache first
            cached = [p for p in reversed(self._ram_cache) if p.get("symbol") == symbol]
            if len(cached) >= limit:
                return cached[:limit]

            # Fallback to DB
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM predictions
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (symbol, limit)).fetchall()
                return [self._row_to_dict(r) for r in rows]

    def get_pending_evaluations(self, horizon_seconds: int) -> List[dict]:
        """
        Return predictions that:
        - were made >= horizon_seconds ago
        - do NOT yet have an outcomes row for this horizon label
        """
        horizon_label = self._seconds_to_label(horizon_seconds)
        cutoff = datetime.now(timezone.utc).timestamp() - horizon_seconds
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT p.* FROM predictions p
                    WHERE datetime(p.timestamp) <= datetime(?, 'unixepoch')
                      AND NOT EXISTS (
                          SELECT 1 FROM outcomes o
                          WHERE o.prediction_id = p.id
                            AND o.horizon = ?
                      )
                    ORDER BY p.timestamp ASC
                    LIMIT 100
                """, (cutoff, horizon_label)).fetchall()
                return [self._row_to_dict(r) for r in rows]

    @staticmethod
    def _seconds_to_label(seconds: int) -> str:
        mapping = {900: "15m", 3600: "1h", 14400: "4h"}
        return mapping.get(seconds, f"{seconds}s")

    # ── Outcome storage ───────────────────────────────────────────────────────

    def store_outcome(self, outcome: dict) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO outcomes
                        (prediction_id, horizon, price_at_outcome,
                         price_change_pct, outcome, evaluated_at)
                    VALUES
                        (:prediction_id, :horizon, :price_at_outcome,
                         :price_change_pct, :outcome, :evaluated_at)
                """, outcome)

    def get_outcomes(self, symbol: str, limit: int = 50) -> List[dict]:
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT o.* FROM outcomes o
                    JOIN predictions p ON p.id = o.prediction_id
                    WHERE p.symbol = ?
                    ORDER BY o.evaluated_at DESC
                    LIMIT ?
                """, (symbol, limit)).fetchall()
                return [self._row_to_dict(r) for r in rows]

    # ── Setup stats ───────────────────────────────────────────────────────────

    def upsert_setup_stats(self, stats: dict) -> None:
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO setup_stats
                        (setup_name, symbol, total_predictions, correct_count,
                         incorrect_count, neutral_count, win_rate,
                         avg_return_pct, last_updated)
                    VALUES
                        (:setup_name, :symbol, :total_predictions, :correct_count,
                         :incorrect_count, :neutral_count, :win_rate,
                         :avg_return_pct, :last_updated)
                    ON CONFLICT(setup_name, symbol) DO UPDATE SET
                        total_predictions = excluded.total_predictions,
                        correct_count     = excluded.correct_count,
                        incorrect_count   = excluded.incorrect_count,
                        neutral_count     = excluded.neutral_count,
                        win_rate          = excluded.win_rate,
                        avg_return_pct    = excluded.avg_return_pct,
                        last_updated      = excluded.last_updated
                """, stats)

    def get_setup_stats(self, symbol: str = "GLOBAL") -> List[dict]:
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT * FROM setup_stats WHERE symbol = ?
                    ORDER BY win_rate DESC
                """, (symbol,)).fetchall()
                return [self._row_to_dict(r) for r in rows]

    def get_outcomes_for_setup(self, setup_name: str, symbol: str) -> List[dict]:
        """Fetch all evaluated outcomes for predictions that had a specific setup tag."""
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT o.price_change_pct, o.outcome FROM outcomes o
                    JOIN predictions p ON p.id = o.prediction_id
                    WHERE p.symbol = ?
                      AND json_each.value = ?
                      AND o.horizon = '1h'
                    FROM json_each(p.active_setups)
                """, (symbol, setup_name)).fetchall()
                # SQLite json_each syntax workaround:
                return [self._row_to_dict(r) for r in rows]

    def get_raw_outcomes_for_symbol(self, symbol: str, horizon: str = "1h") -> List[dict]:
        """Return all evaluated 1h outcomes joined with their prediction's setup list."""
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT p.active_setups, p.bias, o.price_change_pct, o.outcome
                    FROM outcomes o
                    JOIN predictions p ON p.id = o.prediction_id
                    WHERE p.symbol = ? AND o.horizon = ?
                    ORDER BY o.evaluated_at DESC
                """, (symbol, horizon)).fetchall()
                return [self._row_to_dict(r) for r in rows]

    # ── Adaptive weights ──────────────────────────────────────────────────────

    def get_weight(self, key: str, symbol: str = "GLOBAL") -> float:
        """Fast read from RAM cache; fallback to DB if not cached."""
        if symbol == "GLOBAL" and key in self._weights_cache:
            return self._weights_cache[key]
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT value FROM adaptive_weights WHERE weight_key=? AND symbol=?",
                    (key, symbol)
                ).fetchone()
                return row["value"] if row else DEFAULT_WEIGHTS.get(key, 1.0)

    def set_weight(self, key: str, new_value: float, reason: str, symbol: str = "GLOBAL") -> None:
        lo, hi = WEIGHT_BOUNDS.get(key, (0.1, 2.0))
        new_value = max(lo, min(hi, new_value))
        old_value = self.get_weight(key, symbol)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    UPDATE adaptive_weights SET value=?, last_updated=?
                    WHERE weight_key=? AND symbol=?
                """, (new_value, now, key, symbol))
                conn.execute("""
                    INSERT INTO weight_history
                        (weight_key, symbol, old_value, new_value, reason, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (key, symbol, old_value, new_value, reason, now))
            # Update RAM cache
            if symbol == "GLOBAL":
                self._weights_cache[key] = new_value
        logger.info(f"[MemoryEngine] Weight '{key}' updated: {old_value:.3f} → {new_value:.3f} ({reason})")

    def get_all_weights(self) -> List[dict]:
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute("SELECT * FROM adaptive_weights ORDER BY weight_key").fetchall()
                return [self._row_to_dict(r) for r in rows]

    def get_weight_history(self, limit: int = 20) -> List[dict]:
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM weight_history ORDER BY changed_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
                return [self._row_to_dict(r) for r in rows]

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        # Deserialize JSON fields
        if "active_setups" in d and isinstance(d["active_setups"], str):
            try:
                d["active_setups"] = json.loads(d["active_setups"])
            except Exception:
                d["active_setups"] = []
        return d

    def count_predictions(self, symbol: str) -> int:
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM predictions WHERE symbol=?", (symbol,)
                ).fetchone()
                return row["cnt"] if row else 0


# Module-level singleton
memory_engine = MemoryEngine()
