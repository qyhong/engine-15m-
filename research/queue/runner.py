# -*- coding: utf-8 -*-
"""Research job queue runner for the Singapore box (standard library only).

Runs ON THE SERVER with /data/venv-research/bin/python, from /data/research_queue/runner.py. It works through the
job files in <root>/jobs/ one after another (at most 2 at a time), unattended, and gets out of the live engine's way:
every child runs at nice 19 (ionice idle when allowed), single-threaded BLAS, and the guards below stop or hold jobs
when the box runs short of disk or memory, when the engine was just deployed, or when STOP / PAUSE files appear.

It is NOT a systemd service. After a reboot start it again (tools/research_queue.py start). See README.md here.

Folder layout under <root> (default /data/research_queue):
  jobs/      queued job files <ID>.json      running/  job files of running jobs (with pid, started_utc)
  done/      finished jobs                   failed/   failed jobs (exit code, last log lines)
  logs/      <ID>.log (child stdout+stderr)  out/      <ID>/ job outputs (progress.json, results.json, DONE)
  code/      <commit>/ code snapshots        status.json, runner.pid, runner.lock, runner.log, STOP, PAUSE
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

DEFAULT_ROOT = "/data/research_queue"
DEPLOYED_FILE = "/data/mind15/DEPLOYED.json"
HARD_MAX_WORKERS = 2                       # the engine needs a free CPU and the vault another
DISK_HOLD_GB = 4.0                         # free space on /data under this: start nothing new
DISK_STOP_GB = 2.0                         # under this: stop running jobs (they are resumable)
MEM_HOLD_GB = 3.0                          # available memory under this: start nothing new
MEM_STOP_GB = 1.5                          # under this: stop the youngest job
DEPLOY_QUIET_MIN = 45                      # engine deployed less than this ago: start nothing new
OVERTIME_FACTOR = 3.0                      # a run longer than 3 x est_hours ...
OVERTIME_MIN_H = 2.0                       # ... (at least 2 hours) is stopped and failed "over time"
MAX_FAILURES = 2                           # a failing job runs at most twice (one automatic retry)
TERM_GRACE_S = 60                          # after SIGTERM, SIGKILL the job's process group if still alive
MEM_STOP_SPACING_S = 60                    # stop at most one job per minute for memory
TICK_S = 5
STATUS_EVERY_S = 60
CHILD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
SUBDIRS = ("jobs", "running", "done", "failed", "logs", "out", "code", "incoming")


# ----------------------------------------------------------------------------------------------- small helpers
def utc_now():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def tail_lines(path, n=20):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 16384))
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    return data.splitlines()[-n:]


def job_out_dir(job):
    if job.get("out"):
        return job["out"]
    cmd = job.get("command") or []
    for i, a in enumerate(cmd[:-1]):
        if a == "--out":
            return cmd[i + 1]
    return None


# ----------------------------------------------------------------------------------------------- pure logic (tested)
def order_jobs(jobs):
    """Lowest priority number first, then oldest added_utc, then id."""
    return sorted(jobs, key=lambda j: (float(j.get("priority", 50)), j.get("added_utc") or "", j.get("id") or ""))


def clamp_workers(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = HARD_MAX_WORKERS
    return max(1, min(HARD_MAX_WORKERS, n))


def start_block_reason(free_disk_gb, mem_avail_gb, stop_file, pause_file, deployed_age_min):
    """Why no new job may start now, or None. deployed_age_min is None when the deploy file is absent."""
    if stop_file:
        return "STOP file present"
    if pause_file:
        return "PAUSE file present"
    if free_disk_gb is not None and free_disk_gb < DISK_HOLD_GB:
        return "free disk %.1f GB < %.1f GB" % (free_disk_gb, DISK_HOLD_GB)
    if mem_avail_gb is not None and mem_avail_gb < MEM_HOLD_GB:
        return "available memory %.1f GB < %.1f GB" % (mem_avail_gb, MEM_HOLD_GB)
    if deployed_age_min is not None and deployed_age_min < DEPLOY_QUIET_MIN:
        return "engine deployed %.0f min ago (< %d min)" % (deployed_age_min, DEPLOY_QUIET_MIN)
    return None


def stop_all_reason(free_disk_gb, stop_file):
    """Why every running job must stop now, or None."""
    if stop_file:
        return "STOP file present"
    if free_disk_gb is not None and free_disk_gb < DISK_STOP_GB:
        return "free disk %.1f GB < %.1f GB" % (free_disk_gb, DISK_STOP_GB)
    return None


def memory_stop_needed(mem_avail_gb):
    return mem_avail_gb is not None and mem_avail_gb < MEM_STOP_GB


def youngest(running):
    """The running job that started last (the one to stop for memory)."""
    if not running:
        return None
    return max(running, key=lambda j: (j.get("started_utc") or "", j.get("id") or ""))


def over_time_limit_h(est_hours):
    try:
        est = float(est_hours)
    except (TypeError, ValueError):
        est = 0.0
    return max(OVERTIME_MIN_H, OVERTIME_FACTOR * est)


def is_over_time(started_utc, est_hours, now):
    started = parse_iso(started_utc) if isinstance(started_utc, str) else started_utc
    if started is None:
        return False
    return (now - started).total_seconds() / 3600.0 > over_time_limit_h(est_hours)


def running_hours_left(job, progress, now):
    """est_hours_left from the job's progress.json, else est_hours minus the time it has run."""
    if isinstance(progress, dict):
        try:
            v = float(progress.get("est_hours_left"))
            if v >= 0:
                return v
        except (TypeError, ValueError):
            pass
    started = parse_iso(job.get("started_utc"))
    ran = (now - started).total_seconds() / 3600.0 if started else 0.0
    return max(0.0, float(job.get("est_hours") or 0) - ran)


def backlog_hours(queued, running_left, workers):
    """(sum of est_hours of queued jobs + sum of hours left of running jobs) / workers."""
    total = sum(float(j.get("est_hours") or 0) for j in queued) + sum(float(h or 0) for h in running_left)
    return round(total / clamp_workers(workers), 2)


def after_failure(job):
    """'retry' (back to the queue once) or 'failed'. job['failures'] already counts the failure just seen."""
    return "retry" if int(job.get("failures", 0)) < MAX_FAILURES else "failed"


def succeeded(exit_code, out_dir):
    return exit_code == 0 and bool(out_dir) and os.path.isfile(os.path.join(out_dir, "DONE"))


# ----------------------------------------------------------------------------------------------- probes (server)
def probe_free_disk_gb(path):
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize / 1e9
    except (AttributeError, OSError):
        return None


def probe_mem_avail_gb():
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024 / 1e9
    except OSError:
        pass
    return None


def probe_deployed_age_min(path, now_ts):
    try:
        return (now_ts - os.path.getmtime(path)) / 60.0
    except OSError:
        return None


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def proc_cmdline(pid):
    try:
        with open("/proc/%d/cmdline" % int(pid), "rb") as f:
            return f.read().replace(b"\0", b" ").decode("utf-8", "replace")
    except (OSError, ValueError, TypeError):
        return ""


def ionice_ok():
    if not shutil.which("ionice"):
        return False
    try:
        return subprocess.run(["ionice", "-c3", "true"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ----------------------------------------------------------------------------------------------- the runner
class Runner:
    def __init__(self, root, workers=HARD_MAX_WORKERS, prefix=None, probes=None, deployed_file=DEPLOYED_FILE,
                 term_grace_s=TERM_GRACE_S, log_to_stdout=False):
        self.root = os.path.abspath(root)
        self.workers = clamp_workers(workers)
        self.requested_workers = workers
        if prefix is None:
            prefix = ["nice", "-n", "19"] + (["ionice", "-c3"] if ionice_ok() else [])
        self.prefix = list(prefix)
        self.deployed_file = deployed_file
        self.term_grace_s = term_grace_s
        self.log_to_stdout = log_to_stdout
        p = probes or {}
        self.now = p.get("now", utc_now)
        self.disk_gb = p.get("disk_gb", lambda: probe_free_disk_gb(self.root))
        self.mem_gb = p.get("mem_gb", probe_mem_avail_gb)
        self.deployed_age_min = p.get("deployed_age_min",
                                      lambda: probe_deployed_age_min(self.deployed_file, time.time()))
        self.procs = {}            # id -> {"proc", "job", "log", "term_at", "stop_kind", "stop_reason"}
        self.started = utc_now()
        self.hold_reason = None
        self.last_mem_stop = 0.0
        self.last_status = 0.0
        self.dirty = True
        for d in SUBDIRS:
            os.makedirs(self.d(d), exist_ok=True)

    # paths
    def d(self, *parts):
        return os.path.join(self.root, *parts)

    def log(self, msg):
        line = "%s  %s" % (iso(utc_now()), msg)
        if self.log_to_stdout:
            print(line, flush=True)
        try:
            with open(self.d("runner.log"), "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass

    def job_files(self, sub):
        out = []
        try:
            names = sorted(os.listdir(self.d(sub)))
        except OSError:
            return out
        for n in names:
            if n.endswith(".json"):
                j = read_json(self.d(sub, n))
                if isinstance(j, dict) and ID_RE.match(str(j.get("id", ""))) and n == j["id"] + ".json":
                    out.append(j)
        return out

    def move(self, job, src, dst, extra=None):
        self.dirty = True
        job = dict(job)
        if extra:
            job.update(extra)
        write_json(self.d(dst, job["id"] + ".json"), job)
        if src != dst:
            try:
                os.remove(self.d(src, job["id"] + ".json"))
            except OSError:
                pass
        return job

    # recovery after a crash or reboot
    def recover(self):
        for job in self.job_files("running"):
            pid = job.get("pid")
            marker = job_out_dir(job) or job["id"]
            if pid and pid_alive(pid) and marker in proc_cmdline(pid):
                self.log("recover: %s still alive as orphan pid %s, stopping it (it resumes)" % (job["id"], pid))
                self._signal_group(int(pid), signal.SIGTERM)
                t0 = time.time()
                while pid_alive(pid) and marker in proc_cmdline(pid) and time.time() - t0 < self.term_grace_s:
                    time.sleep(1)
                if pid_alive(pid) and marker in proc_cmdline(pid):
                    self._signal_group(int(pid), getattr(signal, "SIGKILL", signal.SIGTERM))
            self.log("recover: %s was running with no live process, back to the queue" % job["id"])
            job.pop("pid", None)
            job.pop("started_utc", None)
            self.move(job, "running", "jobs", {"note": "requeued after runner restart " + iso(utc_now())})

    @staticmethod
    def _signal_group(pid, sig):
        try:
            if hasattr(os, "killpg"):
                os.killpg(pid, sig)
            else:
                os.kill(pid, sig)
        except OSError:
            pass

    # start / stop
    def start_job(self, job):
        jid = job["id"]
        cwd = job.get("cwd") or self.root
        logp = self.d("logs", jid + ".log")
        env = dict(os.environ)
        env.update(CHILD_ENV)
        env["RESEARCH_QUEUE_JOB"] = jid
        out = job_out_dir(job)
        if out:
            os.makedirs(out, exist_ok=True)
        lf = open(logp, "ab")
        lf.write(("\n=== %s start attempt %d: %s (cwd %s)\n"
                  % (iso(utc_now()), int(job.get("failures", 0)) + 1, " ".join(job["command"]), cwd)).encode())
        lf.flush()
        try:
            proc = subprocess.Popen(self.prefix + list(job["command"]), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as e:
            lf.write(("=== could not start: %s\n" % e).encode())
            lf.close()
            job["failures"] = int(job.get("failures", 0)) + 1
            self.finish_failed(job, "jobs", None, "could not start: %s" % e)
            return
        job = self.move(job, "jobs", "running", {"pid": proc.pid, "started_utc": iso(self.now())})
        self.procs[jid] = {"proc": proc, "job": job, "log": lf, "term_at": None, "stop_kind": None,
                           "stop_reason": None}
        self.log("start %s pid %d (est %.2f h)" % (jid, proc.pid, float(job.get("est_hours") or 0)))

    def request_stop(self, jid, kind, reason):
        """kind: 'requeue' (resumable stop by a guard) or 'overtime' (fail it)."""
        r = self.procs.get(jid)
        if not r or r["term_at"] is not None:
            return
        r["term_at"], r["stop_kind"], r["stop_reason"] = time.time(), kind, reason
        self.log("stop %s (%s): %s" % (jid, kind, reason))
        try:
            r["log"].write(("\n=== %s runner stops this job: %s\n" % (iso(utc_now()), reason)).encode())
            r["log"].flush()
        except (OSError, ValueError):
            pass
        if hasattr(os, "killpg"):
            self._signal_group(r["proc"].pid, signal.SIGTERM)
        else:
            r["proc"].terminate()

    def finish_failed(self, job, src, code, reason):
        lines = tail_lines(self.d("logs", job["id"] + ".log"), 20)
        extra = {"last_exit_code": code, "last_failure": reason, "last_failure_utc": iso(utc_now()),
                 "last_log_lines": lines}
        job.pop("pid", None)
        job.pop("started_utc", None)
        if reason.startswith("over time") or after_failure(job) == "failed":
            self.move(job, src, "failed", extra)
            self.log("failed %s: %s" % (job["id"], reason))
        else:
            self.move(job, src, "jobs", dict(extra, note="automatic retry (once) after: " + reason))
            self.log("retry %s once: %s" % (job["id"], reason))

    def reap(self):
        for jid in list(self.procs):
            r = self.procs[jid]
            code = r["proc"].poll()
            if code is None:
                if r["term_at"] is not None and time.time() - r["term_at"] > self.term_grace_s:
                    self._signal_group(r["proc"].pid, getattr(signal, "SIGKILL", signal.SIGTERM))
                    if not hasattr(os, "killpg"):
                        r["proc"].kill()
                continue
            try:
                r["log"].write(("=== %s exit %s\n" % (iso(utc_now()), code)).encode())
                r["log"].close()
            except (OSError, ValueError):
                pass
            del self.procs[jid]
            job = r["job"]
            out = job_out_dir(job)
            if r["stop_kind"] == "requeue":
                job.pop("pid", None)
                job.pop("started_utc", None)
                self.move(job, "running", "jobs", {"note": "stopped by guard, resumes: " + r["stop_reason"],
                                                   "last_stop_utc": iso(utc_now())})
                self.log("requeued %s (%s)" % (jid, r["stop_reason"]))
            elif r["stop_kind"] == "overtime":
                job["failures"] = int(job.get("failures", 0)) + 1
                self.finish_failed(job, "running", code, r["stop_reason"])
            elif succeeded(code, out):
                job.pop("pid", None)
                self.move(job, "running", "done", {"finished_utc": iso(utc_now()), "exit_code": code})
                self.log("done %s" % jid)
            else:
                job["failures"] = int(job.get("failures", 0)) + 1
                why = "exit code %s" % code if code != 0 else "exit 0 but no DONE marker in %s" % out
                self.finish_failed(job, "running", code, why)

    def guards_and_schedule(self):
        """One pass of the guards over running jobs, then start jobs if allowed. Returns False to exit."""
        disk, mem = self.disk_gb(), self.mem_gb()
        stop_file, pause_file = os.path.exists(self.d("STOP")), os.path.exists(self.d("PAUSE"))
        now = self.now()
        reason = stop_all_reason(disk, stop_file)
        if reason:
            for jid in list(self.procs):
                self.request_stop(jid, "requeue", reason)
            if not stop_file:
                self.write_reason(reason)
        live = [r["job"] for r in self.procs.values() if r["term_at"] is None]
        if not reason and memory_stop_needed(mem) and live and time.time() - self.last_mem_stop > MEM_STOP_SPACING_S:
            y = youngest(live)
            self.request_stop(y["id"], "requeue", "available memory %.2f GB < %.1f GB" % (mem, MEM_STOP_GB))
            self.write_reason("memory: stopped youngest job %s" % y["id"])
            self.last_mem_stop = time.time()
        for r in list(self.procs.values()):
            j = r["job"]
            if r["term_at"] is None and is_over_time(j.get("started_utc"), j.get("est_hours"), now):
                self.request_stop(j["id"], "overtime", "over time: ran more than %.1f h"
                                  % over_time_limit_h(j.get("est_hours")))
        if stop_file:
            return False
        self.hold_reason = start_block_reason(disk, mem, stop_file, pause_file, self.deployed_age_min())
        if self.hold_reason is None:
            queued = order_jobs(self.job_files("jobs"))
            while queued and len(self.procs) < self.workers:
                self.start_job(queued.pop(0))
                # re-check memory and disk before a second start in the same pass
                if start_block_reason(self.disk_gb(), self.mem_gb(), False, False, None):
                    break
        return True

    def write_reason(self, reason):
        try:
            with open(self.d("LAST_GUARD_STOP.txt"), "w", encoding="utf-8") as f:
                f.write("%s  %s\n" % (iso(utc_now()), reason))
        except OSError:
            pass
        self.log("guard: " + reason)

    def status(self):
        now = self.now()
        running, left = [], []
        for r in self.procs.values():
            j = r["job"]
            out = job_out_dir(j)
            prog = read_json(os.path.join(out, "progress.json")) if out else None
            h = running_hours_left(j, prog, now)
            left.append(h)
            running.append({"id": j["id"], "pid": j.get("pid"), "started_utc": j.get("started_utc"),
                            "est_hours": j.get("est_hours"), "hours_left": round(h, 2), "progress": prog,
                            "stopping": r["stop_reason"]})
        queued = order_jobs(self.job_files("jobs"))
        disk, mem = self.disk_gb(), self.mem_gb()
        return {
            "updated_utc": iso(utc_now()),
            "runner": {"pid": os.getpid(), "started_utc": iso(self.started), "workers": self.workers,
                       "prefix": self.prefix, "hold_reason": self.hold_reason},
            "running": running,
            "queued": len(queued),
            "queued_ids": [j["id"] for j in queued],
            "backlog_hours": backlog_hours(queued, left, self.workers),
            "done": len(self.job_files("done")),
            "failed": len(self.job_files("failed")),
            "free_disk_gb": None if disk is None else round(disk, 2),
            "mem_available_gb": None if mem is None else round(mem, 2),
        }

    def write_status(self, final=None):
        st = self.status()
        if final:
            st["runner"]["exited"] = final
        write_json(self.d("status.json"), st)
        self.last_status = time.time()

    def tick(self):
        self.reap()
        keep = self.guards_and_schedule()
        if not keep:
            return False
        if time.time() - self.last_status >= STATUS_EVERY_S or self.dirty:
            self.write_status()
            self.dirty = False
        return True

    def shutdown(self, why):
        for jid in list(self.procs):
            self.request_stop(jid, "requeue", why)
        t0 = time.time()
        while self.procs and time.time() - t0 < self.term_grace_s + 15:
            self.reap()
            time.sleep(1)
        self.reap()
        self.write_status(final=why)
        self.log("runner exits: " + why)

    def loop(self, tick_s=TICK_S):
        stop = {"why": None}

        def on_term(signum, frame):
            stop["why"] = "signal %d" % signum

        signal.signal(signal.SIGTERM, on_term)
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal.SIG_IGN)     # survive an ssh disconnect
        self.log("runner start pid %d workers %d prefix %s root %s" % (os.getpid(), self.workers, self.prefix, self.root))
        if str(self.requested_workers) != str(self.workers):
            self.log("workers %s requested, capped at %d" % (self.requested_workers, self.workers))
        self.recover()
        self.write_status()
        while True:
            if stop["why"]:
                self.shutdown(stop["why"])
                return 0
            try:
                if not self.tick():
                    self.shutdown("STOP file present")
                    return 0
            except Exception as e:                       # keep going: one bad job file must not end the queue
                self.log("error in tick: %r" % (e,))
            time.sleep(tick_s)


# ----------------------------------------------------------------------------------------------- single instance
def acquire_lock(root):
    """flock on runner.lock (held for life) plus runner.pid. Returns the open lock file, or None if another runs."""
    import fcntl
    lf = open(os.path.join(root, "runner.lock"), "a+")
    try:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lf.close()
        return None
    write_json(os.path.join(root, "runner.pid"), {"pid": os.getpid(), "started_utc": iso(utc_now())})
    return lf


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--workers", type=int, default=HARD_MAX_WORKERS, help="at most %d" % HARD_MAX_WORKERS)
    ap.add_argument("--deployed-file", default=DEPLOYED_FILE)
    ap.add_argument("--once", action="store_true", help="one tick, then exit (testing)")
    a = ap.parse_args(argv)
    os.makedirs(a.root, exist_ok=True)
    lock = acquire_lock(a.root)
    if lock is None:
        pid = (read_json(os.path.join(a.root, "runner.pid")) or {}).get("pid")
        print("runner already running (pid %s); not starting a second one" % pid)
        return 3
    r = Runner(a.root, workers=a.workers, deployed_file=a.deployed_file, log_to_stdout=True)
    if a.once:
        r.recover()
        r.tick()
        r.write_status()
        return 0
    return r.loop()


if __name__ == "__main__":
    sys.exit(main())
