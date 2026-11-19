#!/usr/bin/env bash
# mind15_watchdog.sh: installs (or with --undo removes) a watchdog for the Mind 15 engine on the Singapore box
# (owner, 19 Nov 2026: "put a guard measure in place so the data no delay", after the 00:04-00:48 UTC hang).
#
# Every 5 minutes, as root: if the mind15 service is active but its log (/data/mind15/live.log) has not changed for
# STALE_MIN minutes, the engine is stuck (a normal step writes lines every few minutes; even a full cache rebuild after
# a deploy prints within ~17 minutes) -> restart the service once and log why. At most one restart per 45 minutes, so
# a fault that survives a restart cannot become a restart loop. Run ON the box as ec2-user: bash mind15_watchdog.sh
set -euo pipefail
STALE_MIN=30
BIN=/usr/local/bin/mind15-watchdog
UNIT=/etc/systemd/system/mind15-watchdog

if [ "${1:-}" = "--undo" ]; then
  sudo systemctl disable --now mind15-watchdog.timer 2>/dev/null || true
  sudo rm -f $UNIT.service $UNIT.timer $BIN
  sudo systemctl daemon-reload
  echo "watchdog removed"; exit 0
fi

sudo tee $BIN >/dev/null <<EOF
#!/usr/bin/env bash
# Mind 15 engine watchdog (installed by tools/server/mind15_watchdog.sh). Restarts a stuck engine; never more than
# once per 45 minutes.
LOG=/data/mind15/live.log
STAMP=/var/lib/mind15-watchdog.last
systemctl is-active --quiet mind15 || exit 0
[ -f "\$LOG" ] || exit 0
age=\$(( \$(date +%s) - \$(stat -c %Y "\$LOG") ))
[ "\$age" -gt $((STALE_MIN * 60)) ] || exit 0
last=\$(cat "\$STAMP" 2>/dev/null || echo 0)
if [ \$(( \$(date +%s) - last )) -lt 2700 ]; then
  echo "mind15-watchdog: engine log silent for \${age}s, but restarted less than 45 min ago: not restarting again"
  exit 0
fi
date +%s > "\$STAMP"
msg="watchdog: no engine output for \$((age / 60)) min: restarting the engine (\$(date -u +%Y-%m-%dT%H:%M:%SZ))"
echo "mind15-watchdog: \$msg"
echo "\$msg" >> "\$LOG"
systemctl restart mind15
EOF
sudo chmod 755 $BIN

sudo tee $UNIT.service >/dev/null <<'EOF'
[Unit]
Description=Mind 15 engine watchdog (restarts a stuck engine; at most once per 45 minutes)

[Service]
Type=oneshot
ExecStart=/usr/local/bin/mind15-watchdog
EOF

sudo tee $UNIT.timer >/dev/null <<'EOF'
[Unit]
Description=Mind 15 engine watchdog, every 5 minutes

[Timer]
OnBootSec=10min
OnUnitActiveSec=5min
AccuracySec=30s

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mind15-watchdog.timer
systemctl list-timers mind15-watchdog.timer --no-pager | head -3
sudo /usr/local/bin/mind15-watchdog && echo "watchdog dry check: engine fresh, nothing to do"
