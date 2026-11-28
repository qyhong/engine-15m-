# -*- coding: utf-8 -*-
"""push -- send page.json to the web server after each live step. OFF until switched on.

The public tab (alphaprediction.ai/aitrading/mind15/) reads page.json from its own folder on
the web server. This engine runs on the laptop, so after each step the file is pushed there.
The rules are the web server owner's (the AI Trading Bot session, 10 Nov 2026):

  * ONE ssh connection per push (the server resets rapid connections);
  * the remote command is short and fixed (Git for Windows' ssh cuts a long argument); the
    file travels on standard input, never on the command line;
  * the file is written to a temporary name in the target folder, then moved into place;
  * a push counts as done only when the server prints the confirmation line with the md5 of
    the file it now holds, and that md5 equals the local one. Exit code 0 alone is not proof.

SWITCH: the environment variable ENGINE15_PUSH. Unset or "0" = no push, nothing leaves this
machine (the default). "1" = push after every step. The target folder is created by the web
server's owner, not by this job; a missing folder is reported as a failed push.

    py -3 -m engine15 push            push out/live/page.json once now (needs ENGINE15_PUSH=1)
"""
import hashlib
import os
import subprocess

from .config import OUT_DIR

KEY = os.path.expanduser(os.environ.get("ENGINE15_PUSH_KEY", "~/.ssh/flowerworlds.pem"))   # the Singapore box uses its own key
HOST = os.environ.get("ENGINE15_PUSH_HOST", "ec2-user@98.93.142.222")
REMOTE_DIR = "/var/www/aitrading/mind15"
# fixed, short; the file arrives on stdin
REMOTE = ("cat > %(d)s/.page.json.tmp && mv -f %(d)s/.page.json.tmp %(d)s/page.json && "
          "echo PUSHED $(md5sum < %(d)s/page.json | cut -d' ' -f1)") % {"d": REMOTE_DIR}
PAGE = os.path.join(OUT_DIR, "live", "page.json")
# the other files allowed beside page.json (fixed names only: the remote command is built from this list, never from input)
EXTRA = ("page.zh.json",)          # 28 Nov 2026: the Chinese map of page.json (engine15/zh_live.py)


def _remote(name):
    return ("cat > %(d)s/.%(n)s.tmp && mv -f %(d)s/.%(n)s.tmp %(d)s/%(n)s && "
            "echo PUSHED $(md5sum < %(d)s/%(n)s | cut -d' ' -f1)") % {"d": REMOTE_DIR, "n": name}


def enabled():
    return os.environ.get("ENGINE15_PUSH", "0") == "1"


def push(path=PAGE, timeout=60, _remote_cmd=None):
    """-> (ok, message). One ssh connection; ok only on the server's own md5 confirmation."""
    if not enabled():
        return False, "push is off (set ENGINE15_PUSH=1 to switch it on)"
    with open(path, "rb") as fh:
        body = fh.read()
    local = hashlib.md5(body).hexdigest()
    try:
        r = subprocess.run(["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST, _remote_cmd or REMOTE],
                           input=body, capture_output=True, timeout=timeout)
    except Exception as e:
        return False, "push failed: %r" % (e,)
    lines = [ln.strip() for ln in r.stdout.decode("utf-8", "replace").splitlines() if ln.strip()]
    confirm = next((ln for ln in lines if ln.startswith("PUSHED ")), None)
    if confirm == "PUSHED " + local:
        return True, "pushed %d bytes, md5 %s" % (len(body), local)
    return False, "push NOT confirmed (exit %s): %s %s" % (r.returncode, confirm or "no confirmation line",
                                                           r.stderr.decode("utf-8", "replace")[-200:].strip())


def push_file(path, name, timeout=60):
    """Push one of the EXTRA files (same rules as page.json). -> (ok, message)"""
    if name not in EXTRA:
        return False, "push refused: %s is not one of %s" % (name, ", ".join(EXTRA))
    return push(path, timeout=timeout, _remote_cmd=_remote(name))


def main(argv):
    print(push()[1])
