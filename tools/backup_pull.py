# -*- coding: utf-8 -*-
"""Daily backup of the Singapore box's Mind 15 records to this laptop (owner, 17 Nov 2026: "Will backup to this laptop").

    py -3 tools/backup_pull.py            one dated archive into backup/server/, older ones pruned (KEEP kept)

What is copied: the journal, the live outputs (page, scoreboard, playbook), the engine's state and accumulated feeds
under data/ (NOT the reading cache, the re-downloadable raw archives or old reset backups), the RL forward books and
the logs. Never copied: secrets/ (the bot key) and mind15.env. Read-only on the server: one `tar` over ssh.
The result of every run is appended to backup/server/backup_log.txt; exit code 0 = a verified archive was written.
"""
import os
import subprocess
import sys
import tarfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "backup", "server")
HOST = os.environ.get("MIND15_BOX", "ec2-user@13.251.40.113")
KEY = os.path.expanduser(os.environ.get("MIND15_BOX_KEY", "~/.ssh/minds15.pem"))
KEEP = 7
MIN_BYTES = 5_000_000                                                 # a real archive is far larger; smaller = something failed
REMOTE = ("cd /data/mind15 && tar czf - --ignore-failed-read --warning=no-file-changed "
          "--exclude=data/evcache --exclude=data/raw --exclude='data/backup_*' --exclude=secrets --exclude=mind15.env "
          "journal out/live data research/out/rl/forward5 research/out/rl/forward6 research/out/rl/logs "
          "live.log telegram.log 2>/dev/null; true")


def _ssh():
    git = r"C:\Program Files\Git\usr\bin\ssh.exe"                     # Git's ssh accepts the key file as it is
    return git if os.path.exists(git) else "ssh"


def _log(line):
    os.makedirs(DEST, exist_ok=True)
    with open(os.path.join(DEST, "backup_log.txt"), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), line))
    print(line)


def main():
    os.makedirs(DEST, exist_ok=True)
    name = "mind15_%s.tgz" % time.strftime("%Y%m%d")
    tmp, out = os.path.join(DEST, name + ".part"), os.path.join(DEST, name)
    cmd = [_ssh(), "-i", KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=30",
           "-o", "StrictHostKeyChecking=accept-new", HOST, REMOTE]
    try:
        with open(tmp, "wb") as f:
            r = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=3600)
        size = os.path.getsize(tmp)
        if size < MIN_BYTES:
            raise RuntimeError("archive too small (%d bytes), ssh exit %d: %s"
                               % (size, r.returncode, r.stderr.decode("utf-8", "replace").strip()[-200:]))
        with tarfile.open(tmp, "r:gz") as t:                          # read it through: proves it is whole
            names = t.getnames()
        if not any(n.startswith("journal/") for n in names) or "out/live/page.json" not in names:
            raise RuntimeError("archive is missing the journal or the page (%d files)" % len(names))
        os.replace(tmp, out)
    except Exception as ex:
        if os.path.exists(tmp):
            os.remove(tmp)
        _log("FAILED %s: %s" % (name, str(ex)[:300]))
        return 1
    old = sorted(f for f in os.listdir(DEST) if f.startswith("mind15_") and f.endswith(".tgz"))
    for f in old[:-KEEP]:
        os.remove(os.path.join(DEST, f))
    _log("OK %s  %.1f MB, %d files; %d archives kept" % (name, size / 1e6, len(names), min(len(old), KEEP)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
