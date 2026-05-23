"""
risk_engine.py — Recurring Market Event Calendar + Risk Penalty System
No external API required. Uses a hardcoded weekly schedule of known high-impact events.
Penalties are applied to reduce confidence when a trade would coincide with event risk.
"""
import logging
from datetime import datetime, timezone, time as dt_time, timedelta
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# ── Timezone helpers ───────────────────────────────────────────────────────────
UTC   = timezone.utc
IST   = ZoneInfo("Asia/Kolkata")
US_ET = ZoneInfo("America/New_York")

# ── Weekday constants ──────────────────────────────────────────────────────────
MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4


class RecurringEvent:
    """Defines a recurring weekly market event."""
    __slots__ = ("name", "weekdays", "utc_hour", "utc_minute",
                 "duration_minutes", "impact", "penalty", "advisory",
                 "relevant_symbols")

    def __init__(
        self,
        name: str,
        weekdays: List[int],
        utc_hour: int,
        utc_minute: int,
        impact: str,
        penalty: float,
        advisory: str,
        relevant_symbols: Optional[List[str]] = None,
        duration_minutes: int = 60,
    ):
        self.name             = name
        self.weekdays         = weekdays
        self.utc_hour         = utc_hour
        self.utc_minute       = utc_minute
        self.duration_minutes = duration_minutes
        self.impact           = impact
        self.penalty          = penalty
        self.advisory         = advisory
        self.relevant_symbols = relevant_symbols or []   # empty = applies to ALL


# ── Event calendar ─────────────────────────────────────────────────────────────

_EVENTS: List[RecurringEvent] = [

    # ── Energy / Commodity reports ─────────────────────────────────────────────
    RecurringEvent(
        name="EIA Crude Oil Inventory Report",
        weekdays=[WED], utc_hour=14, utc_minute=30,
        impact="HIGH", penalty=-8.0, duration_minutes=90,
        relevant_symbols=["CL=F", "BZ=F"],
        advisory="Crude inventory surprise can cause 2–3% move. Avoid new positions 30 min before."
    ),
    RecurringEvent(
        name="EIA Natural Gas Storage Report",
        weekdays=[THU], utc_hour=14, utc_minute=30,
        impact="HIGH", penalty=-8.0, duration_minutes=90,
        relevant_symbols=["NG=F"],
        advisory="Gas storage report often triggers sharp 3–5% moves. Avoid pre-report entries."
    ),
    RecurringEvent(
        name="API Crude Oil Inventory (Unofficial)",
        weekdays=[TUE], utc_hour=20, utc_minute=30,
        impact="MEDIUM", penalty=-4.0, duration_minutes=60,
        relevant_symbols=["CL=F", "BZ=F"],
        advisory="API data published after market hours. May gap next open."
    ),

    # ── US Market sessions ─────────────────────────────────────────────────────
    RecurringEvent(
        name="US Market Open Volatility Window",
        weekdays=[MON, TUE, WED, THU, FRI], utc_hour=13, utc_minute=30,
        impact="MEDIUM", penalty=-4.0, duration_minutes=30,
        advisory="Opening 30 min often has erratic price action. Wait for direction to establish."
    ),
    RecurringEvent(
        name="US Market Power Hour",
        weekdays=[MON, TUE, WED, THU, FRI], utc_hour=19, utc_minute=30,
        impact="LOW", penalty=-2.0, duration_minutes=60,
        advisory="Last hour of US session can see position squaring and trend acceleration."
    ),

    # ── NSE sessions ──────────────────────────────────────────────────────────
    RecurringEvent(
        name="NSE Market Open (India)",
        weekdays=[MON, TUE, WED, THU, FRI], utc_hour=3, utc_minute=45,
        impact="MEDIUM", penalty=-4.0, duration_minutes=30,
        relevant_symbols=["^NSEI", "^NSEBANK", "^BSESN", "^CNXPHARMA", "^CNXFMCG"],
        advisory="Indian market open (09:15 IST). First 15 min often volatile. Wait for clarity."
    ),
    RecurringEvent(
        name="NSE Weekly F&O Expiry",
        weekdays=[THU], utc_hour=4, utc_minute=0,
        impact="HIGH", penalty=-7.0, duration_minutes=360,  # Full session impact
        relevant_symbols=["^NSEI", "^NSEBANK"],
        advisory="F&O expiry Thursday — max pain pinning, gamma exposure, and high intraday swings."
    ),
    RecurringEvent(
        name="NSE Monthly F&O Expiry (Last Thursday of Month)",
        weekdays=[THU], utc_hour=4, utc_minute=0,
        impact="HIGH", penalty=-9.0, duration_minutes=420,
        relevant_symbols=["^NSEI", "^NSEBANK"],
        advisory="Monthly F&O expiry. Institutional rollovers cause heightened volatility all day."
    ),

    # ── Macro / Global events ──────────────────────────────────────────────────
    RecurringEvent(
        name="US Non-Farm Payrolls (First Friday)",
        weekdays=[FRI], utc_hour=12, utc_minute=30,
        impact="HIGH", penalty=-8.0, duration_minutes=120,
        advisory="NFP release. All risk assets can move 1–2% on surprise. Avoid pre-report exposure."
    ),
    RecurringEvent(
        name="US CPI Data Release",
        weekdays=[WED], utc_hour=12, utc_minute=30,
        impact="HIGH", penalty=-7.0, duration_minutes=90,
        advisory="CPI print affects rate expectations. Gold, crude, and equities all react sharply."
    ),
    RecurringEvent(
        name="Gold / Silver London Fix",
        weekdays=[MON, TUE, WED, THU, FRI], utc_hour=14, utc_minute=0,
        impact="LOW", penalty=-2.0, duration_minutes=15,
        relevant_symbols=["GC=F", "SI=F"],
        advisory="London PM gold fix at 15:00 BST. Minor benchmark-related moves possible."
    ),
]


class RiskEngine:
    """
    Checks the current UTC time against the recurring event schedule.
    Returns a list of upcoming/active risk events affecting the given symbol.
    """

    # Window in minutes — events within this window are flagged
    LOOKAHEAD_MINUTES = 120

    def get_risk_events(
        self,
        symbol: str,
        now: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Return a list of risk events relevant to `symbol` within the lookahead window.
        Also returns the total penalty to subtract from confidence.
        """
        if now is None:
            now = datetime.now(UTC)

        current_weekday = now.weekday()
        active_events   = []
        total_penalty   = 0.0

        for ev in _EVENTS:
            # Filter by symbol relevance
            if ev.relevant_symbols and symbol not in ev.relevant_symbols:
                continue

            # Check if this event occurs on today's weekday
            if current_weekday not in ev.weekdays:
                continue

            # Compute event time today in UTC
            event_time_today = now.replace(
                hour=ev.utc_hour, minute=ev.utc_minute,
                second=0, microsecond=0
            )
            minutes_away = (event_time_today - now).total_seconds() / 60

            # Check if event is active (within lookahead window ahead, or just started)
            event_end = event_time_today + timedelta(minutes=ev.duration_minutes)
            if -ev.duration_minutes < minutes_away <= self.LOOKAHEAD_MINUTES:
                active_events.append({
                    "event":       ev.name,
                    "minutes_away": int(minutes_away),
                    "impact":      ev.impact,
                    "penalty":     ev.penalty,
                    "advisory":    ev.advisory,
                })
                total_penalty += ev.penalty

        # Sort by proximity
        active_events.sort(key=lambda x: x["minutes_away"])

        # Cap total penalty at -20
        total_penalty = max(-20.0, total_penalty)

        return {
            "events":        active_events,
            "total_penalty": round(total_penalty, 1),
            "has_high_impact": any(e["impact"] == "HIGH" for e in active_events),
            "nearest_event_minutes": active_events[0]["minutes_away"] if active_events else None,
        }

    def get_event_penalty(self, symbol: str, now: Optional[datetime] = None) -> float:
        """Convenience method: return just the total penalty float."""
        return self.get_risk_events(symbol, now)["total_penalty"]


risk_engine = RiskEngine()
