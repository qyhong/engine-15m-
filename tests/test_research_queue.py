# -*- coding: utf-8 -*-
"""Research job queue runner (research/queue/runner.py): pure logic and a few real child processes in a temp folder.

No server, no network. The guards are driven by injected disk / memory / deploy-age / clock values; the jobs are the
laptop's own Python sleeping or writing the contract's files.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "queue"))

import runner as R  # noqa: E402

PY = sys.executable
OK_JOB = ("import json,os,sys,time;o=sys.argv[1];os.makedirs(o,exist_ok=True);time.sleep({s});"
          "json.dump({{'done':1,'total':1,'est_hours_left':0}},open(os.path.join(o,'progress.json'),'w'));"
          "json.dump({{}},open(os.path.join(o,'results.json'),'w'));open(os.path.join(o,'report.md'),'w').write('ok');"
          "open(os.path.join(o,'DONE'),'w').close()")
SLEEP_JOB = "import time;time.sleep(60)"
FAIL_JOB = "import sys;print('boom');sys.exit(3)"
NODONE_JOB = "print('no marker')"


class Env:
    """Mutable probe values for one Runner."""

    def __init__(self):
        self.disk, self.mem, self.dep = 8.0, 10.0, None
        self.clock = None

    def probes(self):
        return {"disk_gb": lambda: self.disk, "mem_gb": lambda: self.mem, "deployed_age_min": lambda: self.dep,
                "now": lambda: self.clock or R.utc_now()}


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rq_test_")
        self.env = Env()

    def tearDown(self):
        for r in getattr(self, "_runners", []):
            for p in r.procs.values():
                try:
                    p["proc"].kill()
                    p["proc"].wait(10)
                    p["log"].close()
                except Exception:
                    pass
        shutil.rmtree(self.root, ignore_errors=True)

    def runner(self, workers=2):
        r = R.Runner(self.root, workers=workers, prefix=[], probes=self.env.probes(), deployed_file="/nonexistent",
                     term_grace_s=5)
        self._runners = getattr(self, "_runners", []) + [r]
        return r

    def add(self, jid, code, est=1.0, priority=50, added=None):
        out = os.path.join(self.root, "out", jid)
        job = {"id": jid, "command": [PY, "-c", code, out], "cwd": self.root, "out": out, "est_hours": est,
               "priority": priority, "added_utc": added or R.iso(R.utc_now()), "failures": 0}
        os.makedirs(os.path.join(self.root, "jobs"), exist_ok=True)
        R.write_json(os.path.join(self.root, "jobs", jid + ".json"), job)
        return job

    def where(self, jid):
        return [d for d in ("jobs", "running", "done", "failed")
                if os.path.exists(os.path.join(self.root, d, jid + ".json"))]

    def tick_until(self, r, cond, timeout=40):
        t0 = time.time()
        while time.time() - t0 < timeout:
            r.tick()
            if cond():
                return True
            time.sleep(0.2)
        return False

    # ---------------------------------------------------------------- pure logic
    def test_order_lowest_priority_then_oldest(self):
        jobs = [{"id": "c", "priority": 50, "added_utc": "2026-11-22T10:00:00Z"},
                {"id": "a", "priority": 10, "added_utc": "2026-11-22T12:00:00Z"},
                {"id": "b", "priority": 50, "added_utc": "2026-11-22T09:00:00Z"}]
        self.assertEqual([j["id"] for j in R.order_jobs(jobs)], ["a", "b", "c"])

    def test_hard_cap_two_workers(self):
        self.assertEqual(R.clamp_workers(5), 2)
        self.assertEqual(R.clamp_workers(0), 1)
        self.assertEqual(R.clamp_workers(1), 1)
        self.assertEqual(self.runner(workers=8).workers, 2)

    def test_start_guards(self):
        f = R.start_block_reason
        self.assertIsNone(f(8.0, 10.0, False, False, None))
        self.assertIsNone(f(8.0, 10.0, False, False, 46))
        self.assertIn("disk", f(3.9, 10.0, False, False, None))
        self.assertIsNone(f(4.0, 3.0, False, False, None))
        self.assertIn("memory", f(8.0, 2.9, False, False, None))
        self.assertIn("deployed", f(8.0, 10.0, False, False, 44))
        self.assertIn("STOP", f(8.0, 10.0, True, False, None))
        self.assertIn("PAUSE", f(8.0, 10.0, False, True, None))

    def test_stop_guards(self):
        self.assertIsNone(R.stop_all_reason(3.0, False))
        self.assertIn("disk", R.stop_all_reason(1.9, False))
        self.assertIn("STOP", R.stop_all_reason(8.0, True))
        self.assertFalse(R.memory_stop_needed(2.0))
        self.assertTrue(R.memory_stop_needed(1.4))
        y = R.youngest([{"id": "a", "started_utc": "2026-11-22T10:00:00Z"},
                        {"id": "b", "started_utc": "2026-11-22T11:00:00Z"}])
        self.assertEqual(y["id"], "b")

    def test_over_time_three_times_est_min_two_hours(self):
        now = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
        self.assertFalse(R.is_over_time("2026-11-22T10:30:00Z", 0.1, now))     # 1.5 h < 2 h minimum
        self.assertTrue(R.is_over_time("2026-11-22T09:59:00Z", 0.1, now))      # 2 h 1 min
        self.assertFalse(R.is_over_time("2026-11-22T03:00:00Z", 3.0, now))     # 9 h = 3 x 3 h, not over
        self.assertTrue(R.is_over_time("2026-11-22T02:59:00Z", 3.0, now))

    def test_backlog_hours(self):
        queued = [{"est_hours": 10}, {"est_hours": 20}]
        self.assertEqual(R.backlog_hours(queued, [6.0], 2), 18.0)
        self.assertEqual(R.backlog_hours(queued, [6.0], 1), 36.0)
        self.assertEqual(R.backlog_hours(queued, [], 9), 15.0)                  # workers capped at 2
        now = R.utc_now()
        job = {"est_hours": 5, "started_utc": R.iso(now - timedelta(hours=2))}
        self.assertAlmostEqual(R.running_hours_left(job, None, now), 3.0, places=2)
        self.assertEqual(R.running_hours_left(job, {"est_hours_left": 1.25}, now), 1.25)

    def test_retry_at_most_once(self):
        self.assertEqual(R.after_failure({"failures": 1}), "retry")
        self.assertEqual(R.after_failure({"failures": 2}), "failed")
        self.assertEqual(R.after_failure({"failures": 3}), "failed")

    # ---------------------------------------------------------------- real children
    def test_job_completes_to_done_with_status(self):
        self.add("ok1", OK_JOB.format(s=0.5), est=2)
        r = self.runner()
        self.assertTrue(self.tick_until(r, lambda: self.where("ok1") == ["done"]))
        r.write_status()
        st = R.read_json(os.path.join(self.root, "status.json"))
        self.assertEqual(st["done"], 1)
        self.assertEqual(st["queued"], 0)
        self.assertEqual(st["backlog_hours"], 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "logs", "ok1.log")))

    def test_failure_retried_once_then_failed(self):
        self.add("bad", FAIL_JOB)
        r = self.runner()
        self.assertTrue(self.tick_until(r, lambda: self.where("bad") == ["failed"]))
        job = R.read_json(os.path.join(self.root, "failed", "bad.json"))
        self.assertEqual(job["failures"], 2)
        self.assertEqual(job["last_exit_code"], 3)
        self.assertTrue(any("boom" in ln for ln in job["last_log_lines"]))
        with open(os.path.join(self.root, "logs", "bad.log"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("=== "), 4)                         # two starts, two exits: no third run

    def test_exit_zero_without_done_marker_is_a_failure(self):
        self.add("nodone", NODONE_JOB)
        r = self.runner()
        self.assertTrue(self.tick_until(r, lambda: self.where("nodone") == ["failed"]))
        self.assertIn("no DONE", R.read_json(os.path.join(self.root, "failed", "nodone.json"))["last_failure"])

    def test_never_more_than_two_at_once(self):
        for i in range(4):
            self.add("s%d" % i, SLEEP_JOB)
        r = self.runner(workers=5)
        for _ in range(5):
            r.tick()
        self.assertEqual(len(r.procs), 2)
        self.assertEqual(len(os.listdir(os.path.join(self.root, "running"))), 2)
        self.assertEqual(len([n for n in os.listdir(os.path.join(self.root, "jobs")) if n.endswith(".json")]), 2)

    def test_crash_recovery_requeues_running_job(self):
        p = subprocess.Popen([PY, "-c", "pass"])
        p.wait()
        job = self.add("crashed", SLEEP_JOB)
        os.remove(os.path.join(self.root, "jobs", "crashed.json"))
        R.write_json(os.path.join(self.root, "running", "crashed.json"),
                     dict(job, pid=p.pid, started_utc="2026-11-22T00:00:00Z"))
        r = self.runner()
        r.recover()
        self.assertEqual(self.where("crashed"), ["jobs"])
        back = R.read_json(os.path.join(self.root, "jobs", "crashed.json"))
        self.assertNotIn("pid", back)
        self.assertEqual(back["failures"], 0)                                   # a crash is not a failure

    def test_nothing_starts_under_hold_guards(self):
        self.add("held", SLEEP_JOB)
        r = self.runner()
        for setup, word in ((lambda: setattr(self.env, "mem", 2.5), "memory"),
                            (lambda: setattr(self.env, "disk", 3.5), "disk"),
                            (lambda: setattr(self.env, "dep", 10.0), "deployed")):
            self.env.disk, self.env.mem, self.env.dep = 8.0, 10.0, None
            setup()
            r.tick()
            self.assertEqual(len(r.procs), 0)
            self.assertIn(word, r.hold_reason)
        open(os.path.join(self.root, "PAUSE"), "w").close()
        self.env.disk, self.env.mem, self.env.dep = 8.0, 10.0, None
        r.tick()
        self.assertEqual(len(r.procs), 0)
        os.remove(os.path.join(self.root, "PAUSE"))
        r.tick()
        self.assertEqual(len(r.procs), 1)

    def test_low_disk_stops_and_requeues(self):
        self.add("big", SLEEP_JOB)
        r = self.runner()
        r.tick()
        self.assertEqual(self.where("big"), ["running"])
        self.env.disk = 1.5
        self.assertTrue(self.tick_until(r, lambda: self.where("big") == ["jobs"]))
        job = R.read_json(os.path.join(self.root, "jobs", "big.json"))
        self.assertEqual(job["failures"], 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "LAST_GUARD_STOP.txt")))
        r.tick()
        self.assertEqual(len(r.procs), 0)                                       # 1.5 GB < 4 GB: nothing restarts

    def test_low_memory_stops_youngest(self):
        self.add("old", SLEEP_JOB, added="2026-11-22T01:00:00Z")
        self.add("new", SLEEP_JOB, added="2026-11-22T02:00:00Z")
        r = self.runner()
        r.tick()
        self.assertEqual(len(r.procs), 2)
        r.procs["old"]["job"]["started_utc"] = "2026-11-22T03:00:00Z"
        r.procs["new"]["job"]["started_utc"] = "2026-11-22T04:00:00Z"
        self.env.mem = 1.2
        self.assertTrue(self.tick_until(r, lambda: self.where("new") == ["jobs"]))
        self.assertEqual(self.where("old"), ["running"])

    def test_over_time_fails_without_retry(self):
        self.add("slow", SLEEP_JOB, est=0.5)
        r = self.runner()
        r.tick()
        self.env.clock = R.utc_now() + timedelta(hours=2, minutes=5)
        self.assertTrue(self.tick_until(r, lambda: self.where("slow") == ["failed"]))
        job = R.read_json(os.path.join(self.root, "failed", "slow.json"))
        self.assertIn("over time", job["last_failure"])
        self.assertEqual(job["failures"], 1)

    def test_stop_file_requeues_and_exits(self):
        self.add("st", SLEEP_JOB)
        r = self.runner()
        r.tick()
        open(os.path.join(self.root, "STOP"), "w").close()
        self.assertFalse(r.tick())
        r.shutdown("STOP file present")
        self.assertEqual(self.where("st"), ["jobs"])
        self.assertEqual(R.read_json(os.path.join(self.root, "status.json"))["runner"]["exited"], "STOP file present")

    def test_laptop_tool_never_builds_removal_outside_queue(self):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
        import research_queue as T
        self.assertTrue(T._rm_cmd("/data/research_queue/STOP").endswith("/data/research_queue/STOP"))
        for bad in ("/data/research_queue", "/data/research_queue/", "/data/mind15/x", "/data/research_queue/../mind15",
                    "/", "/data/research_queue_x/a"):
            with self.assertRaises(SystemExit):
                T._rm_cmd(bad, recursive=True)
        for bad in (("..", "x"), ("/etc",), ("a\\b",), ("",)):
            with self.assertRaises(SystemExit):
                T._remote_path(*bad)
        job = T.build_job("H70_a", "harness_x", "H70", "abcdef123456", 3.5, 10)
        self.assertEqual(job["command"][-1], "/data/research_queue/out/H70_a")
        self.assertEqual(job["cwd"], "/data/research_queue/code/abcdef123456")
        self.assertIn("/data/mind15/research/out/h60_regime_exits/fits_today", job["command"])


if __name__ == "__main__":
    unittest.main()
