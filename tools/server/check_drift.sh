#!/bin/bash
# Read-only: does the Singapore box still match what this repository says it runs? (20 Nov 2026, tools/server/REBUILD.md)
#
#   bash tools/server/check_drift.sh        run on the laptop; prints one line per item and "DRIFT" where they differ
#
# It compares: the deploy receipt with origin/main, the unit files, drop-ins, launcher, watchdog and log rotation with
# the copies in tools/server/, and the box's Python packages with requirements-box.txt. It changes nothing, restarts
# nothing, and never reads mind15.env, secrets/ or any key. Exit code 0 = no drift, 1 = drift, 2 = the box was not reached.
set -uo pipefail
cd "$(dirname "$0")/../.."
BOX="${MIND15_BOX:-ec2-user@13.251.40.113}"
KEY="${MIND15_BOX_KEY:-$HOME/.ssh/minds15.pem}"
SSH=(ssh -o ConnectTimeout=20 -o LogLevel=ERROR -i "$KEY" "$BOX")
DRIFT=0

same() {   # same <label> <repo file> <path on the box>
  local have want
  want=$(tr -d '\r' < "$2" | sha256sum | cut -d' ' -f1)
  have=$("${SSH[@]}" "sha256sum '$3' 2>/dev/null | cut -d' ' -f1") || { echo "STOP: cannot reach the box"; exit 2; }
  if [ -z "$have" ]; then echo "DRIFT  $1: $3 is not on the box"; DRIFT=1
  elif [ "$have" = "$want" ]; then echo "ok     $1"
  else echo "DRIFT  $1: $3 differs from $2"; DRIFT=1; fi
}

"${SSH[@]}" true || { echo "STOP: cannot reach the box"; exit 2; }

echo "== what is deployed"
LIVE=$("${SSH[@]}" 'cat /data/mind15/DEPLOYED.json 2>/dev/null' | py -3 -c "import json,sys
try:
    d = json.load(sys.stdin); print('%s|%s|%s|%s' % (d.get('commit'), d.get('version'), d.get('deployed_utc'), d.get('tests_passed')))
except Exception: print('|||')")
COMMIT=${LIVE%%|*}
git fetch -q origin 2>/dev/null || echo "note   origin could not be reached: comparing with the last fetched origin/main"
MAIN=$(git rev-parse origin/main 2>/dev/null || echo "")
if [ -z "$COMMIT" ]; then echo "DRIFT  no deploy receipt on the box (/data/mind15/DEPLOYED.json)"; DRIFT=1
elif [ "$COMMIT" = "$MAIN" ]; then echo "ok     the box runs origin/main ($(git log --oneline -1 "$COMMIT")), receipt: ${LIVE#*|}"
elif git merge-base --is-ancestor "$COMMIT" origin/main 2>/dev/null; then
  echo "note   the box runs $(git log --oneline -1 "$COMMIT"); origin/main is $(git rev-list --count "$COMMIT..origin/main") commit(s) ahead (not deployed yet)"
else echo "DRIFT  the box's receipt names $COMMIT, which is not on origin/main"; DRIFT=1; fi
VER=$("${SSH[@]}" "cd /data/mind15 && /data/venv/bin/python -c \"from engine15.config import CFG; print(CFG['version'])\"" 2>/dev/null)
[ "$VER" = "$(echo "$LIVE" | cut -d'|' -f2)" ] && echo "ok     version on the box: $VER" || { echo "DRIFT  the code on the box says $VER, the receipt says $(echo "$LIVE" | cut -d'|' -f2)"; DRIFT=1; }
if [ -n "$COMMIT" ] && git cat-file -e "$COMMIT^{commit}" 2>/dev/null; then
  FILES=$(git ls-tree -r --name-only "$COMMIT" engine15 | grep '\.py$' | LC_ALL=C sort)
  WANT=$(for f in $FILES; do printf '%s  %s\n' "$(git show "$COMMIT:$f" | sha256sum | cut -d' ' -f1)" "$f"; done)
  HAVE=$(printf '%s\n' "$FILES" | "${SSH[@]}" 'cd /data/mind15 && xargs sha256sum' 2>&1)
  if [ "$WANT" = "$HAVE" ]; then echo "ok     $(echo "$FILES" | wc -l | tr -d ' ') engine files equal the receipt's commit"
  else echo "DRIFT  engine files on the box differ from the receipt's commit:"; diff <(echo "$WANT") <(echo "$HAVE") | head -6; DRIFT=1; fi
fi

echo "== services"
S=$("${SSH[@]}" 'for u in mind15.service mind15-telegram.service mind15-watchdog.timer mind15-state-copy.timer; do echo "$u $(systemctl is-enabled $u 2>&1 | head -1) $(systemctl is-active $u 2>&1 | head -1)"; done')
while read -r u en ac; do
  if [ "$en" = enabled ] && [ "$ac" = active ]; then echo "ok     $u enabled and active"; else echo "DRIFT  $u is $en / $ac"; DRIFT=1; fi
done <<< "$S"

echo "== files that define the box"
for u in mind15.service mind15-telegram.service mind15-watchdog.service mind15-watchdog.timer mind15-state-copy.service mind15-state-copy.timer; do
  same "unit $u" "tools/server/units/$u" "/etc/systemd/system/$u"
done
same "drop-in mind15 24x7" tools/server/dropins/24x7.conf /etc/systemd/system/mind15.service.d/24x7.conf
same "drop-in telegram 24x7" tools/server/dropins/24x7.conf /etc/systemd/system/mind15-telegram.service.d/24x7.conf
same "launcher run_live.sh" tools/server/run_live.sh /data/mind15/run_live.sh
same "watchdog script" tools/server/bin/mind15-watchdog /usr/local/bin/mind15-watchdog
same "log rotation" tools/server/logrotate/mind15 /etc/logrotate.d/mind15

echo "== Python packages (the numpy and pandas versions sign the reading cache)"
HAVE=$("${SSH[@]}" '/data/venv/bin/python -V; /data/venv/bin/pip freeze 2>/dev/null' | tr -d '\r')
WANT=$(tr -d '\r' < tools/server/requirements-box.txt | grep -v '^#')
PYV=$(grep '^# python' tools/server/requirements-box.txt | sed 's/^# python //')
[ "$(echo "$HAVE" | head -1)" = "Python $PYV" ] && echo "ok     $(echo "$HAVE" | head -1)" || { echo "DRIFT  the box has $(echo "$HAVE" | head -1), the record says Python $PYV"; DRIFT=1; }
if [ "$(echo "$HAVE" | tail -n +2)" = "$WANT" ]; then echo "ok     $(echo "$WANT" | wc -l | tr -d ' ') packages equal requirements-box.txt"
else echo "DRIFT  packages differ from requirements-box.txt:"; diff <(echo "$WANT") <(echo "$HAVE" | tail -n +2) | head -10; DRIFT=1; fi

echo "== the engine's memory copies"
"${SSH[@]}" 'd=/data/mind15/data/state_copies; n=$(ls -d $d/2* 2>/dev/null | wc -l); new=$(ls -d $d/2* 2>/dev/null | tail -1); echo "$n|${new##*/}"' | {
  IFS='|' read -r n new
  if [ "${n:-0}" -ge 1 ]; then echo "ok     $n hourly copies, the newest $new"; else echo "DRIFT  no hourly copy in data/state_copies"; exit 1; fi
} || DRIFT=1

echo
[ "$DRIFT" = 0 ] && echo "NO DRIFT: the box matches the repository's record." || echo "DRIFT FOUND: see the lines above. Nothing was changed."
exit "$DRIFT"
