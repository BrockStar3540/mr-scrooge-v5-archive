# Deployment + rollback

How V5 lives on EC2 and how to push changes safely.

## Where V5 lives

- **EC2**: `[REDACTED-IP]` (Tailscale, preferred) / `[REDACTED-IP]` (public)
- **SSH**: `ssh -i ~/.ssh/openclaw-key.pem ubuntu@[REDACTED-IP]`
- **Repo path**: `~/mr-scrooge-v5/`
- **Service**: `mr-scrooge-v5.service` (systemd user unit)
- **venv**: `~/mr-scrooge-v5/.venv/`
- **Logs**: `journalctl --user -u mr-scrooge-v5 -f`

## Service control

```bash
# Status
systemctl --user status mr-scrooge-v5

# Restart (needed only when you change Python source or .env or sessions.py)
systemctl --user restart mr-scrooge-v5

# Stop / start
systemctl --user stop mr-scrooge-v5
systemctl --user start mr-scrooge-v5

# Tail logs
journalctl --user -u mr-scrooge-v5 -f
journalctl --user -u mr-scrooge-v5 --since today --no-pager
```

When you need NOT to restart:
- Edits to `config/exit_config.json` or `config/playmaker_config.json` — engine re-reads on next cycle.
- Edits to the dashboard via the panel UI — server hot-reloads.

When you DO need to restart:
- Any change to `core/`, `modules/`, `ops/server.py`, `main.py`.
- Any change to `config/sessions.py` (static Python, not hot-reloaded).
- Any change to `data/factor_sweep.json` (loaded at module init, cached for process lifetime).
- Any change to `~/.openclaw/secrets.env`.

## Git deploy flow

V5 has two git remotes:
- `origin` → GitHub (`BrockStar3540/mr-scrooge-v5`)
- `alien` → Mac Mini mirror (via Tailscale)

Standard workflow:

```bash
ssh -i ~/.ssh/openclaw-key.pem ubuntu@[REDACTED-IP]
cd ~/mr-scrooge-v5
# Edit / commit on EC2 directly OR pull from a feature branch
git pull origin main          # if you're updating from outside
git status
git diff
git add <files>
git commit -m "Subject

Body explaining what + why"
git push origin main
git push alien main           # mirror

# Restart only if Python files changed
systemctl --user restart mr-scrooge-v5
```

## Staging vs activating new modules

V5 follows a **stage-then-activate** pattern. The pattern:

1. Add the new module file (e.g., `direction_v2.py`) alongside the existing live one.
2. Commit it. Engine.py still imports the v1 module by name — v2 is in the tree but unused.
3. Run smoke tests in the module's own folder:
   ```bash
   cd modules/signals
   python3 test_<thing>.py
   ```
4. (Optionally) wire shadow logging: in `engine.py`, import both v1 and v2; log both stamps each cycle without acting on v2.
5. When confident, swap the engine import:
   ```python
   from modules.signals.direction_v2 import DirectionModule
   ```
6. Restart the service.
7. Watch the live trades for 1-3 days to confirm behavior matches expectation.

Rollback is always: revert the import line + restart. The old module file stays in the tree.

## Per-(pair × session × direction) module activation order

**Activated 2026-06-20** — direction_v2 + momentum_v3 are now the live modules. The activation was applied via `modules/signals/__init__.py` (single source of truth for which module the engine uses), so `core/engine.py` was unchanged. The historical activation steps below remain valid as the rollback procedure:

1. Update engine imports:
   ```python
   from modules.signals.direction_v2 import DirectionModule
   from modules.signals.momentum_v3 import MomentumModule
   ```
2. Update the per-cycle flow to pass direction into momentum:
   ```python
   d_stamp = direction.stamp(view)
   if d_stamp.bias == "block":
       continue
   m_stamp = momentum.stamp(view, d_stamp.bias)  # NEW: direction arg
   ```
3. Restart.

The Playmaker doesn't need any change — it already gates on `min_mom_certainty`, and when v3 gates fail it emits `certainty = 0.0`.

Rollback: revert both import lines + revert the `momentum.stamp()` call signature + restart.

## Config rollback

Config files don't go through git in the normal way — they're hot-reloaded JSON. The rollback pattern is via filesystem backups:

```bash
# Before editing
cp config/exit_config.json config/exit_config.json.bak-pre-<changeName>

# Edit + verify behavior

# If bad:
cp config/exit_config.json.bak-pre-<changeName> config/exit_config.json
# Engine picks up the revert on next cycle
```

Backups eventually get archived. See [../CHANGELOG.md](../CHANGELOG.md) `[2026-06-19] repo cleanup` for the archive pattern + Dropbox storage.

## OANDA broker safety

The broker module has a few guards:

- Every order has a server-side SL set at submission time. If V5 crashes before the ratchet runs, OANDA still holds the SL.
- The broker validates order size against account margin BEFORE submitting.
- Retries on network errors with exponential backoff (capped).
- All orders are logged with their OANDA `transaction_id` for reconciliation.

The `/api/positions/reconcile` endpoint can re-sync V5's in-memory state from OANDA `positions()` if the two ever drift (e.g., after a crash + restart).

## Pre-flight checklist

Before pushing a substantive change:

- [ ] Tests pass: `cd modules/signals && python3 test_<thing>.py` (or whichever test files exist for the changed module)
- [ ] Engine import order makes sense if you're swapping module versions
- [ ] Config backups in place if config edits are part of the change
- [ ] Commit message has both **what** and **why** lines
- [ ] [CHANGELOG.md](../CHANGELOG.md) entry drafted
- [ ] Dashboard renders without JS errors after deploy (open browser, check console)
- [ ] At least one full `_cycle()` runs cleanly post-deploy (`journalctl -f`)

## Post-deploy verification

After any significant deploy:

```bash
# Watch the next cycle
journalctl --user -u mr-scrooge-v5 -f

# Check open positions match expected
curl -s http://localhost:8084/api/state | python3 -m json.tool | head -40

# Check config the engine sees
curl -s http://localhost:8084/api/config/exit | python3 -m json.tool

# Check service is healthy
systemctl --user is-active mr-scrooge-v5
```

If the engine logs an exception traceback or the dashboard 500s, roll back immediately (revert the commit + restart).
