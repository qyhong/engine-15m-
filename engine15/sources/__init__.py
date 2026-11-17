# -*- coding: utf-8 -*-
"""sources -- the second ten decision cards (queued 10 Nov 2026). Each module here exposes

    GROUPS                      OrderedDict: voice name -> (card title, [feature names])
    update(log=print)           fetch / extend what it keeps under data/sources/ (network)
    features(index15, asset)    frame on the 15m index: its features (0.0 = no read) and readable columns

and follows the engine's one rule: a row may use only what was known at that 15m close.
evidence.py picks up every module listed in MODULES that imports cleanly.
"""
MODULES = ("derivs", "market", "structure", "ltf", "fib", "overnight", "xmarket", "mavg", "trendtools", "cot", "japan", "equity_events", "oil", "flows", "osc", "osc2", "osc3", "cryptox", "adr", "osc4", "osc5")      # a module that is missing or will not import is skipped
