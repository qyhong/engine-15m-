#!/bin/bash
# H58 runner: takes the heavy-job lock, readings in two streams, the walk-forward sets in two streams, the report.
cd /data/mind15
export PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1     # one BLAS thread: 30x faster here, and no contention with the live engine
OUTD=research/out/h58_stocks
LOCK=research/out/heavy_job.lock
PY="nice -n 10 /data/venv-research/bin/python research/h58_stocks.py"
while true; do
  if ( set -o noclobber; echo "{\"pid\": $$, \"label\": \"h58_stocks\", \"since_utc\": \"$(date -u '+%F %T')\"}" > $LOCK ) 2>/dev/null; then break; fi
  HP=$(python3 -c "import json;print(json.load(open('$LOCK')).get('pid',''))" 2>/dev/null)
  if [ -n "$HP" ] && ! kill -0 "$HP" 2>/dev/null; then rm -f $LOCK; continue; fi
  echo "lock held: $(cat $LOCK)"; sleep 60
done
trap 'python3 -c "import json,os;d=json.load(open(\"$LOCK\"));os.remove(\"$LOCK\") if d.get(\"pid\")==$$ else None"' EXIT
avail() { awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo; }
[ "$(avail)" -lt 3000 ] && { echo "only $(avail) MB available: not starting"; exit 2; }
todo() { for T in "$@"; do [ -f $OUTD/readings/$T.npz ] || echo -n "$T "; done; }
STAGE=${1:-all}
if [ "$STAGE" = all ] || [ "$STAGE" = readings ]; then
  A=$(todo NVDA MU T AAPL MSFT AMZN GOOGL); B=$(todo AVGO META TSLA BRK.B JPM LLY)
  [ -n "$A" ] && $PY readings $A >> $OUTD/readings_a.log 2>&1 &
  [ -n "$B" ] && $PY readings $B >> $OUTD/readings_b.log 2>&1 &
  wait
  for T in NVDA MU T AAPL MSFT AMZN GOOGL AVGO META TSLA BRK.B JPM LLY; do
    [ -f $OUTD/readings/$T.npz ] || { echo "readings missing for $T"; exit 1; }
  done
  echo "readings done $(date -u)"
fi
if [ "$STAGE" = all ] || [ "$STAGE" = walk ]; then
  $PY walk primary loto_NVDA loto_MU loto_T loto_AAPL loto_MSFT loto_AMZN > $OUTD/walk_a.log 2>&1 &
  $PY walk e1 loto_GOOGL loto_AVGO loto_META loto_TSLA loto_BRK.B loto_JPM loto_LLY > $OUTD/walk_b.log 2>&1 &
  wait
  echo "walks done $(date -u)"
  $PY report > $OUTD/report.log 2>&1
  echo "all done $(date -u)"
fi
