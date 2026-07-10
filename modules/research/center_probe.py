"""modules/research/center_probe.py — center-of-box direction-discovery probe.

Brock 2026-07-10: fire (LOG-ONLY, never trades) whenever price sits at the
center of the previous-session box with enough room for a ratchet to lock the
minimum. Record the FULL indicator vector with NO direction commitment. The
scorer (research/tools/center_probe_score.py) later mines: does any indicator
predict which wall the wave rides to? If yes → a which-way filter is born, and
this becomes a real two-sided center-out setup. If no → the market keeps its
secret and we've proven it honestly.
"""
from __future__ import annotations
import json, logging, threading
from pathlib import Path

log = logging.getLogger("v5.center_probe")
_LOG  = Path(__file__).resolve().parent.parent.parent / "data" / "center_probe_log.jsonl"
_LOCK = threading.Lock()
_last: dict = {}
_GAP_S   = 1800     # one observation per cell per 30 min
_MIN_BOX = 16.0     # box half-width >= 8p → room for the 5-6p lock (Brock's constraint)
_CTR_LO, _CTR_HI = 0.42, 0.58

_FEATURES = ["atr_5m","atr_1h","atr_conc","atr_h1_relative","rvol_5bar","rvol_12bar",
             "range_5bar","range_12bar","bb_pos","bb_width","zscore_5m","willr_m5",
             "rsi14","rsi_slope","ema20_dist_pct","ema5_dist_pips","ema50_dist_pct",
             "ema_cross_pips","ret_5m","ret_15m","ret_30m","ret_1h","h1_ret_1bar",
             "h1_ret_4bar","htf_pct_20","htf_pct_60","close_pos_daily","adr_consumed",
             "d_ret","kc_up_dist_pips","vortex_diff_h1","trend_4h","aroonosc_h1",
             "pdh_dist","pdl_dist","ps_high_dist","ps_low_dist","ps_pos"]

def observe(views, now) -> None:
    """Called each scan cycle. Appends a full-feature observation per qualifying
    cell. Log-only — this function never returns intents and never trades."""
    for v in views:
        try:
            box = float(getattr(v, "ps_low_dist", 0.0)) - float(getattr(v, "ps_high_dist", 0.0))
            pos = float(getattr(v, "ps_pos", 0.5))
            if box < _MIN_BOX or not (_CTR_LO <= pos <= _CTR_HI):
                continue
            key = (v.pair, v.session)
            t = now.timestamp()
            if t - _last.get(key, 0.0) < _GAP_S:
                continue
            _last[key] = t
            bid = float(getattr(v, "bid", 0.0)); ask = float(getattr(v, "ask", 0.0))
            rec = {"ts": now.isoformat(), "pair": v.pair, "session": v.session,
                   "mid": round((bid + ask) / 2.0, 5) if bid and ask else None,
                   "box": round(box, 1)}
            for f in _FEATURES:
                val = getattr(v, f, None)
                rec[f] = round(float(val), 5) if isinstance(val, (int, float)) else None
            with _LOCK:
                _LOG.parent.mkdir(exist_ok=True)
                with open(_LOG, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
        except Exception as exc:
            log.warning("center_probe observe failed %s: %s", getattr(v, "pair", "?"), exc)
