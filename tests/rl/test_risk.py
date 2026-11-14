# -*- coding: utf-8 -*-
"""The risk manager: one test per rule, and every block / resize is logged with a reason."""
from engine15.rl.risk import DAY_MS, RiskConfig, RiskManager

T0 = 1_700_000_000_000 - (1_700_000_000_000 % DAY_MS)          # a UTC midnight
BAR = 900000


def rm(**kw):
    base = dict(max_position=1.0, max_daily_loss=0.05, kill_drawdown=0.30, kill_cooldown_bars=10,
                vol_breaker_mult=3.0, vol_breaker_max_position=0.5)
    base.update(kw)
    return RiskManager(RiskConfig(**base))


def test_max_position_resizes_and_logs():
    r = rm(max_position=0.5)
    assert r.filter(1.0, 0.0, T0) == 0.5
    assert r.filter(-0.8, 0.0, T0) == -0.5
    assert r.filter(0.3, 0.0, T0) == 0.3
    assert r.counts["max_position"] == 2 and len(r.events) == 2
    e = r.events[0]
    assert e["rule"] == "max_position" and e["requested"] == 1.0 and e["allowed"] == 0.5 and "max" in e["reason"]


def test_daily_loss_blocks_until_next_utc_day():
    r = rm()
    eq = 1.0
    r.on_bar(T0 + BAR, eq)                                      # first bar of the day
    r.on_bar(T0 + 2 * BAR, 0.97)
    assert not r.must_flatten() and r.filter(1.0, 0.0, T0 + 2 * BAR) == 1.0
    r.on_bar(T0 + 3 * BAR, 0.94)                                # -6% on the day
    assert r.must_flatten() and r.counts["daily_loss_triggered"] == 1
    assert r.filter(1.0, 1.0, T0 + 3 * BAR) == 0.0
    assert r.filter(0.0, 1.0, T0 + 3 * BAR) == 0.0              # reducing is fine and not logged as a block
    assert r.counts["daily_loss"] == 1
    assert any(e["rule"] == "daily_loss" and "UTC day" in e["reason"] for e in r.events)
    r.on_bar(T0 + DAY_MS, 0.94)                                 # last bar of the day (closes at midnight)
    assert r.must_flatten()
    r.on_bar(T0 + DAY_MS + BAR, 0.94)                           # first bar of the next day
    assert not r.must_flatten() and r.filter(1.0, 0.0, T0 + DAY_MS + BAR) == 1.0


def test_kill_switch_goes_flat_for_cooldown_then_resets_peak():
    r = rm(max_daily_loss=0.99, kill_cooldown_bars=5)
    r.on_bar(T0 + BAR, 1.0)
    r.on_bar(T0 + 2 * BAR, 1.2)                                 # new peak
    r.on_bar(T0 + 3 * BAR, 0.85)                                # -29%: not yet
    assert not r.killed()
    r.on_bar(T0 + 4 * BAR, 0.83)                                # -31% from 1.2
    assert r.killed() and r.must_flatten() and r.counts["kill_switch_triggered"] == 1
    assert r.filter(-1.0, 0.0, T0 + 4 * BAR) == 0.0 and r.counts["kill_switch"] == 1
    assert any(e["rule"] == "kill_switch" and "kill switch" in e["reason"] for e in r.events)
    for k in range(5, 9):
        r.on_bar(T0 + k * BAR, 0.83)
    assert r.killed()
    r.on_bar(T0 + 9 * BAR, 0.83)                                # 5 bars later
    assert not r.killed() and r.peak == 0.83
    assert r.filter(1.0, 0.0, T0 + 9 * BAR) == 1.0


def test_vol_breaker_caps_position_and_logs_reason():
    r = rm()
    assert r.filter(1.0, 0.0, T0, vol_short=0.002, vol_long=0.001) == 1.0      # 2x: fine
    assert r.filter(1.0, 0.0, T0, vol_short=0.004, vol_long=0.001) == 0.5      # 4x: capped
    assert r.filter(-1.0, 0.0, T0, vol_short=0.004, vol_long=0.001) == -0.5
    assert r.filter(0.0, 1.0, T0, vol_short=0.004, vol_long=0.001) == 0.0      # flat is never blocked
    assert r.filter(1.0, 0.0, T0, vol_short=float("nan"), vol_long=0.001) == 1.0
    assert r.counts["vol_breaker"] == 2
    assert all(e["rule"] == "vol_breaker" and "rv_16" in e["reason"] for e in r.events)


def test_disabled_risk_manager_passes_everything():
    r = RiskManager(RiskConfig(enabled=False))
    r.on_bar(T0 + BAR, 1.0)
    r.on_bar(T0 + 2 * BAR, 0.1)
    assert not r.must_flatten() and r.filter(1.0, 0.0, T0, 1.0, 0.0001) == 1.0 and not r.events


def test_events_can_be_counted_without_being_stored():
    r = RiskManager(RiskConfig(max_position=0.5), log_events=False)
    r.filter(1.0, 0.0, T0)
    assert r.counts["max_position"] == 1 and r.events == []
