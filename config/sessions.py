# Session windows in UTC hours. V5 uses 8 fine-grained sessions.
SESSIONS = {
    "asia":         (22, 7),    # 22:00-07:00 UTC
    "asia_late":    (4,  7),    # 04:00-07:00 UTC
    "london_open":  (7,  9),    # 07:00-09:00 UTC
    "london":       (9,  15),   # 09:00-15:00 UTC
    "ny_open":      (13, 15),   # 13:00-15:00 UTC (overlaps london)
    "ny_mid":       (15, 19),   # 15:00-19:00 UTC
    "ny_close":     (19, 22),   # 19:00-22:00 UTC
    "off_hours":    (22, 22),   # effectively closed
}

def current_session(hour_utc: int) -> str:
    if 7 <= hour_utc < 9:   return "london_open"
    if 13 <= hour_utc < 15: return "ny_open"
    if 9 <= hour_utc < 15:  return "london"
    if 15 <= hour_utc < 19: return "ny_mid"
    if 19 <= hour_utc < 22: return "ny_close"
    if 4 <= hour_utc < 7:   return "asia_late"
    if 22 <= hour_utc or hour_utc < 4: return "asia"
    return "off_hours"
