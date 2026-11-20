# -*- coding: utf-8 -*-
"""config -- THE ONE CONFIG BLOCK of the 15-minute thinking engine.

Every constant the engine reads lives here, declared once, before the first replay.
A change to any of them is a new version of the thought process (bump "version"), so a
post-mortem can always tell which rules made a decision.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "out")
JOURNAL_DIR = os.path.join(ROOT, "journal")

# The AI Trading Bot estate (read-only reference: its strategy library and trend map).
ESTATE = os.environ.get("ENGINE15_ESTATE", os.path.join(os.path.dirname(ROOT), "eth-signal-bot"))
LIBRARY_JSON = os.path.join(ESTATE, "research", "local", "library", "strategy_library.json")

# Said once in the journal (each market group's next entry) after "version" changes (live.step_group).
VERSION_NOTE = ("think15-v5.2.7: on USDJPY the main book now sells half the position at Target 1, moves the stop of "
                "the rest to the entry price, and sells the rest at Target 2 (the Setups book's exit rule). The S&P 500 "
                "keeps v5.2.6 (half at Target 1, the rest runs). Entries, sizing, flips, the 4-session mandate and "
                "the other six markets are unchanged.")

CFG = {
    "version": "think15-v5.2.7",      # v5.2.7 (20 Nov 2026): USDJPY's main book sells half at Target 1 and the rest at Target 2
                                      #   ("half_t1" and "t2_exit", below); owner, after the long of 10 Nov passed both targets and
                                      #   closed at its entry: "Sell at target"; the mandate stays ("Still follow our rules").
                                      # v5.2.6 (20 Nov 2026): the S&P 500 main book closes half at Target 1, stop of the rest to the
                                      #   entry ("half_t1", below); owner: "The snp 500 should close half of the profit now ... as
                                      #   TP1 already achieve", then chose "Rest runs, stop at entry". Other markets unchanged.
                                      # v5.2.5 (19 Nov 2026): the FX main book (USDJPY) moves its stop to the entry once Target 1
                                      #   trades ("be_t1", below); owner: "Follow the target", then chose "Stop to entry after T1".
                                      #   The first change to a main-book EXIT rule. Every other market unchanged.
                                      # v5.2.4 (17 Nov 2026): card batch 4, five reading-only cards for every market (sources/osc5.py:
                                      #   Fisher Transform, Ultimate Oscillator, TRIX, linear-regression channel, Mass Index); owner
                                      #   "let's continue pending tasks". Rules and votes unchanged.
                                      # v5.2.3 (16 Nov 2026): six reading-only cards for every market: daily range budget and range
                                      #   breaks (sources/adr.py) and card batch 3 (sources/osc4.py: Williams %R, Chaikin money flow/OBV,
                                      #   Elder-Ray, pivot points, RSI divergence); owner "Yes". Rules and votes unchanged.
                                      # v5.2.2 (15 Nov 2026): six crypto reading-only cards (sources/cryptox.py: Deribit options flow,
                                      #   Korea premium, CME gap (spot proxy), BTC dominance, spot vs perp, cross-exchange funding/OI);
                                      #   owner "Yes". Rules and votes unchanged.
                                      # v5.2.1 (15 Nov 2026): CCI card, 15m to daily, all markets, reading-only (sources/osc3.py);
                                      #   owner: "For commodities like metal. Should include CCI". Rules and votes unchanged.
                                      # v5.2 (15 Nov 2026): trust cap - no voting card holds more than 40% of the say (trust_cap);
                                      #   owner: "set it as 40%" (chosen by the owner, not by a test; H43 records the history comparison).
                                      # v5.1.2 (15 Nov 2026): seven reading-only cards, card pipeline batches 1-2 (sources/osc.py:
                                      #   Supertrend, StochRSI; sources/osc2.py: Parabolic SAR, Money Flow Index, volume profile,
                                      #   Heikin-Ashi, Aroon/Vortex); owner "ok". Rules and votes unchanged.
                                      # v5.1.1 (13 Nov 2026): four more crypto cards from sources/flows.py (Binance archive positioning,
                                      #   Bitfinex margin, CME positioning, on-chain); owner: "Yes" to wiring them in. Rules unchanged.
                                      # v5.1 (11 Nov 2026): each market group votes with its own best-rated cards (voting_by_group, below)
                                      # v5 (11 Nov 2026): higher-timeframe bias and release guard, below        # v2 (10 Nov 2026): the voices learn from ALL graded history, weekly
    "assets": ("BTCUSDT", "ETHUSDT"),  # the crypto market: the replay and the cards were built on these two
    # v4.1 (11 Nov 2026): four more markets, each its own $10,000 paper book (owner's request).
    # Markets with different trading hours cannot share one evidence index, so each group below
    # is thought about separately (its own voices, trust and odds); the crypto group is unchanged.
    "universes": (("crypto", ("BTCUSDT", "ETHUSDT")),
                  ("metals", ("XAUUSD", "XAGUSD")),          # gold and silver: same hours, each reads the other
                  ("fx", ("USDJPY",)),
                  ("index", ("SPX",)),                       # S&P 500 cash hours: 26 sessions a day
                  ("energy", ("WTI", "BRENT"))),             # oil (11 Nov 2026): WTI and Brent read each other
    "crypto": ("BTCUSDT", "ETHUSDT"),  # only these get the crypto-only sources (funding, book, ETF, ...)
    "asset_cost": {"XAUUSD": 0.0002, "XAGUSD": 0.0003, "USDJPY": 0.0001, "SPX": 0.0002,
                   "WTI": 0.0004, "BRENT": 0.0004},   # a side; else cost_side (oil: ~3 cents spread on ~$90)
    "group_horizon": {"index": 26},
    # leverage (owner, 11 Nov 2026): caps per asset; the engine sizes each new trade so its stop
    # risks about risk_per_trade of equity, between 1x and the cap (backtest.leverage). Crypto: 1x.
    "max_leverage": {"USDJPY": 100.0, "SPX": 5.0, "XAUUSD": 5.0, "XAGUSD": 5.0,
                     "WTI": 5.0, "BRENT": 5.0},      # oil: 5x, the same cap as the other commodities (my choice)
    "risk_per_trade": 0.02,
    # honest fills (11 Nov 2026): these markets' live bars arrive ~10 minutes after they close, so a decision
    # at a bar's close can only be acted on one bar later; their orders fill one open later than the others
    "fill_delay": {"XAUUSD": 1, "XAGUSD": 1, "WTI": 1, "BRENT": 1},
    # total-risk cap (11 Nov 2026, the owner's list item 5): what all open main-book trades would lose if every
    # stop were hit at once may not exceed this share of the books' total equity; a new entry that would go over
    # is shrunk to fit (or skipped when nothing is left). With ~2% risk a trade, it binds only when most books
    # are in at once. The shadow and strategy books are not capped (they compare rules).
    "risk_cap_pct": 10.0,   # grade an S&P call within one trading day (26 sessions), not 96
    "bar_ms": 900000,                 # one session = one closed 15-minute bar
    "data_base_url": "https://data-api.binance.vision",   # Binance spot public market data
    "data_start": "2019-01-01",       # history kept (evidence warm-up comes before the birth date)
    "birth": "2020-01-01",            # the engine learns from nothing before this date
    # ---- costs (the estate's HF-lane convention: taker, a flip is two sides)
    "cost_side": 0.0010,
    # ---- what "rewarding" means: the triple barrier
    "barrier_atr": 1.5,               # barrier = 1.5 x ATR14 of the 1-hour chart, each side
    "horizon": 96,                    # a call is graded within 96 sessions (24 hours)
    # ---- the mandate
    "idle_max": 4,                    # at most 4 sessions (1 hour) flat in a row
    "theta_enter": 0.05,              # a side is "rewarding" at P(win) - P(lose) >= 5 points
    "theta_enter_shock": 0.10,        # ... 10 points when risk is high
    "theta_flip": 0.10,               # leave a held side for the other at 10 points against
    "shock_ratio": 2.0,               # high risk: last hour's 15m range >= 2x its 24h norm
    "stop_units": 2.0,                # protective stop = 2 barriers (3 x ATR 1H) from the fill
    # v5.2.5 (owner, 19 Nov 2026, of the USDJPY long that was past Target 1 with its stop still below entry: "Follow the
    # target"; of the two readings offered the owner chose "Stop to entry after T1"). Markets listed here: once a bar trades
    # through the trade's Target 1 (live.plan_targets, set at entry) the main book's stop moves to the entry price, live
    # from the next bar, never looser (backtest.run_book, exits.be_stop; a stop-out there is "STOP_BE"). History (H36,
    # research/out/exits/trail_study.md, in-sample, 1 of 15 exit variants): on USDJPY +$27,238 against +$19,209 for
    # holding, the only variant ahead of holding there; pooled over all eight markets it made less than holding, which
    # is why the list is USDJPY alone. Adopted on the owner's call, not on a passed test. The shadow books are
    # unchanged: their "main" copy keeps hold-to-stop-or-flip, so the old rule stays on the forward record beside it.
    # v5.2.6 (20 Nov 2026): the S&P 500 joins the list, with half_t1 below.
    "be_t1": ("USDJPY", "SPX"),
    # v5.2.6 (owner, 20 Nov 2026, of the S&P short that was past Target 1 with its stop still above the entry: "The snp
    # 500 should close half of the profit now under mind 15 as TP1 already achieve"; for the other half the owner chose
    # "Rest runs, stop at entry" over closing it at Target 2 or keeping full size). Markets listed here (they must be
    # in be_t1 too): in the bar that trades through Target 1 half the position is closed AT Target 1, the stop of the
    # rest goes to the entry, and the rest leaves at that stop or on a flip (backtest.run_book, exits.PART). The half
    # is a closed trade of its own at once ("T1"); the rest is a second row when it closes. A trade
    # already past its Target 1 when the rule began has its half closed at the next open (live.adopt_be_t1). Adopted
    # on the owner's call. This exact combination was not in H36's grid; its history read is H59 (registered the same
    # day, descriptive, gates nothing). The nearest H36 numbers on the S&P: holding +$6,816, stop-to-entry at full
    # size +$6,334, half at Target 1 with the rest out at Target 2 (b_targets) +$1,018.
    # v5.2.7 (20 Nov 2026): USDJPY joins, with t2_exit below.
    "half_t1": ("SPX", "USDJPY"),
    # v5.2.7 (owner, 20 Nov 2026). The USDJPY long of 10 Nov traded through Target 1 and Target 2 on 11 Nov, went on to
    # 160.19 and was closed at its entry nine days later (research/out/usdjpy_postmortem_20261120.md). Asked whether the
    # open USDJPY long should sell at its targets, the owner: "1. Sell at target". Asked whether a trade that ended at a
    # target should be exempt from the forced re-entry: "2. Still follow our rules. Our goal is to ace the directional
    # setup at highest probability. 4 session (max 1 hour) flat is good enough to re-read the market condition and
    # choose best probability option" (so the mandate is unchanged). Markets listed here (they must be in half_t1
    # too): once Target 1 has traded, a bar that trades through Target 2 closes what is left AT Target 2 ("T2"). With
    # be_t1 and half_t1 this is the Setups book's exit rule (b_targets) on the main book's own entries. Adopted on the
    # owner's call, not on a passed test: on history b_targets earned less than holding on USDJPY (H36: +$2,939 against
    # +$19,209; H59's re-run -$394 against +$7,288). The shadow "main" copy keeps holding as the forward comparison.
    # H60 (registered the same day) reads exits by regime per market and may change this list later.
    "t2_exit": ("USDJPY",),
    # v3 (owner, 10 Nov 2026): HOLD when risk is high and the edge is gone, instead of stepping
    # aside. In the replay the step-aside rule made about 770 exits and 1,000 forced re-entries a coin.
    "step_aside": False,
    # v4 (10 Nov 2026), from the post-mortem of a week in which the engine leaned long on 77% of
    # calls while the market fell and was right 36% of the time. Three causes, three fixes:
    #  even_prior      every voice starts each call at even odds between up and down. Before, each
    #                  carried history's slight excess of up-moves as a standing lean to the long side.
    #  silent voices   a voice with no reading at all on a session (no answer from the owner, no
    #                  order-book snapshot ...) has no vote on that session (backtest.prepare).
    #  trend_tiebreak  when the mandate forces a side and neither clears the bar, take the side of
    #                  the 4h and daily trend, not the sign of an edge too small to mean anything.
    "even_prior": True,
    "trend_tiebreak": True,
    # v5 (11 Nov 2026), from the owner's post-mortem of the BTC longs of 10 Nov: BTC was below its
    # 1h, 4h and daily moving averages with every timeframe trending down, ETH's short worked, and
    # the engine went long 15 minutes before the CPI print. Owner: "The bias should go for short
    # rather than long" and "it never notices the CPI ... and just jumps into entry".
    #  htf_bias       when 1h, 4h and 1d all trend one way and price is on that side of the 1h EMA50
    #                 and the 4h EMA20/EMA50: forced entries take that side; an entry against it needs
    #                 theta_counter (15 pts) instead of 5; a position against it with less than a
    #                 5-pt edge for it is flipped to the bias side.
    #  release_guard  in the hour before a high-impact US release: no new position, no flip (H2).
    # History check before adoption (BTC and ETH 2019-2026): in the bias state the next 1.5-ATR move
    # went the bias way 49-53% of the time, about a coin flip at the 24h horizon. Adopted on the
    # owner's call as a risk rule (do not fight every timeframe), graded forward as hypothesis H4.
    "htf_bias": True,
    "theta_counter": 0.15,
    "release_guard": True,
    # v3 (owner, 10 Nov 2026): only the ten best-rated cards VOTE on direction (research/card_rating.json);
    # the other cards are still read, journaled and shown. With all 20 voting the replay's accuracy
    # on claimed-edge calls fell from 51.7% to 50.0%. The owner's own view always has a vote.
    "voting": ("regime", "momentum", "meanrev", "pullback", "levels", "cbprem", "flow", "breadth", "trend",
               "strategies", "stable", "basis", "owner"),
    # ---- learning
    # v1 refitted daily on the last 180 days and called direction at 50%: it chased noise and
    # lost the small steady effects the raw readings show. research/exp_memory.py (10 Nov 2026):
    # learning from all history with a heavier ridge lifts the most confident 5% of calls to
    # about 55% in both 2020-2023 and 2024 on. That rule is v2.
    "refit_every": 672,               # every voice is refitted once a week
    "train_days": 4000,               # on ALL graded calls since train_floor
    "train_step": 16,                 # one training row per 4 hours (calls overlap)
    "min_train_rows": 400,            # no model, no trade, before this many graded rows
    "l2": 100.0,                      # ridge on the weights (sum loss)
    "train_floor": "2020-01-01",      # the first call a voice may learn from
    "trust_eta": 0.2,                 # Hedge learning rate on graded log-loss
    "trust_halflife": 960,            # trust forgets with a 10-day half-life (in sessions)
    "trust_cap": 0.40,                # v5.2 (owner, 15 Nov 2026: "set it as 40%"): no voting card above 40% of the say
    "trust_floor": 0.02,              # no voice is ever fully ignored
}

# v5.1 (11 Nov 2026, the owner's list item 4): card ratings per market. The ten voting cards above were chosen
# from a crypto-only rating and used for every market, so gold/silver, USDJPY, the S&P 500 and oil voted with
# several crypto-only cards that read nothing there, and the ~25 newer cards never voted anywhere.
# research/rate_cards.py rates every card that applies to a group by exp_memory.py's method (a card's steadiest
# raw reading, direction accuracy in the first and second half of 2020-2026, the group's assets pooled;
# research/out/card_rating_<group>.json/.md). Each group votes with its top ten cards by the worse half, only
# those above 50.5% (at least the three best), plus the owner's voice. Crypto keeps exactly its v3 list (owner:
# "top ten cards vote", from research/card_rating.json). Switch: group_voting False = every group uses "voting".
CFG["group_voting"] = True
# Ratings of 11 Nov 2026 (2020-01-01 .. 11 Nov 2026). Every group had ten cards above the floor. Crypto's new
# rating would swap six cards (in: ribbon, trend quality, KAMA, intraday levels, moving averages, Ichimoku; out:
# order flow, breadth, timeframe strength, strategies, stablecoins, basis): reported to the owner, not applied.
CFG["voting_by_group"] = {
    "crypto": CFG["voting"],
    "metals": ("volx", "ichimoku", "momentum", "meanrev", "pullback", "goldetf", "structure", "trend", "regime",
               "kama", "news", "macro", "mavg", "owner"),
    "fx": ("setups", "regime", "strategies", "clock", "mavg", "rates", "trendq", "momentum", "meanrev", "pullback",
           "levels", "trend", "owner"),
    "index": ("setups", "news", "macro", "mavg", "overnight", "trendq", "levels", "regime", "intraday", "fib",
              "rates", "owner"),
    "energy": ("oilvol", "regime", "setups", "oilspread", "fib", "mavg", "levels", "kama", "candles", "trendq",
               "owner"),
}


def voting_for(group, cfg=None):
    """The voices that vote for this market group (CFG["voting"] when group voting is off or unrated)."""
    cfg = CFG if cfg is None else cfg
    if cfg.get("group_voting") and group in (cfg.get("voting_by_group") or {}):
        return tuple(cfg["voting_by_group"][group])
    return cfg["voting"]
