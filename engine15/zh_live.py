# -*- coding: utf-8 -*-
"""zh_live -- after each live step, the Chinese maps for Mind 15's published files (engine15/zh.py does the work).

Owner, 28 Nov 2026: the website's other languages fully translated, automatically ("Automatic").

The step starts this module as its own process at the very end (live.start_zh) and does not wait for it, so the
translation never slows or stops a step, the vault feed or the push. It does nothing until the key file exists
(zh.KEY_FILE, /etc/mind15/anthropic.key: placed by the owner, root:mind15 0640; read at run time, never printed).

For each of out/live/page.json, setups.json, stocks.json, b_trail_book.json and landing.json it writes X.zh.json
beside it; the four Setups-side files are also copied into MIND15_SETUPS_WEB_DIR (as setups.py does), and
page.zh.json goes to the web box through push.push_file (the same one-connection rule as page.json).
One run at a time (a lock file); one cache for every file (data/zh_cache.json); one line per run in out/live/zh.log.

    py -3 -m engine15.zh_live          one run now
"""
import datetime as _dt
import os
import shutil
import sys
import time

from . import zh
from .config import DATA_DIR, OUT_DIR

LIVE = os.path.join(OUT_DIR, "live")
DATA = DATA_DIR
CACHE = os.path.join(DATA, "zh_cache.json")
LOCK = os.path.join(DATA, "zh.lock")
LOG = os.path.join(LIVE, "zh.log")
FILES = ("page.json", "setups.json", "stocks.json", "b_trail_book.json", "landing.json")
WEB_FILES = ("setups.json", "stocks.json", "b_trail_book.json", "landing.json")
WEB_ENV = "MIND15_SETUPS_WEB_DIR"
STALE_LOCK_S = 3600


def ready():
    """True when there is a key file to translate with (the step starts a run only then)."""
    return os.path.isfile(zh.KEY_FILE)


def _lock():
    """True when this run holds the lock (a lock older than an hour is a crashed run's and is taken over)."""
    try:
        fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        try:
            if time.time() - os.path.getmtime(LOCK) > STALE_LOCK_S:
                os.remove(LOCK)
                return _lock()
        except OSError:
            pass
        return False


def _say(line):
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (stamp, line))
        if os.path.getsize(LOG) > 2_000_000:                       # keep the log small: the last half stays
            with open(LOG, encoding="utf-8") as f:
                tail = f.readlines()[-2000:]
            with open(LOG, "w", encoding="utf-8") as f:
                f.writelines(tail)
    except OSError:
        pass


def run(client=None, push_page=True):
    """One pass over FILES. -> {name: (translated, total)}"""
    if client is None:
        key = zh.read_key()
        if not key:
            return {}
        client = zh.make_client(key)
    done = {}
    for name in FILES:
        src = os.path.join(LIVE, name)
        if not os.path.isfile(src):
            continue
        r = zh.run_file(src, cache_path=CACHE, client=client, log=_say)
        if r is None:
            continue
        done[name] = r
        out = zh.zh_path(src)
        web_dir = (os.environ.get(WEB_ENV) or "").strip()
        if name in WEB_FILES and web_dir:
            try:
                tmp = os.path.join(web_dir, "." + os.path.basename(out) + ".tmp")
                shutil.copyfile(out, tmp)
                os.chmod(tmp, 0o644)
                os.replace(tmp, os.path.join(web_dir, os.path.basename(out)))
            except OSError as e:
                _say("web copy of %s not written (%r)" % (os.path.basename(out), e))
        if name == "page.json" and push_page:
            from . import push
            if push.enabled():
                _say("push page.zh.json: %s" % push.push_file(out, "page.zh.json")[1])
    return done


def main(argv=None):
    if not ready() or not _lock():
        return 0
    t0 = time.time()
    try:
        done = run()
        _say("; ".join("%s %d/%d" % (n, a, b) for n, (a, b) in done.items()) + " (%.0fs)" % (time.time() - t0))
    except Exception as e:                                         # never loud: the next step tries again
        _say("run failed (%r)" % (e,))
    finally:
        try:
            os.remove(LOCK)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
