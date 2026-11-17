#!/bin/bash
# One-command deploy of Mind 15 from this laptop to the Singapore box (17 Nov 2026).
#
#   bash tools/deploy.sh                 full test suite here, then deploy the last commit
#   bash tools/deploy.sh tests/test_x.py only these tests (anything after the script name goes to pytest)
#
# What it does, in order, stopping at the first failure:
#   1. refuses if tracked files have uncommitted changes (only the last commit is deployed);
#   2. runs the tests on the laptop;
#   3. waits until the engine on the box is asleep between steps with at least 2 minutes to spare;
#   4. unpacks the commit over /data/mind15 (code only: data, journal, outputs and secrets are not in git);
#   5. restarts the engine and the Telegram bot and checks both are running and report the new version.
# Paper only. It never touches the web box, the bot key or the env file.
set -euo pipefail
cd "$(dirname "$0")/.."
BOX="${MIND15_BOX:-ec2-user@13.251.40.113}"
KEY="${MIND15_BOX_KEY:-$HOME/.ssh/minds15.pem}"
SSH=(ssh -o ServerAliveInterval=30 -o ConnectTimeout=20 -o LogLevel=ERROR -i "$KEY" "$BOX")

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "STOP: uncommitted changes in tracked files. Commit first; only the last commit is deployed."; git status --short --untracked-files=no; exit 1
fi
REV=$(git log --oneline -1)
WANT=$(py -3 -c "from engine15.config import CFG; print(CFG['version'])")
echo "== deploying: $REV  ($WANT)"

echo "== 1/4 tests on the laptop"
PYTHONIOENCODING=utf-8 py -3 -m pytest -q -x "$@"

echo "== 2/4 waiting for a gap between steps on the box"
# Asleep = the log's last line is "sleeping Ns until the next close" AND that sleep has not run out yet (the log's own
# time + N). The last line alone is not enough: a long step prints nothing for minutes after waking up.
GAP='l=$(tail -1 /data/mind15/live.log); rem=-1; case "$l" in sleeping*) s=${l#sleeping }; s=${s%%s*}; rem=$(( $(stat -c %Y /data/mind15/live.log) + s - $(date +%s) ));; esac; echo "$rem|$(systemctl is-active mind15)"'
for i in $(seq 1 120); do
  S=$("${SSH[@]}" "$GAP") || { echo "STOP: cannot reach the box"; exit 1; }
  REM=${S%%|*}; ACT=${S#*|}
  if [ "$ACT" != "active" ] || [ "$REM" -gt 120 ]; then break; fi
  echo "   engine busy or too close to its next step (asleep for another ${REM}s; -1 = mid-step): waiting"; sleep 20
  [ "$i" = 120 ] && { echo "STOP: no gap found in 40 minutes"; exit 1; }
done

echo "== 3/4 unpacking the commit on the box"
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

echo "== 4/4 restarting the engine and the Telegram bot"
"${SSH[@]}" "sudo systemctl restart mind15 mind15-telegram; sleep 8; a=\$(systemctl is-active mind15); b=\$(systemctl is-active mind15-telegram); v=\$(cd /data/mind15 && /data/venv/bin/python -c \"from engine15.config import CFG; print(CFG['version'])\"); echo \"engine: \$a   telegram bot: \$b   version on the box: \$v\"; [ \"\$a\" = active ] && [ \"\$b\" = active ] && [ \"\$v\" = '$WANT' ]" \
  || { echo "STOP: the box is not healthy after the restart. Check: ssh ... 'systemctl status mind15; tail -30 /data/mind15/live.log'"; exit 1; }
echo "== done: $WANT is on the box. Its first step runs at the next 15-minute close (a first step after new cards rebuilds the reading cache and takes longer)."
