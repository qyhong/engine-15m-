#!/bin/bash
# One-command deploy of Mind 15 from this laptop to the Singapore box (17 Nov 2026; gates and receipt 20 Nov 2026).
#
#   bash tools/deploy.sh                 full test suite here, then deploy the last commit
#   bash tools/deploy.sh tests/test_x.py only these tests (anything after the script name goes to pytest); REFUSED
#                                        when a money file changed since the last deploy (tools/money_files.txt)
#   MIND15_DEPLOY_DRY=1 bash tools/deploy.sh [...]   the gates only: says what it would do, runs no test, changes nothing
#
# What it does, in order, stopping at the first failure:
#   1. refuses if tracked files have uncommitted changes (only the last commit is deployed);
#   2. refuses a commit that is not on origin/main (the live code must be in the remote history);
#      MIND15_DEPLOY_ALLOW_UNPUSHED=1 lets it through in an emergency and the receipt says "pushed": false;
#   3. reads the last receipt on the box and refuses a narrowed test run when a money file changed since then
#      (no receipt yet = treated as changed);
#   4. runs the tests on the laptop;
#   5. waits until the engine on the box is asleep between steps with more than 6 minutes to spare (and checks again,
#      for 2 minutes, right before the restart), so the restart never lands on a close and no bar is skipped;
#   6. unpacks the commit over /data/mind15 (code only: data, journal, outputs and secrets are not in git) and checks
#      every engine file on the box against the commit; lists code files on the box that the commit does not have;
#   7. restarts the engine and the Telegram bot and checks both are running and report the new version;
#   8. writes the receipt /data/mind15/DEPLOYED.json (commit, version, time, tests) and a line in out/deploy_log.jsonl.
# It never touches the web box, the bot key, the vault or the env file.
set -euo pipefail
cd "$(dirname "$0")/.."
BOX="${MIND15_BOX:-ec2-user@13.251.40.113}"
KEY="${MIND15_BOX_KEY:-$HOME/.ssh/minds15.pem}"
SSH=(ssh -o ServerAliveInterval=30 -o ConnectTimeout=20 -o LogLevel=ERROR -i "$KEY" "$BOX")
DRY="${MIND15_DEPLOY_DRY:-0}"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "STOP: uncommitted changes in tracked files. Commit first; only the last commit is deployed."; git status --short --untracked-files=no; exit 1
fi
REV=$(git log --oneline -1)
HEAD_SHA=$(git rev-parse HEAD)
WANT=$(py -3 -c "from engine15.config import CFG; print(CFG['version'])")
echo "== deploying: $REV  ($WANT)"

echo "== 1/6 is the commit on origin/main?"
PUSHED=true
if git fetch -q origin 2>/dev/null && git merge-base --is-ancestor HEAD origin/main 2>/dev/null; then
  echo "   yes"
elif [ "${MIND15_DEPLOY_ALLOW_UNPUSHED:-0}" = 1 ]; then
  PUSHED=false; echo "   NO (or origin cannot be reached). MIND15_DEPLOY_ALLOW_UNPUSHED=1: going on; the receipt will say so. Push as soon as you can."
else
  echo "STOP: this commit is not on origin/main (or origin cannot be reached). Push first: git push origin main"; exit 1
fi

echo "== 2/6 what changed since the last deploy"
LAST=$("${SSH[@]}" 'cat /data/mind15/DEPLOYED.json 2>/dev/null || true') || { echo "STOP: cannot reach the box"; exit 1; }
LAST=$(printf '%s' "$LAST" | py -3 -c "import json,sys
try: print(json.load(sys.stdin).get('commit') or '')
except Exception: print('')")
MONEY=$(grep -v -E '^\s*(#|$)' tools/money_files.txt | tr -d '\r')
SIGNED="engine15/evidence.py engine15/levels.py engine15/indicators.py engine15/data.py engine15/econ.py engine15/owner.py engine15/evcache.py engine15/extdata.py engine15/livefeeds.py engine15/calhistory.py engine15/sources engine15/config.py"
if [ -n "$LAST" ] && git cat-file -e "$LAST^{commit}" 2>/dev/null; then
  echo "   live now: $(git log --oneline -1 "$LAST")"
  # shellcheck disable=SC2086
  CHANGED=$(git diff --name-only "$LAST" HEAD -- $MONEY | tr '\n' ' ')
  # shellcheck disable=SC2086
  REBUILD=$(git diff --name-only "$LAST" HEAD -- $SIGNED | tr '\n' ' ')
else
  LAST=""; CHANGED="unknown (no receipt on the box, or its commit is not in this repository)"; REBUILD="unknown"
  echo "   no usable receipt on the box: every money file counts as changed"
fi
if [ -n "$CHANGED" ]; then
  echo "   money files changed: $CHANGED"
  if [ "$#" -gt 0 ]; then
    echo "STOP: a money file changed since the last deploy, so only the FULL test suite may deploy it. Run: bash tools/deploy.sh"; exit 1
  fi
else
  echo "   no money file changed"
fi
if [ -n "$REBUILD" ]; then
  echo "   NOTE: files that sign the reading cache changed ($REBUILD): the first step may rebuild the cache (about 15"
  echo "         minutes). The vault's book ages meanwhile; deploy when BTC and ETH are flat or far from an exit."
fi
"${SSH[@]}" "cd /data/mind15 && /data/venv/bin/python -c \"
import json
try:
    ms = dict((m.get('symbol'), m) for m in json.load(open('out/live/setups.json'))['markets'])
    print('   the vault book now: ' + ', '.join('%s %s%s' % (s, ms[s].get('side'), ' (Target 1 taken)' if ms[s].get('t1_taken') else '') for s in ('BTCUSDT', 'ETHUSDT') if s in ms))
except Exception as e:
    print('   the vault book now: not readable (%s)' % type(e).__name__)
\"" || true
if [ "$DRY" = 1 ]; then
  echo "== dry run: the gates passed. Tests that would run: ${*:-the full suite}. Nothing was changed."; exit 0
fi

echo "== 3/6 tests on the laptop"
TLOG=$(mktemp)
set +e
PYTHONIOENCODING=utf-8 py -3 -m pytest -q -x "$@" 2>&1 | tee "$TLOG"
RC=${PIPESTATUS[0]}
set -e
PASSED=$(grep -oE '[0-9]+ passed' "$TLOG" | tail -1 | cut -d' ' -f1 || true)
SKIPPED=$(grep -oE '[0-9]+ skipped' "$TLOG" | tail -1 | cut -d' ' -f1 || true)
rm -f "$TLOG"
[ "$RC" = 0 ] || { echo "STOP: the tests failed; nothing was deployed."; exit 1; }
SCOPE="full"; [ "$#" -gt 0 ] && SCOPE="$*"

echo "== 4/6 waiting for a gap between steps on the box"
# Asleep = the log's last line is "sleeping Ns until the next close" AND that sleep has not run out yet (the log's own
# time + N). The last line alone is not enough: a long step prints nothing for minutes after waking up.
GAP='l=$(tail -1 /data/mind15/live.log); rem=-1; case "$l" in sleeping*) s=${l#sleeping }; s=${s%%s*}; rem=$(( $(stat -c %Y /data/mind15/live.log) + s - $(date +%s) ));; esac; echo "$rem|$(systemctl is-active mind15)"'
# wait_gap N: until the engine is asleep with more than N seconds left (or is not running at all).
wait_gap() {
  for i in $(seq 1 120); do
    S=$("${SSH[@]}" "$GAP") || { echo "STOP: cannot reach the box"; exit 1; }
    REM=${S%%|*}; ACT=${S#*|}
    if [ "$ACT" != "active" ] || [ "$REM" -gt "$1" ]; then return 0; fi
    echo "   engine busy or too close to its next step (asleep for another ${REM}s; -1 = mid-step; need more than $1): waiting"; sleep 20
  done
  echo "STOP: no gap found in 40 minutes"; exit 1
}
# 20 Nov 2026: unpacking and checking take about 100 s, so a 2-minute margin put the restart 15 s before a close and the
# engine missed that bar (the vault's book then aged 30 minutes, its limit). Start with 6 minutes in hand.
wait_gap 360

echo "== 5/6 unpacking the commit on the box"
# tar may complain about the mode or time of a folder the service user owns: that is harmless, so its exit code is not
# trusted either way. What counts is the check below: every engine file on the box must equal the commit, byte for byte.
git archive HEAD | "${SSH[@]}" 'tar xf - --no-overwrite-dir -C /data/mind15 2>&1 | grep -v -E "Cannot (change mode|utime)|Exiting with failure" ; /data/venv/bin/python -m compileall -q /data/mind15/engine15 >/dev/null; echo unpacked'
FILES=$(git ls-files engine15 | grep '\.py$' | LC_ALL=C sort)
WANT_SUMS=$(for f in $FILES; do printf '%s  %s\n' "$(git show "HEAD:$f" | sha256sum | cut -d' ' -f1)" "$f"; done)
HAVE_SUMS=$(printf '%s\n' "$FILES" | "${SSH[@]}" 'cd /data/mind15 && xargs sha256sum' 2>&1) || true
if [ "$WANT_SUMS" != "$HAVE_SUMS" ]; then
  echo "STOP: the engine files on the box do not match the commit (the engine has NOT been restarted and still runs the old code in memory):"
  diff <(echo "$WANT_SUMS") <(echo "$HAVE_SUMS") | head -10; exit 1
fi
echo "   $(echo "$FILES" | wc -l) engine files on the box match the commit"
# tar adds and overwrites; it never deletes. A file removed from git stays on the box (and stays importable).
ON_BOX=$("${SSH[@]}" 'cd /data/mind15 && { find engine15 tools tests -type f \( -name "*.py" -o -name "*.sh" -o -name "*.bat" \) -not -path "*/__pycache__/*"; ls *.py *.sh *.bat 2>/dev/null; } | LC_ALL=C sort' | tr -d '\r') || true
IN_GIT=$(git ls-files | grep -E '\.(py|sh|bat)$' | LC_ALL=C sort)
# known and wanted on the box only: its launcher, and the site's answer puller (the AI Trading Bot session's file)
EXTRA=$(comm -23 <(printf '%s\n' "$ON_BOX") <(printf '%s\n' "$IN_GIT") | grep -v -x -E 'run_live\.sh|tools/pull_answers\.py' || true)
EXTRA_N=0
if [ -n "$EXTRA" ]; then
  EXTRA_N=$(printf '%s\n' "$EXTRA" | wc -l | tr -d ' ')
  echo "   NOTE: $EXTRA_N code file(s) on the box are not in this commit (a deploy never deletes; remove by hand if dead):"
  printf '%s\n' "$EXTRA" | sed 's/^/        /'
fi

echo "== 6/6 restarting the engine and the Telegram bot"
# the restart itself needs room before the next close: with under 2 minutes left, let that step run first
wait_gap 120
"${SSH[@]}" "sudo systemctl restart mind15 mind15-telegram; sleep 8; a=\$(systemctl is-active mind15); b=\$(systemctl is-active mind15-telegram); v=\$(cd /data/mind15 && /data/venv/bin/python -c \"from engine15.config import CFG; print(CFG['version'])\"); echo \"engine: \$a   telegram bot: \$b   version on the box: \$v\"; [ \"\$a\" = active ] && [ \"\$b\" = active ] && [ \"\$v\" = '$WANT' ]" \
  || { echo "STOP: the box is not healthy after the restart. Check: ssh ... 'systemctl status mind15; tail -30 /data/mind15/live.log'"; exit 1; }

RECEIPT=$(D_COMMIT="$HEAD_SHA" D_VERSION="$WANT" D_PASSED="${PASSED:-0}" D_SKIPPED="${SKIPPED:-0}" D_SCOPE="$SCOPE" D_PUSHED="$PUSHED" \
  D_PREV="$LAST" D_CHANGED="$CHANGED" D_EXTRA="$EXTRA_N" D_SUBJECT="$(git log -1 --format=%s)" py -3 -c "
import json, os, time
e = os.environ
print(json.dumps({'commit': e['D_COMMIT'], 'subject': e['D_SUBJECT'], 'version': e['D_VERSION'],
                  'deployed_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                  'tests_passed': int(e['D_PASSED']), 'tests_skipped': int(e['D_SKIPPED']), 'tests_scope': e['D_SCOPE'],
                  'pushed': e['D_PUSHED'] == 'true', 'previous_commit': e['D_PREV'] or None,
                  'money_files_changed': e['D_CHANGED'].split() if e['D_PREV'] else None,
                  'extra_files_on_box': int(e['D_EXTRA'])}, sort_keys=True))")
printf '%s\n' "$RECEIPT" | "${SSH[@]}" 'cat > /data/mind15/DEPLOYED.json.tmp && mv /data/mind15/DEPLOYED.json.tmp /data/mind15/DEPLOYED.json' \
  || { echo "STOP: the new code is running but the receipt could not be written on the box. Write it by hand: $RECEIPT"; exit 1; }
mkdir -p out && printf '%s\n' "$RECEIPT" >> out/deploy_log.jsonl
echo "   receipt: $RECEIPT"
echo "== done: $WANT is on the box. Its first step runs at the next 15-minute close (a first step after new cards rebuilds the reading cache and takes longer)."
