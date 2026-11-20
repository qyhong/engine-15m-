#!/bin/bash
# Installs (or with --undo removes) the hourly copy of the engine's memory on the Singapore box (20 Nov 2026).
# Run ON the box as ec2-user, after a deploy has put tools/server/ there:   bash /data/mind15/tools/server/install_state_copy.sh
# It copies the two unit files from this folder, starts the timer and takes one copy now. Nothing else is touched.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
UNIT=/etc/systemd/system/mind15-state-copy
if [ "${1:-}" = "--undo" ]; then
  sudo systemctl disable --now mind15-state-copy.timer 2>/dev/null || true
  sudo rm -f $UNIT.service $UNIT.timer
  sudo systemctl daemon-reload
  echo "hourly state copy removed (the copies in /data/mind15/data/state_copies are left)"; exit 0
fi
sudo install -m 644 "$HERE/units/mind15-state-copy.service" $UNIT.service
sudo install -m 644 "$HERE/units/mind15-state-copy.timer" $UNIT.timer
sudo systemctl daemon-reload
sudo systemctl enable --now mind15-state-copy.timer
sudo systemctl start mind15-state-copy.service
systemctl list-timers mind15-state-copy.timer --no-pager | head -3
sudo -u mind15 /data/venv/bin/python /data/mind15/tools/server/state_copies.py list | head -3
