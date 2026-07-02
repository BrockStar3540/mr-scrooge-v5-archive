"""modules/signals/profile_shadow.py — corrected-profile shadow dual-stamp.

2026-07-02: research/sessions/2026-06-21_v5_2026_audit produced a corrected
per-cell direction-profile assignment (data/config_2026_per_cell.json,
`direction_profile_recommended` — most cells → reversion). A 6-month
retrospective replay validated it: 6/6 winning months, +2.3-3.2p mean fwd
per call. Before flipping the live PROFILE_ASSIGNMENT we shadow the
corrected stack on live V5 bars: the engine stamps each scanned MarketView
through a SECOND set of DirectionModules built from the corrected
assignment and logs a SHADOW_PROFILE line when the two stacks disagree on
bias or either is non-block. EXECUTION IS UNCHANGED — logging only.

Fail-open by design: if the audit JSON is missing or unparseable the shadow
is disabled with a single warning and shadow_stamp() returns None; a cell
whose shadow module fails to build is skipped, never the engine.

Kill-switch: defaults.profile_shadow_enabled in config/playmaker_config.json
(hot-reload, checked by the engine each cycle — see pm_profile_shadow_enabled).
Scorer: research/tools/profile_shadow_score.py greps the journal's
SHADOW_PROFILE lines and measures 1H forward pips per stack.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Optional

from .base import MarketView
from .direction_v2 import DirectionModule, _normalize_weights
from .direction_profiles import (
    _profile_continuation_strong, _profile_reversion, _profile_default,
)

log = logging.getLogger("v5.profile_shadow")

_AUDIT_PATH = (Path(__file__).resolve().parents[2]
               / "research" / "sessions" / "2026-06-21_v5_2026_audit"
               / "data" / "config_2026_per_cell.json")

_PROFILE_DEFS = {
    "continuation_strong": _profile_continuation_strong,
    "reversion":           _profile_reversion,
    "default":             _profile_default,
}

_EVIDENCE_TAG = "SHADOW_2026_AUDIT"


def _load_corrected() -> dict[tuple[str, str, str], str]:
    """(pair, session, direction) -> recommended profile name. {} = shadow disabled."""
    try:
        raw = json.loads(_AUDIT_PATH.read_text())
        out: dict[tuple[str, str, str], str] = {}
        for key, cell in raw.items():
            # Keys look like "(AUD_JPY,asia,long)"
            parts = [p.strip() for p in key.strip("()").split(",")]
            prof = cell.get("direction_profile_recommended")
            if len(parts) == 3 and prof in _PROFILE_DEFS:
                out[(parts[0], parts[1], parts[2])] = prof
        if not out:
            log.warning("profile_shadow DISABLED: no usable cells in %s", _AUDIT_PATH)
        return out
    except Exception as exc:
        log.warning("profile_shadow DISABLED: cannot load %s: %s", _AUDIT_PATH, exc)
        return {}


_CORRECTED: dict[tuple[str, str, str], str] = _load_corrected()


class _ShadowDirectionModule(DirectionModule):
    """DirectionModule with the corrected (2026-audit) profile assignment.

    Reuses direction_v2 wholesale — same factor_sweep anchors, same dual-compute
    stamp(), same aggregator rules — only the per-direction profile weights are
    swapped for the audit's recommended profiles. Cells absent from the audit
    file keep their live profile."""

    def __init__(self, pair: str, session: str):
        super().__init__(pair, session)          # live profiles + anchors first
        lp = _CORRECTED.get((pair, session, "long"))
        sp = _CORRECTED.get((pair, session, "short"))
        if lp is not None:
            self._long_defs    = _PROFILE_DEFS[lp]()
            self.long_profile  = lp
            self.long_evidence = _EVIDENCE_TAG
        if sp is not None:
            self._short_defs    = _PROFILE_DEFS[sp]()
            self.short_profile  = sp
            self.short_evidence = _EVIDENCE_TAG
        self._long_base  = _normalize_weights(self._long_defs)
        self._short_base = _normalize_weights(self._short_defs)
        feat_union = set(f for f, _ in self._long_defs) | set(f for f, _ in self._short_defs)
        self._feature_list = sorted(feat_union)
        self._load_anchors()                     # re-anchor for the new feature union


# (pair, session) -> module, built lazily on first stamp; None = build failed (cell skipped)
_shadow_mods: dict[tuple[str, str], Optional[_ShadowDirectionModule]] = {}


def shadow_enabled() -> bool:
    """True when the corrected assignment loaded and the shadow can stamp."""
    return bool(_CORRECTED)


def corrected_profile(pair: str, session: str, direction: str) -> Optional[str]:
    """Corrected profile name for a cell, or None if the cell isn't in the audit file."""
    return _CORRECTED.get((pair, session, direction))


def shadow_stamp(view: MarketView) -> Optional[tuple[str, float, float]]:
    """Stamp `view` through the corrected-profile direction stack.

    Returns (bias, score, certainty) for the SAME bar the live stack just
    stamped, or None (shadow disabled / cell shadow unavailable)."""
    if not _CORRECTED:
        return None
    key = (view.pair, view.session)
    if key not in _shadow_mods:
        try:
            _shadow_mods[key] = _ShadowDirectionModule(view.pair, view.session)
        except Exception as exc:
            log.warning("profile_shadow: cannot build shadow module %s/%s: %s",
                        view.pair, view.session, exc)
            _shadow_mods[key] = None
    mod = _shadow_mods[key]
    if mod is None:
        return None
    try:
        stamp = mod.stamp(view)
        return (stamp.bias, stamp.score, stamp.certainty)
    except Exception as exc:
        log.warning("profile_shadow: stamp failed %s/%s: %s", view.pair, view.session, exc)
        return None
