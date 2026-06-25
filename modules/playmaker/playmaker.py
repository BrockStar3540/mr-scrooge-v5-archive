"""modules/playmaker/playmaker.py — Selects the best trade from active pair tickets.

The playmaker receives one PairTicket per active pair (already stamped by direction
and momentum modules) and picks the highest-quality setup to fire.

CERTAINTY FLOORS — derived from dm_04 raw factor sweep (not exit-management calibrated):

  MIN_DIRECTION_SCORE = 0.25
    The direction module emits "block" at |score| < 0.15.  Score 0.15–0.25 is
    technically non-block but directionally weak (D6-D7 territory on primary
    indicator with poor supporting signal).  0.25+ means the weighted factor
    composite is committed to a side with meaningful conviction.

  MIN_DIR_CERTAINTY = 0.30
    Certainty = factor_extremity × (0.4 + 0.6 × agreement).
    From dm_04: h1_ret_1bar at D9 (norm≈0.85) + 4 supporting factors at D7
    (norm≈0.45) → certainty ≈ 0.30.  Below that, the signal is not consistently
    above the noise floor established by the sweep.  The is_actionable property
    in PairTicket already gates on certainty > 0.25; this adds the stricter
    playmaker-level bar.

  MIN_MOM_CERTAINTY = 0.25
    Momentum certainty 0.25 = ATR is at least 25% of the way from the center of
    the normal regime toward a boundary (low/normal or normal/high).  Below 0.25
    the vol regime is ambiguous and expected_pips estimates are unreliable.

BEST-EDGE PRIORITY when multiple pairs pass all gates simultaneously:
  Primary rank:   abs(composite_score) = abs(direction.score) × dir_certainty × mom_certainty
  Secondary rank: expected_pips        — higher-magnitude setup wins on ties
  This means a moderately strong signal with high dual-certainty beats a raw
  signal with middling certainties, which is the correct preference.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..signals.base import PairTicket
from config.pairs import PAIR_SESSIONS



# ── Live config (PLAYMAKER tab) ──────────────────────────────────────────────
import json as _json
from pathlib import Path as _Path
_PM_CONFIG_PATH = _Path(__file__).resolve().parents[2] / "config" / "playmaker_config.json"
_PM_DEFAULTS = {
    "enabled":             True,
    "min_direction_score": 0.25,
    "min_dir_certainty":   0.30,
    "min_mom_certainty":   0.25,
    "cooldown_after_sl_min": 0.0,
}
_PM_ACCT_DEFAULTS = {
    "margin_pct_per_trade":  0.005,   # fraction of BALANCE used as margin per trade
    "max_concurrent_trades": 3,
}

def _pm_load() -> dict:
    """Return {"account":..., "defaults":..., "per_pair":..., "disabled_cells":...} with safe fallbacks."""
    try:
        raw = _json.loads(_PM_CONFIG_PATH.read_text())
        acct = dict(raw.get("account") or {})
        if "margin_pct_per_trade" not in acct and "risk_pct_per_trade" in acct:
            acct["margin_pct_per_trade"] = acct.pop("risk_pct_per_trade")
        # disabled_cells: list of [pair, session, direction] triples → frozenset of tuples
        dc_raw = raw.get("disabled_cells") or []
        dc = frozenset(tuple(x) for x in dc_raw if len(x) == 3)
        # inverted_shadow_cells: list of [pair, session] pairs → frozenset of tuples
        isc_raw = raw.get("inverted_shadow_cells") or []
        isc = frozenset(tuple(x) for x in isc_raw if len(x) == 2)
        # inverted_live_cells: list of [pair, session] pairs → frozenset of tuples
        # When the winning ticket's (pair, session) is in this set, the trade direction
        # is FLIPPED before execution (long signal → short trade, short signal → long).
        ilc_raw = raw.get("inverted_live_cells") or []
        ilc = frozenset(tuple(x) for x in ilc_raw if len(x) == 2)
        # random_pick: when True, pick_best randomizes among actionable candidates
        # instead of ranking by |composite_score|. Used to spread fire rate across
        # cells while we collect per-cycle ticket data to evaluate alternative rankings.
        random_pick = bool(raw.get("random_pick", False))
        # per_cell_mom_cert_max: dict of "pair/session" -> float CEILING on m_cert.
        # Brock reframe 2026-06-23: low m_cert predicts BIG directional moves; high
        # m_cert predicts small contained moves. For cells whose edge IS the big-move
        # tail, block trades where m_cert exceeds the ceiling (keep only big-move setups).
        # First use: AUD_JPY/asia ceiling 0.50 (5 of 6 trades there had m_cert <= 0.50,
        # and the inverted-mistake losses showed low m_cert + big move dynamic).
        pcmm_raw = raw.get("per_cell_mom_cert_max") or {}
        per_cell_mom_cert_max = {tuple(k.split("/")): float(v) for k, v in pcmm_raw.items()
                                  if "/" in k and len(k.split("/")) == 2}
        # per_cell_mom_cert_min: dict of "pair/session" -> float FLOOR on m_cert.
        # Mirror of the ceiling. Used for cells where the OPPOSITE pattern holds:
        # high m_cert → big MFE (the move is contained AND directional). Block
        # trades below the floor so only high-conviction setups fire.
        # First use: GBP_USD/ny floor 0.40 (Brock obs: 9186 m_cert 0.39 won only +6p;
        # 9148/9159/9170/9176 m_cert 0.41-0.84 all bigger MFEs 9.3-13.8p).
        pcmn_raw = raw.get("per_cell_mom_cert_min") or {}
        per_cell_mom_cert_min = {tuple(k.split("/")): float(v) for k, v in pcmn_raw.items()
                                  if "/" in k and len(k.split("/")) == 2}
        # per_cell_dir_cert_min: dict of "pair/session" -> float FLOOR on d_cert.
        # 2026-06-24 deep-dive on GBP_USD/ny inverted (n=11): both losses had d_cert
        # 0.49/0.50, 8 of 9 winners had d_cert >= 0.54 (one win at 0.49). Clean gap at
        # 0.51-0.53. Floor 0.52 catches both losses, costs 1 winning trade — net
        # +31.45p over n=11. Mirror of per_cell_mom_cert_min on direction certainty.
        pcdn_raw = raw.get("per_cell_dir_cert_min") or {}
        per_cell_dir_cert_min = {tuple(k.split("/")): float(v) for k, v in pcdn_raw.items()
                                  if "/" in k and len(k.split("/")) == 2}
        # per_cell_dir_cert_max: dict of "pair/session" -> float CEILING on d_cert.
        # Mirror of per_cell_dir_cert_min. Used with min for range filters when only
        # mid-range direction conviction works for the cell (extremes go either way).
        # 2026-06-25 first use: USD_CHF/ny + USD_CHF/london = 0.55 (paired with min 0.35).
        pcdx_raw = raw.get("per_cell_dir_cert_max") or {}
        per_cell_dir_cert_max = {tuple(k.split("/")): float(v) for k, v in pcdx_raw.items()
                                  if "/" in k and len(k.split("/")) == 2}
        # per_cell_willr_range: dict of "pair/session/direction" -> [min, max] on willr_m5.
        # 2026-06-23 backtest finding (EUR_JPY/ny/short): willr in [-85, -7] gives
        # +8.48p/70.2% WR vs baseline +6.95p/64.8% (1999 V5-actionable bars).
        # Per (pair, session, direction) granularity since willr behavior is direction-asymmetric.
        pcwr_raw = raw.get("per_cell_willr_range") or {}
        per_cell_willr_range = {}
        for k, v in pcwr_raw.items():
            parts = k.split("/")
            if len(parts) == 3 and isinstance(v, (list, tuple)) and len(v) == 2:
                per_cell_willr_range[tuple(parts)] = (float(v[0]), float(v[1]))
        # per_cell_kc_up_range: dict of "pair/session/direction" -> [min, max] on kc_up_dist_pips.
        # 2026-06-23 backtest finding (AUD_USD/london/short): kc_up in [-15, 0] gives
        # +4.22p/69% WR vs baseline +2.86p/65% on 1120 V5-actionable bars. Deep-below
        # bucket kc_up < -20 was a LOSING zone (-4.02p mean, 54% WR).
        pckur_raw = raw.get("per_cell_kc_up_range") or {}
        per_cell_kc_up_range = {}
        for k, v in pckur_raw.items():
            parts = k.split("/")
            if len(parts) == 3 and isinstance(v, (list, tuple)) and len(v) == 2:
                per_cell_kc_up_range[tuple(parts)] = (float(v[0]), float(v[1]))
        return {
            "account":         {**_PM_ACCT_DEFAULTS, **acct},
            "defaults":        {**_PM_DEFAULTS,      **(raw.get("defaults") or {})},
            "per_pair":        raw.get("per_pair") or {},
            "disabled_cells":  dc,
            "inverted_shadow_cells": isc,
            "inverted_live_cells":   ilc,
            "random_pick":     random_pick,
            "per_cell_mom_cert_max": per_cell_mom_cert_max,
            "per_cell_mom_cert_min": per_cell_mom_cert_min,
            "per_cell_dir_cert_min": per_cell_dir_cert_min,
            "per_cell_dir_cert_max": per_cell_dir_cert_max,
            "per_cell_willr_range":  per_cell_willr_range,
            "per_cell_kc_up_range":  per_cell_kc_up_range,
        }
    except Exception:
        return {"account": dict(_PM_ACCT_DEFAULTS), "defaults": dict(_PM_DEFAULTS),
                "per_pair": {}, "disabled_cells": frozenset(),
                "inverted_shadow_cells": frozenset(),
                "inverted_live_cells":   frozenset(),
                "random_pick":     False,
                "per_cell_mom_cert_max": {},
                "per_cell_mom_cert_min": {},
                "per_cell_dir_cert_min": {},
                "per_cell_dir_cert_max": {},
                "per_cell_willr_range":  {},
                "per_cell_kc_up_range":  {}}

def _pm_for_pair(cfg: dict, pair: str) -> dict:
    eff = dict(cfg["defaults"])
    eff.update(cfg["per_pair"].get(pair) or {})
    return eff

def pm_margin_pct() -> float:
    """Fraction of BALANCE used as margin per trade (V1 model)."""
    return float(_pm_load()["account"]["margin_pct_per_trade"])

# Back-compat alias
pm_risk_pct = pm_margin_pct

def pm_max_concurrent() -> int:
    return int(_pm_load()["account"]["max_concurrent_trades"])

def pm_inverted_shadow_cells() -> frozenset:
    """(pair, session) cells whose signal stream is shadow-logged for invert evaluation."""
    return _pm_load().get("inverted_shadow_cells", frozenset())

def pm_inverted_live_cells() -> frozenset:
    """(pair, session) cells whose live trade direction is FLIPPED at execution."""
    return _pm_load().get("inverted_live_cells", frozenset())

def pm_random_pick() -> bool:
    """True when pick_best randomizes among actionable candidates."""
    return bool(_pm_load().get("random_pick", False))

# ── Certainty floors (dm_04-derived, see module docstring) ──────────────────
MIN_DIRECTION_SCORE = 0.25   # |direction.score| minimum
MIN_DIR_CERTAINTY   = 0.30   # direction.certainty minimum
MIN_MOM_CERTAINTY   = 0.25   # momentum.certainty minimum

# ── Position and spread limits ───────────────────────────────────────────────
MAX_OPEN_POSITIONS = 3

# Maximum spread to accept a trade (pips).  Above these levels the spread
# consumes too much of the expected edge.  0.0 in the ticket = feed not yet
# wired → skip the spread gate (fail-open until feed is live).
_MAX_SPREAD: dict[str, float] = {
    "EUR_USD": 2.5,
    "GBP_USD": 3.0,
    "USD_JPY": 2.0,
    "AUD_USD": 2.5,
    "USD_CAD": 3.0,
    "USD_CHF": 3.0,
    "EUR_JPY": 3.5,
    "AUD_JPY": 4.0,
}
_DEFAULT_MAX_SPREAD = 3.0


@dataclass
class TradeTicket:
    """What the playmaker emits — consumed by trade management, not signal modules."""
    pair:          str
    session:       str
    direction:     str     # "long" | "short"
    score:         float   # composite_score at fire time
    dir_certainty: float   # direction module certainty
    mom_certainty: float   # momentum module certainty
    vol_regime:    str     # from momentum stamp
    expected_pips: float   # from momentum stamp
    timestamp:     datetime
    reads:         dict    # direction.reads + momentum.reads for logging/debug
    rivals:        int = 0 # how many other candidates passed all gates this cycle
    inverted_live: bool = False  # True when direction was flipped by inverted_live_cells


def _passes_gates(t: PairTicket, pcfg: dict) -> bool:
    """All certainty + spread gates the playmaker requires (beyond is_actionable).
    pcfg: per-pair effective config (defaults + override) from _pm_for_pair()."""
    d, m = t.direction, t.momentum

    if not pcfg.get("enabled", True):
        return False
    if not t.is_actionable:
        return False
    if abs(d.score) < float(pcfg["min_direction_score"]):
        return False
    if d.certainty < float(pcfg["min_dir_certainty"]):
        return False
    if m.certainty < float(pcfg["min_mom_certainty"]):
        return False
    if t.spread_pips > 0.0:
        max_spread = _MAX_SPREAD.get(t.pair, _DEFAULT_MAX_SPREAD)
        if t.spread_pips > max_spread:
            return False
    return True

def _edge_rank(t: PairTicket) -> tuple:
    """Higher is better.  Primary: composite magnitude.  Secondary: expected move."""
    return (abs(t.composite_score), t.momentum.expected_pips)


def pick_best(
    tickets:       list[PairTicket],
    hour_utc:      int,
    open_pairs:    set[str],
    max_positions: Optional[int] = None,
    now:           Optional[datetime] = None,
    sl_history:    Optional[dict] = None,
) -> Optional[TradeTicket]:
    """Select the best-edge trade ticket from active pair tickets.

    Returns None when:
      - position limit is already reached (max_concurrent_trades from playmaker config), or
      - no ticket passes per-pair certainty + spread gates, or
      - pair is under cooldown after a recent losing exit.

    When multiple tickets pass (group arrival), picks the one with the highest
    abs(composite_score), breaking ties by expected_pips.
    """
    pm = _pm_load()
    max_positions = int(max_positions if max_positions is not None
                        else pm["account"]["max_concurrent_trades"])
    if len(open_pairs) >= max_positions:
        return None

    # Step 1: session + position + enabled + cooldown
    eligible = []
    for t in tickets:
        if t.pair in open_pairs:
            continue
        if t.session not in PAIR_SESSIONS.get(t.pair, []):
            continue
        pcfg = _pm_for_pair(pm, t.pair)
        if not pcfg.get("enabled", True):
            continue
        # 2026-06-21 Master Matrix: per-cell disable for cells with negative ML edge + no live evidence
        if (t.pair, t.session, t.direction.bias) in pm.get("disabled_cells", frozenset()):
            continue
        # 2026-06-23 per-cell m_cert CEILING (Brock reframe): block trades with m_cert
        # above the cell's ceiling. Low m_cert = big-move setup; high m_cert = small
        # contained move. For cells whose edge IS the big-move tail, filter out the
        # small-move trades that would dilute the cell's average.
        _pcmm = pm.get("per_cell_mom_cert_max", {})
        _cell_max = _pcmm.get((t.pair, t.session))
        if _cell_max is not None and t.momentum.certainty > _cell_max:
            continue
        # 2026-06-23 per-cell m_cert FLOOR: mirror of above for cells where the pattern
        # is opposite (high m_cert correlates with big MFE). Block low-cert trades so
        # only high-conviction setups fire.
        _pcmn = pm.get("per_cell_mom_cert_min", {})
        _cell_min = _pcmn.get((t.pair, t.session))
        if _cell_min is not None and t.momentum.certainty < _cell_min:
            continue
        # 2026-06-24 per-cell d_cert FLOOR: mirror on direction certainty.
        # First use: GBP_USD/ny=0.52 (both n=11 inverted losses had d_cert 0.49/0.50;
        # 8 of 9 winners had d_cert >= 0.54; clean gap at 0.51-0.53).
        _pcdn = pm.get("per_cell_dir_cert_min", {})
        _cell_dmin = _pcdn.get((t.pair, t.session))
        if _cell_dmin is not None and t.direction.certainty < _cell_dmin:
            continue
        # 2026-06-25 per-cell d_cert CEILING: mirror of min for range filters.
        # First use: USD_CHF/ny + london = 0.55 (paired with min 0.35).
        _pcdx = pm.get("per_cell_dir_cert_max", {})
        _cell_dmax = _pcdx.get((t.pair, t.session))
        if _cell_dmax is not None and t.direction.certainty > _cell_dmax:
            continue
        # 2026-06-23 per-cell willr_m5 range gate (per pair/session/direction).
        # 2026 backtest finding: EUR_JPY/ny/short willr in [-85, -7] = +8.5p/70% WR
        # vs baseline +6.9p/65% on 1999 V5-actionable bars. Block bars outside the range.
        _pcwr = pm.get("per_cell_willr_range", {})
        _willr_rng = _pcwr.get((t.pair, t.session, t.direction.bias))
        if _willr_rng is not None:
            _willr = getattr(t, "willr_m5", 0.0)
            if _willr < _willr_rng[0] or _willr > _willr_rng[1]:
                continue
        # 2026-06-23 per-cell kc_up_dist_pips range gate (mirror of willr_range).
        # AUD_USD/london/short backtest: kc_up in [-15, 0] = +4.22p/69% WR vs baseline
        # +2.86p/65% on 1120 V5-actionable bars. Deep-below (<-20) is a LOSING zone.
        _pckur = pm.get("per_cell_kc_up_range", {})
        _kc_rng = _pckur.get((t.pair, t.session, t.direction.bias))
        if _kc_rng is not None:
            _kc = getattr(t, "kc_up_dist_pips", 0.0)
            if _kc < _kc_rng[0] or _kc > _kc_rng[1]:
                continue
        cd_min = float(pcfg.get("cooldown_after_sl_min", 0) or 0)
        if cd_min > 0 and now is not None and sl_history and t.pair in sl_history:
            elapsed_min = (now - sl_history[t.pair]).total_seconds() / 60.0
            if elapsed_min < cd_min:
                continue
        eligible.append((t, pcfg))
    if not eligible:
        return None

    # Step 2: certainty + spread gates per pair
    candidates = [t for (t, pcfg) in eligible if _passes_gates(t, pcfg)]
    if not candidates:
        return None

    # Step 3: pick winner — random.choice (if random_pick on) or max edge_rank
    if pm.get("random_pick", False):
        import random
        best = random.choice(candidates)
        pick_method = "random"
    else:
        best = max(candidates, key=_edge_rank)
        pick_method = "edge_rank"
    # Step 4: per-cell live inversion — flip trade direction for inverted_live_cells
    signal_dir = best.direction.bias
    inverted = (best.pair, best.session) in pm.get("inverted_live_cells", frozenset())
    trade_dir = ("short" if signal_dir == "long" else "long") if inverted else signal_dir
    return TradeTicket(
        pair=best.pair,
        session=best.session,
        direction=trade_dir,
        score=round(best.composite_score, 4),
        dir_certainty=round(best.direction.certainty, 4),
        mom_certainty=round(best.momentum.certainty, 4),
        vol_regime=best.momentum.vol_regime,
        expected_pips=best.momentum.expected_pips,
        timestamp=best.timestamp,
        reads={
            "direction": best.direction.reads,
            "momentum":  best.momentum.reads,
            "signal_direction": signal_dir,  # what the engine SAW pre-inversion
            "pick_method":      pick_method, # "random" or "edge_rank"
        },
        rivals=len(candidates) - 1,
        inverted_live=inverted,
    )