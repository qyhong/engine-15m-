# -*- coding: utf-8 -*-
"""Laptop side of the research job queue on the Singapore box (standard library only).

    py -3 -X utf8 tools/research_queue.py install                 # create /data/research_queue/ and copy runner.py there
    py -3 -X utf8 tools/research_queue.py snapshot <commit>       # code snapshot of engine15/ + research/ at a commit
    py -3 -X utf8 tools/research_queue.py add --id ID --harness NAME --study ID --commit C [--est-hours H] [--priority N]
    py -3 -X utf8 tools/research_queue.py status                  # running, queued, BACKLOG HOURS, done, failed, disk, memory
    py -3 -X utf8 tools/research_queue.py start | stop | pause | resume
    py -3 -X utf8 tools/research_queue.py fetch ID                # results into research/out/queue/<ID>/
    py -3 -X utf8 tools/research_queue.py logs ID [-n 80]

It only shells out to ssh / scp. Every remote path it writes or removes is under /data/research_queue/ (checked by
_remote_path); it never touches the live engine. See research/queue/README.md.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = os.environ.get("MIND15_BOX", "ec2-user@13.251.40.113")
KEY = os.path.expanduser(os.environ.get("MIND15_BOX_KEY", "~/.ssh/minds15.pem"))
QROOT = "/data/research_queue"
PY = "/data/venv-research/bin/python"
FITS = "/data/mind15/research/out/h60_regime_exits/fits_today"
ENGINE_DATA = "/data/mind15/data"
SUBDIRS = ("jobs", "running", "done", "failed", "logs", "out", "code", "incoming")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,79}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _exe(name):
    git = r"C:\Program Files\Git\usr\bin\%s.exe" % name             # Git's ssh accepts the key file as it is
    return git if os.path.exists(git) else name


SSH_OPTS = ["-i", KEY, "-o", "ConnectTimeout=20", "-o", "LogLevel=ERROR", "-o", "BatchMode=yes"]


def _remote_path(*parts):
    """A path under /data/research_queue/; refuses anything that could escape it."""
    for p in parts:
        if not p or p.startswith("/") or ".." in p.split("/") or "\\" in p or "\0" in p:
            raise SystemExit("refused remote path part %r" % (p,))
    path = "/".join((QROOT,) + parts)
    if not path.startswith(QROOT + "/") or "/../" in path + "/":
        raise SystemExit("refused remote path %r" % path)
    return path


def _rm_cmd(path, recursive=False):
    """The only way this tool builds a removal: inside /data/research_queue/ and never the root itself."""
    norm = os.path.normpath(path).replace("\\", "/")
    if norm != path or not path.startswith(QROOT + "/") or path.rstrip("/") == QROOT or ".." in path.split("/"):
        raise SystemExit("refused to build a removal for %r" % path)
    return ("rm -rf -- " if recursive else "rm -f -- ") + shlex.quote(path)


def ssh(cmd, check=True, capture=True, timeout=600):
    r = subprocess.run([_exe("ssh")] + SSH_OPTS + [HOST, cmd], stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None,
                       timeout=timeout)
    out = (r.stdout or b"").decode("utf-8", "replace")
    if check and r.returncode != 0:
        err = (r.stderr or b"").decode("utf-8", "replace").strip()
        raise SystemExit("remote command failed (exit %d): %s\n%s" % (r.returncode, err, out.strip()))
    return r.returncode, out


def scp_to(local, remote):
    r = subprocess.run([_exe("scp")] + SSH_OPTS + [local, "%s:%s" % (HOST, remote)], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=1800)
    if r.returncode != 0:
        raise SystemExit("scp failed: %s" % r.stderr.decode("utf-8", "replace").strip())


def scp_from(remote, local):
    r = subprocess.run([_exe("scp")] + SSH_OPTS + ["%s:%s" % (HOST, remote), local], stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=600)
    return r.returncode == 0


def git(*args):
    r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    if r.returncode != 0:
        raise SystemExit("git %s failed: %s" % (" ".join(args), r.stderr.decode("utf-8", "replace").strip()))
    return r.stdout.decode("utf-8", "replace").strip()


def resolve_commit(c):
    full = git("rev-parse", "--verify", c + "^{commit}")
    short = full[:12]
    if not COMMIT_RE.match(short):
        raise SystemExit("bad commit %r" % c)
    return short


def mkdirs_cmd():
    return "mkdir -p " + " ".join(shlex.quote(_remote_path(d)) for d in SUBDIRS)


def utc_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------------------------------- commands
def cmd_install(a):
    ssh(mkdirs_cmd())
    for name in ("runner.py", "README.md"):
        local = os.path.join(REPO, "research", "queue", name)
        tmp = _remote_path("incoming", name + ".new")
        scp_to(local, tmp)
        ssh("mv -f %s %s" % (shlex.quote(tmp), shlex.quote(_remote_path(name))))
    print("installed runner.py and README.md in %s/ (a running runner keeps its old code until restarted)" % QROOT)


def cmd_snapshot(a):
    c = resolve_commit(a.commit)
    dest = _remote_path("code", c)
    code, _ = ssh("test -e %s" % shlex.quote(dest), check=False)
    if code == 0:
        raise SystemExit("refused: %s already exists" % dest)
    ssh(mkdirs_cmd())
    fd, tar = tempfile.mkstemp(suffix=".tar.gz")
    os.close(fd)
    try:
        git("archive", "--format=tar.gz", "-o", tar, c, "engine15", "research")
        remote_tar = _remote_path("incoming", c + ".tar.gz")
        scp_to(tar, remote_tar)
    finally:
        os.remove(tar)
    part = _remote_path("code", c + ".partial")
    q = shlex.quote
    script = ("set -e; %s; mkdir %s; tar -xzf %s -C %s; ln -s %s %s/data; mv %s %s; %s"
              % (_rm_cmd(part, recursive=True), q(part), q(remote_tar), q(part), q(ENGINE_DATA), q(part),
                 q(part), q(dest), _rm_cmd(remote_tar)))
    code, out = ssh(script, check=False)
    if code != 0:
        ssh(_rm_cmd(part, recursive=True) + "; " + _rm_cmd(remote_tar), check=False)
        raise SystemExit("snapshot failed: %s" % out)
    print("snapshot %s ready: %s (engine15/, research/, data -> %s)" % (c, dest, ENGINE_DATA))


def build_job(jid, harness, study, commit, est_hours, priority):
    out = _remote_path("out", jid)
    return {
        "id": jid,
        "command": [PY, "research/queue/%s.py" % harness, "--study", study, "--fits-dir", FITS, "--out", out],
        "cwd": _remote_path("code", commit),
        "out": out,
        "est_hours": float(est_hours),
        "priority": priority,
        "added_utc": utc_iso(),
        "harness": harness,
        "study": study,
        "commit": commit,
        "failures": 0,
    }


def cmd_add(a):
    if not ID_RE.match(a.id):
        raise SystemExit("bad id %r (letters, digits, _ . -; at most 80)" % a.id)
    if not NAME_RE.match(a.harness):
        raise SystemExit("bad harness name %r (a module name under research/queue/, no .py)" % a.harness)
    if not ID_RE.match(a.study):
        raise SystemExit("bad study id %r" % a.study)
    c = resolve_commit(a.commit)
    q = shlex.quote
    cwd = _remote_path("code", c)
    checks = " ".join("test -e %s && echo EXISTS:%s;" % (q(_remote_path(d, a.id + ".json")), d)
                      for d in ("jobs", "running", "done", "failed"))
    checks += " test -e %s && echo EXISTS:out; test -e %s && echo EXISTS:logs;" % (
        q(_remote_path("out", a.id)), q(_remote_path("logs", a.id + ".log")))
    checks += " test -f %s || echo NOHARNESS; true" % q(cwd + "/research/queue/%s.py" % a.harness)
    _, out = ssh(checks)
    if "EXISTS:" in out:
        raise SystemExit("refused: id %s already exists on the server (%s)" % (
            a.id, ", ".join(x.split(":")[1] for x in out.split() if x.startswith("EXISTS:"))))
    if "NOHARNESS" in out:
        raise SystemExit("refused: %s/research/queue/%s.py not found (run snapshot %s first?)" % (cwd, a.harness, c))
    est = a.est_hours
    if est is None:
        code, eo = ssh("cd %s && timeout 600 nice -n 19 env OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 "
                       "%s research/queue/%s.py --study %s --fits-dir %s --estimate"
                       % (q(cwd), PY, a.harness, q(a.study), q(FITS)), check=False)
        try:
            est = float(eo.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise SystemExit("could not read --estimate (exit %d): %s\nPass --est-hours." % (code, eo.strip()[-400:]))
    if est <= 0:
        raise SystemExit("est-hours must be > 0")
    job = build_job(a.id, a.harness, a.study, c, est, a.priority)
    fd, tmp = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=1, sort_keys=True)
    try:
        staged = _remote_path("incoming", a.id + ".json.new")
        scp_to(tmp, staged)
    finally:
        os.remove(tmp)
    ssh("mv -n %s %s && test ! -e %s" % (q(staged), q(_remote_path("jobs", a.id + ".json")), q(staged)))
    print("queued %s: %s study %s at %s, est %.2f h, priority %s" % (a.id, a.harness, a.study, c, est, a.priority))


def _alive_script():
    pidf = shlex.quote(_remote_path("runner.pid"))
    return ("p=$(%s -c 'import json,sys;print(json.load(open(sys.argv[1]))[\"pid\"])' %s 2>/dev/null); "
            "if [ -n \"$p\" ] && kill -0 \"$p\" 2>/dev/null && tr '\\0' ' ' < /proc/$p/cmdline | grep -q runner.py; "
            "then echo ALIVE:$p; else echo DEAD; fi" % (PY, pidf))


def runner_alive():
    _, out = ssh(_alive_script())
    m = re.search(r"ALIVE:(\d+)", out)
    return int(m.group(1)) if m else None


def cmd_status(a):
    _, out = ssh("cat %s 2>/dev/null; echo; echo ===; %s; ls %s 2>/dev/null"
                 % (shlex.quote(_remote_path("status.json")), _alive_script(), " ".join(
                     shlex.quote(_remote_path(f)) for f in ("STOP", "PAUSE"))) + "; true")
    body, _, tail = out.partition("===")
    alive = re.search(r"ALIVE:(\d+)", tail)
    flags = [f for f in ("STOP", "PAUSE") if _remote_path(f) in tail]
    try:
        st = json.loads(body.strip())
    except ValueError:
        st = None
    if a.json:
        print(json.dumps(st, indent=1))
        return
    print("runner: %s%s" % ("RUNNING pid %s" % alive.group(1) if alive else "NOT RUNNING",
                            ("  [" + " ".join(flags) + " file present]") if flags else ""))
    if not st:
        print("no status.json yet")
        return
    r = st.get("runner", {})
    print("status written %s, runner started %s, workers %s" % (st.get("updated_utc"), r.get("started_utc"),
                                                                r.get("workers")))
    if r.get("hold_reason"):
        print("holding (starts nothing new): %s" % r["hold_reason"])
    if r.get("exited"):
        print("runner exited: %s" % r["exited"])
    print("BACKLOG: %.1f hours   queued %d   running %d   done %d   failed %d"
          % (st.get("backlog_hours", 0), st.get("queued", 0), len(st.get("running", [])), st.get("done", 0),
             st.get("failed", 0)))
    print("free disk %s GB   available memory %s GB" % (st.get("free_disk_gb"), st.get("mem_available_gb")))
    for j in st.get("running", []):
        p = j.get("progress") or {}
        print("  running %-28s since %s  %s/%s  ~%.1f h left%s" % (
            j["id"], j.get("started_utc"), p.get("done", "?"), p.get("total", "?"), j.get("hours_left") or 0,
            ("  STOPPING: " + j["stopping"]) if j.get("stopping") else ""))
    if st.get("queued_ids"):
        print("  queued: " + ", ".join(st["queued_ids"]))


def cmd_start(a):
    pid = runner_alive()
    if pid:
        print("runner already running (pid %d)" % pid)
        return
    q = shlex.quote
    ssh("%s; %s; (cd %s && exec nohup setsid %s runner.py --workers %d) >> %s 2>&1 < /dev/null &"
        % (mkdirs_cmd(), _rm_cmd(_remote_path("STOP")), q(QROOT), PY, a.workers, q(_remote_path("runner.out"))), timeout=60)
    time.sleep(4)
    pid = runner_alive()
    if not pid:
        _, out = ssh("tail -n 20 %s" % q(_remote_path("runner.out")), check=False)
        raise SystemExit("runner did not stay up:\n" + out)
    print("runner started (pid %d, workers %d)" % (pid, a.workers))


def cmd_stop(a):
    ssh("touch %s" % shlex.quote(_remote_path("STOP")))
    print("STOP written: the runner stops running jobs (they resume later) and exits within a minute. "
          "'start' removes STOP and starts it again.")


def cmd_pause(a):
    ssh("touch %s" % shlex.quote(_remote_path("PAUSE")))
    print("PAUSE written: running jobs continue, nothing new starts until 'resume'.")


def cmd_resume(a):
    ssh(_rm_cmd(_remote_path("PAUSE")))
    print("PAUSE removed.")


def cmd_fetch(a):
    if not ID_RE.match(a.id):
        raise SystemExit("bad id")
    q = shlex.quote
    _, where = ssh("for d in done failed running jobs; do test -e %s/$d/%s.json && echo $d; done; true"
                   % (q(QROOT), a.id))
    where = where.split()
    if not where:
        raise SystemExit("no job %s on the server" % a.id)
    if where[0] != "done":
        print("note: job %s is in %s/, not done/; copying what exists" % (a.id, where[0]))
    dest = os.path.join(REPO, "research", "out", "queue", a.id)
    os.makedirs(dest, exist_ok=True)
    got = []
    for f in ("results.json", "report.md", "progress.json"):
        if scp_from(_remote_path("out", a.id, f), os.path.join(dest, f)):
            got.append(f)
    if scp_from(_remote_path(where[0], a.id + ".json"), os.path.join(dest, "job.json")):
        got.append("job.json")
    _, tail = ssh("tail -n 50 %s 2>/dev/null; true" % q(_remote_path("logs", a.id + ".log")))
    with open(os.path.join(dest, "log_tail.txt"), "w", encoding="utf-8") as f:
        f.write(tail)
    got.append("log_tail.txt")
    print("fetched into %s: %s" % (dest, ", ".join(got)))


def cmd_logs(a):
    if not ID_RE.match(a.id):
        raise SystemExit("bad id")
    _, out = ssh("tail -n %d %s 2>/dev/null; true" % (a.n, shlex.quote(_remote_path("logs", a.id + ".log"))))
    sys.stdout.write(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Research job queue on the Singapore box")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("install").set_defaults(fn=cmd_install)
    p = sub.add_parser("snapshot")
    p.add_argument("commit")
    p.set_defaults(fn=cmd_snapshot)
    p = sub.add_parser("add")
    p.add_argument("--id", required=True)
    p.add_argument("--harness", required=True)
    p.add_argument("--study", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--est-hours", type=float, default=None, help="if left out, the harness's --estimate is run")
    p.add_argument("--priority", type=int, default=50, help="lower runs first (default 50)")
    p.set_defaults(fn=cmd_add)
    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_status)
    p = sub.add_parser("start")
    p.add_argument("--workers", type=int, default=2, choices=(1, 2))
    p.set_defaults(fn=cmd_start)
    for name, fn in (("stop", cmd_stop), ("pause", cmd_pause), ("resume", cmd_resume)):
        sub.add_parser(name).set_defaults(fn=fn)
    p = sub.add_parser("fetch")
    p.add_argument("id")
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("logs")
    p.add_argument("id")
    p.add_argument("-n", type=int, default=80)
    p.set_defaults(fn=cmd_logs)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
