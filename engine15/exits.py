# -*- coding: utf-8 -*-
"""exits -- trade-management rules shared by every book that simulates a position. PAPER ONLY.

Pure functions, one bar at a time, no state of their own: the caller keeps the numbers in its own
state and passes them back each bar. Used by the H36 shadow books (engine15/shadows.run) and written so
the main book's simulation (backtest.run_book) can call the very same code if the owner switches the
main rule (a v5.2); nothing here changes the main book by itself.

THE MOVING-AVERAGE TRAIL (research/HYPOTHESES.md, H36). Read at the close of bar t:
  * the average is the MA value of row t (15m: bars <= t; 1h: the last 1h bar CLOSED by t's close,
    mavg.py's htf join), so no bar after t is ever used;
  * arming: "entry" (from the entry bar's close), "1r" (once a bar's high / low has gone one stop
    distance in favour), "t1" (once Target 1 has traded);
  * once armed the level is ratcheted: long = the highest MA since arming, short = the lowest. It
    never loosens;
  * it counts only while tighter than the protective stop (which stays live inside every bar);
  * a CLOSE beyond the level against the position is an exit, filled at the NEXT open by the caller.

BREAK-EVEN AFTER TARGET 1: once a bar trades through Target 1 the stop moves to entry, live from the
next bar, never loosening an already tighter stop.
"""

ARM_R = 1.0                     # "1r": arm after one stop distance in favour (b_trail's TRAIL_ARM_R)
MA_WORDS = {"ema": "EMA", "sma": "SMA"}
ARM_WORDS = {"entry": "from entry", "1r": "after 1R", "t1": "after Target 1"}


def ma_basis(key):
    """'1h ema20' -> 'EMA20 on 1h' (the trail's name on the page)."""
    tf, m = key.split()
    return "%s%s on %s" % (MA_WORDS[m[:3]], m[3:], tf)


def reached(pos, high, low, level):
    """Did this bar trade at `level` in the position's favour (a target)?"""
    return high >= level if pos == 1 else low <= level


def be_stop(pos, entry, stop):
    """The stop after Target 1: entry, or the current stop when that is already tighter."""
    return max(stop, entry) if pos == 1 else min(stop, entry)


def ma_trail_step(pos, entry, stop, stop0, armed, level, arm, t1_hit, high, low, close, ma):
    """One bar's close of the moving-average trail.
    pos +1/-1, entry the fill, stop the live protective stop, stop0 the stop at entry (1R = |entry - stop0|),
    armed / level the trail's state from the previous bar (level None until it has a value),
    arm "entry" | "1r" | "t1", t1_hit whether Target 1 has traded, high / low / close of this bar,
    ma the average at this close (NaN = no read: the level is kept).
    -> (armed, level, exit_now): exit_now True = close beyond the level, out at the next open."""
    if not armed:
        R = abs(entry - stop0)
        if arm == "entry":
            armed = True
        elif arm == "t1":
            armed = bool(t1_hit)
        elif arm == "1r":
            armed = R > 0 and pos * ((high if pos == 1 else low) - entry) >= ARM_R * R
    if not armed:
        return False, level, False
    if ma == ma:
        ma = float(ma)
        level = ma if level is None else (max(level, ma) if pos == 1 else min(level, ma))
    exit_now = level is not None and pos * (level - stop) > 0 and pos * (close - level) < 0
    return True, level, bool(exit_now)


def trail_from_history(pos, entry, stop0, t1, arm, high, low, close, ma, i_in, i_last, be_t1=False):
    """For a switch of the main book (v5.2): rebuild an OPEN trade's trail from its own bars since entry, closed
    bars only. i_in = the row of the entry bar (filled at its open), i_last = the last closed row. Runs the same
    per-bar steps as a book would have (the protective stop first inside each bar, then Target 1 / break-even,
    then the trail at the close). -> dict(armed, level, t1_hit, stop, exit_row, exit_why): exit_row is the first
    row at whose close (or inside which, for a stop) the rule would already have closed the trade, else None;
    the caller then closes it at the next open (a trail) and says so, rather than pretending it was closed earlier."""
    armed, level, t1_hit, stop = False, None, False, float(stop0)
    for i in range(int(i_in), int(i_last) + 1):
        if (pos == 1 and low[i] <= stop) or (pos == -1 and high[i] >= stop):
            return dict(armed=armed, level=level, t1_hit=t1_hit, stop=stop, exit_row=i,
                        exit_why="STOP_BE" if (t1_hit and be_t1) else "STOP")
        if t1 is not None and not t1_hit and reached(pos, high[i], low[i], t1):
            t1_hit = True
            if be_t1:
                stop = be_stop(pos, entry, stop)
        if arm:
            armed, level, out = ma_trail_step(pos, entry, stop, stop0, armed, level, arm, t1_hit,
                                              high[i], low[i], close[i], ma[i])
            if out:
                return dict(armed=armed, level=level, t1_hit=t1_hit, stop=stop, exit_row=i, exit_why="TRAIL_MA")
    return dict(armed=armed, level=level, t1_hit=t1_hit, stop=stop, exit_row=None, exit_why=None)
