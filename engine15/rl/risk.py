# -*- coding: utf-8 -*-
"""risk -- the risk manager that sits between the agent and execution (paper only).

The agent asks for a target position; the risk manager returns the target that is allowed.
Every order it blocks or resizes is logged with the rule and the reason. Rules:

  max_position   |target| is capped at max_position (resize).
  daily_loss     once equity is max_daily_loss below where the UTC day started, the book is flat
                 for the rest of that UTC day (orders that add or keep risk are blocked).
  kill_switch    once equity is kill_drawdown below its running peak, the book goes flat and stays
                 flat for kill_cooldown_bars (a stand-in for "stop and review"); then the peak is reset
                 to the equity at release and trading resumes.
  vol_breaker    when short-term realised vol (e.g. rv_16, 4 hours) is above vol_breaker_mult x the
                 long-term one (rv_672, one week), |target| is capped at vol_breaker_max_position.

The equity rules (daily_loss, kill_switch) are checked at EVERY bar close through on_bar();
must_flatten() tells the simulator to go flat at once (fill at the next open) without waiting for
the agent's next decision. Volatility inputs are closed-bar features known at the decision.
"""
from dataclasses import asdict, dataclass

DAY_MS = 86400000


@dataclass
class RiskConfig:
    enabled: bool = True
    max_position: float = 1.0
    max_daily_loss: float = 0.05
    kill_drawdown: float = 0.30
    kill_cooldown_bars: int = 672
    vol_breaker_mult: float = 3.0
    vol_breaker_max_position: float = 0.5
    vol_breaker_short: str = "rv_16"
    vol_breaker_long: str = "rv_672"

    @classmethod
    def from_cfg(cls, c):
        c = dict(c or {})
        keys = set(cls.__dataclass_fields__)
        return cls(**dict((k, v) for k, v in c.items() if k in keys))

    def as_dict(self):
        return asdict(self)


def _cap(x, m):
    return max(-m, min(m, x))


class RiskManager:
    def __init__(self, cfg=None, log_events=True):
        self.cfg = cfg if isinstance(cfg, RiskConfig) else RiskConfig.from_cfg(cfg)
        self.log_events = log_events
        self.events = []
        self.counts = {"max_position": 0, "daily_loss": 0, "kill_switch": 0, "vol_breaker": 0,
                       "kill_switch_triggered": 0, "daily_loss_triggered": 0, "forced_flat": 0}
        self.reset()

    def reset(self, equity=1.0, close_ms=None):
        self.peak = float(equity)
        self.day = None if close_ms is None else int(close_ms) // DAY_MS
        self.day_start = float(equity)
        self.equity = float(equity)
        self.bar = 0
        self.killed_until = None
        self.daily_hit_day = None

    # ---- every bar close
    def on_bar(self, close_ms, equity):
        """Update the equity state at a bar's close (close_ms = the bar's close time, UTC ms)."""
        c = self.cfg
        self.bar += 1
        self.equity = float(equity)
        day = int(close_ms - 1) // DAY_MS                       # the UTC day this bar belongs to
        if self.day is None:
            self.day = day
            self.day_start = self.equity
        elif day != self.day:
            # a new UTC day began at the previous bar's close; its start equity is the equity then
            self.day = day
            self.day_start = getattr(self, "_prev_equity", self.equity)
        if self.killed_until is not None and self.bar >= self.killed_until:
            self.killed_until = None
            self.peak = self.equity
            self._log(close_ms, "kill_switch_release", None, None, None,
                      "cool-down over; peak reset to equity %.4f" % self.equity, count=False)
        if self.equity > self.peak:
            self.peak = self.equity
        if not c.enabled:
            self._prev_equity = self.equity
            return
        if self.killed_until is None and self.peak > 0 and self.equity / self.peak - 1.0 <= -c.kill_drawdown:
            self.killed_until = self.bar + int(c.kill_cooldown_bars)
            self.counts["kill_switch_triggered"] += 1
            self._log(close_ms, "kill_switch_on", None, None, None,
                      "drawdown %.1f%% from peak >= %.1f%%; flat for %d bars"
                      % (100 * (1 - self.equity / self.peak), 100 * c.kill_drawdown, c.kill_cooldown_bars), count=False)
        if self.daily_hit_day != self.day and self.day_start > 0 and self.equity / self.day_start - 1.0 <= -c.max_daily_loss:
            self.daily_hit_day = self.day
            self.counts["daily_loss_triggered"] += 1
            self._log(close_ms, "daily_loss_on", None, None, None,
                      "day loss %.1f%% >= %.1f%%; flat for the rest of the UTC day"
                      % (100 * (1 - self.equity / self.day_start), 100 * c.max_daily_loss), count=False)
        self._prev_equity = self.equity

    def killed(self):
        return self.killed_until is not None

    def daily_stopped(self):
        return self.daily_hit_day is not None and self.daily_hit_day == self.day

    def must_flatten(self):
        return bool(self.cfg.enabled and (self.killed() or self.daily_stopped()))

    def restricting(self):
        return self.must_flatten()

    # ---- at a decision
    def filter(self, requested, current, close_ms, vol_short=None, vol_long=None):
        """requested target -> allowed target. Logs every block / resize with its reason."""
        c = self.cfg
        req = float(requested)
        if not c.enabled:
            return req
        a = req
        rules, why = [], []
        if abs(a) > c.max_position:
            a = _cap(a, c.max_position)
            rules.append("max_position")
            why.append("|%.2f| > max %.2f" % (req, c.max_position))
        if self.killed():
            if a != 0.0:
                rules.append("kill_switch")
                why.append("kill switch on (drawdown >= %.0f%%), %d bars of cool-down left"
                           % (100 * c.kill_drawdown, self.killed_until - self.bar))
            a = 0.0
        elif self.daily_stopped():
            if a != 0.0:
                rules.append("daily_loss")
                why.append("day's loss >= %.1f%%: flat until the next UTC day" % (100 * c.max_daily_loss))
            a = 0.0
        if (a != 0.0 and vol_short is not None and vol_long is not None and vol_long == vol_long and vol_short == vol_short
                and vol_long > 0 and vol_short > c.vol_breaker_mult * vol_long and abs(a) > c.vol_breaker_max_position):
            a = _cap(a, c.vol_breaker_max_position)
            rules.append("vol_breaker")
            why.append("%s %.5f > %.1f x %s %.5f" % (c.vol_breaker_short, vol_short, c.vol_breaker_mult,
                                                     c.vol_breaker_long, vol_long))
        if a != req:
            for r in rules:
                self.counts[r] += 1
            self._log(close_ms, "+".join(rules), req, a, current, "; ".join(why), count=False)
        return a

    def forced(self, close_ms, current):
        """The simulator flattened `current` between decisions because must_flatten() was true."""
        self.counts["forced_flat"] += 1
        rule = "kill_switch" if self.killed() else "daily_loss"
        self._log(close_ms, rule + "_forced_flat", current, 0.0, current,
                  "equity rule breached at this bar's close: flat at the next open", count=False)

    def _log(self, close_ms, rule, requested, allowed, current, reason, count=True):
        if self.log_events:
            self.events.append({"close_ms": int(close_ms), "rule": rule, "requested": requested, "allowed": allowed,
                                "current": current, "reason": reason})
