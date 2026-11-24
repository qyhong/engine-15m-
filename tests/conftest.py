# -*- coding: utf-8 -*-
"""Test order only: nothing here skips, deselects or changes a test.

tests/test_parallel_step.py steps a throw-away engine with four worker processes in a child Python. On the 12 GB
Windows ARM64 laptop that child died with exit code 0xC0000005 (access violation, no output) twice on 24 Nov 2026
when the file ran in its alphabetical place, about 500 tests into the full suite, and passed both times it was run
alone the same day. The full suite must pass before a deploy (`tools/deploy.sh`), so these tests run FIRST, before
the pytest process has grown. Every test still runs and must pass.
"""
FIRST = ("test_parallel_step.py",)


def pytest_collection_modifyitems(session, config, items):
    head = [it for it in items if it.nodeid.replace("\\", "/").split("::")[0].endswith(FIRST)]
    if head:
        rest = [it for it in items if it not in head]
        items[:] = head + rest
