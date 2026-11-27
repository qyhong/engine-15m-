# -*- coding: utf-8 -*-
"""Keeps one test file's import from changing another test's environment. Nothing here skips or changes a test.

The research-queue harnesses (research/queue/placebo.py, h81_audit.py, ...) set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS,
MKL_NUM_THREADS and NUMEXPR_NUM_THREADS to "1" when they are imported: right for a queue job, but in a full pytest run
the import happens at collection and the setting stays in the pytest process. tests/test_parallel_step.py then starts
a throw-away engine in a child Python, which inherits it, and on the Windows ARM64 laptop that child dies with exit
code 0xC0000005 (access violation, no output) about 15 seconds in. Found 24 Nov 2026: the file passed alone and failed
in every full run, so tools/deploy.sh stopped before deploying; the single test fails the same way when those four
variables are set by hand, and passes without them. The live box (Linux) never sets them for the engine.

So the four variables are put back to what they were before collection, once collection ends and after every test.
"""
import os

import pytest

THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
_BEFORE = dict((v, os.environ.get(v)) for v in THREAD_VARS)       # conftest is imported before any test module


def _restore():
    for v, val in _BEFORE.items():
        if val is None:
            os.environ.pop(v, None)
        else:
            os.environ[v] = val


def pytest_collection_finish(session):
    _restore()


@pytest.fixture(autouse=True)
def _thread_settings_do_not_leak_between_tests():
    yield
    _restore()


@pytest.fixture(autouse=True)
def _no_test_reads_the_real_setups_voice_state(monkeypatch, tmp_path_factory):
    """engine15/setups_voice.py's state (data/setups_voice_state.json) decides which paper book the Setups page, the
    signals and the vault feed read. A test that does not name its own file would read the real one: on a machine where
    a market is on the trail voice, tests of the targets voice would then fail (or pass for the wrong reason). Every
    test gets a path in a temp folder instead; nothing is written there unless the test's own code does."""
    from engine15 import setups_voice
    monkeypatch.setattr(setups_voice, "STATE_PATH",
                        str(tmp_path_factory.mktemp("voice") / "setups_voice_state.json"))


# The trail voice's two switches (setups_voice.TRAIL_MARKETS, vault_feed.SEND_TRAIL) are ON in the shipped code since
# think15-v5.2.12. The tests were written for, and keep testing, the default voice: every test runs with both OFF unless it
# turns them on itself (monkeypatch). The tests that check the shipped values read them from the source files
# (tests/shipped_values.py; not from here: tests/rl has a conftest of its own, so "import conftest" is ambiguous).


@pytest.fixture(autouse=True)
def _trail_switches_off_inside_tests(monkeypatch):
    from engine15 import setups_voice, vault_feed
    monkeypatch.setattr(setups_voice, "TRAIL_MARKETS", ())
    monkeypatch.setattr(vault_feed, "SEND_TRAIL", False)
