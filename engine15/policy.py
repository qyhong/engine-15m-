# -*- coding: utf-8 -*-
"""policy -- stage 4 of the thought process: THE MANDATE.

The engine must be LONG or SHORT almost all the time. It may sit out at most `idle_max`
sessions (4 x 15 minutes = 1 hour) in a row, and only while neither side is rewarding for
the risk on the table. After that it must commit to the better side.

One pure function. In: the position, how many sessions it has been flat, and the engine's
odds at this close. Out: what to do at the next open, and why (a reason code the journal
turns into words).

  edge = P(up first) - P(down first)      the long side's edge; the short side's is -edge
  FLAT   edge of the better side >= theta_enter (theta_enter_shock when risk is high)
             -> ENTER that side
         else idle < idle_max -> IDLE (sit out one more session)
         else -> FORCED: the mandate picks the better side (ties: with the 4h/1d trend)
  LONG / SHORT
         the other side's edge >= theta_flip -> FLIP (two fills: the edge must pay for them)
         risk is high AND the held side's edge is negative -> STEP_ASIDE (flat, the idle
             clock starts)
         else -> HOLD
A protective stop (backtest.py) can also flatten the book; the idle clock starts then too.
"""
ENTER, FORCED, IDLE, HOLD, FLIP, STEP_ASIDE, WAIT = "ENTER", "FORCED", "IDLE", "HOLD", "FLIP", "STEP_ASIDE", "WAIT"


def decide(pos, idle, p_up, p_down, shock, tide, cfg, bias=0, guard=False):
    """-> (action, target_position, reason). pos/target in {-1, 0, +1}.
    p_up / p_down None = the engine has no odds yet (still learning): WAIT, flat, uncounted.
    bias  +1 / -1 / 0: the higher-timeframe bias (v5): the 1h, 4h and daily trends all one way AND
          price on that side of the 1h EMA50 and the 4h EMA20 and EMA50, which then act as
          support (bias +1) or resistance (bias -1). 0 = no clear bias.
    guard True in the hour before a scheduled high-impact US release (v5, hypothesis H2): no new
          position and no flip; a position already open is kept (its stop stays live)."""
    if p_up is None or p_up != p_up:
        return WAIT, 0, "no_model"
    edge = p_up - p_down
    side = 1 if edge > 0 else -1 if edge < 0 else (1 if tide >= 0 else -1)
    use_bias = bool(cfg.get("htf_bias")) and bias != 0
    if pos == 0:
        if guard and cfg.get("release_guard"):                     # the hour before CPI, jobs, the Fed ...
            return IDLE, 0, "release_guard"
        need = cfg["theta_enter_shock"] if shock else cfg["theta_enter"]
        if use_bias and side != bias:                              # against the bias: a much bigger edge is needed
            need = max(need, cfg.get("theta_counter", 0.15))
        if abs(edge) >= need:
            return ENTER, side, "edge_clears_bar" if not use_bias or side == bias else "counter_bias_clears_bar"
        if idle >= cfg["idle_max"]:
            if use_bias:                                           # no real edge: go with the higher-timeframe bias
                return FORCED, bias, "mandate_with_bias"
            if cfg.get("trend_tiebreak") and tide != 0:            # no real edge: go with the 4h and daily trend
                return FORCED, (1 if tide > 0 else -1), "mandate_with_trend"
            return FORCED, side, "mandate_idle_limit"
        return IDLE, 0, "no_side_rewarding_high_risk" if shock else "no_side_rewarding"
    held_edge = edge * pos
    if guard and cfg.get("release_guard"):                         # keep what is open; no flip into a release
        return HOLD, pos, "release_guard_hold"
    if use_bias and pos != bias and held_edge < cfg["theta_enter"]:  # fighting every timeframe without a real edge
        return FLIP, bias, "against_htf_bias"
    if -held_edge >= cfg["theta_flip"]:
        return FLIP, -pos, "other_side_clears_flip_bar"
    if cfg.get("step_aside", True) and shock and held_edge < 0:
        return STEP_ASIDE, 0, "high_risk_and_edge_gone"
    return HOLD, pos, "edge_still_with_position" if held_edge >= 0 else "against_but_below_flip_bar"
