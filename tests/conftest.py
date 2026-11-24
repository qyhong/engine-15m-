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
