#!/usr/bin/env bash
# mind15_own_user.sh: the Mind 15 engine and its Telegram bot leave ec2-user (who has passwordless sudo) and run as
# their own system user "mind15" inside a systemd sandbox (owner "Yes, do it", 17 Nov 2026; the box audit's top finding).
# After it, the services can write ONLY the engine's state folders; the code, the Python environment, the rest of the box
# and the site's secrets are read-only or out of reach for them. Same pattern as the forecast loop's forecast_own_user.sh.
#
# Run ON the Singapore box as ec2-user:   bash mind15_own_user.sh            apply (between steps; it checks)
#                                         bash mind15_own_user.sh --undo     back to ec2-user with the old units
# It never prints or reads the content of a key: the push key and the bot key are only copied / re-owned.
set -euo pipefail
M=/data/mind15
ETC=/etc/mind15
HOMEDIR=/var/lib/mind15
UNITS=/etc/systemd/system
OWNED="data journal out research/out/rl"          # become mind15:mind15 (the engine creates and rewrites files here)
SHARED="research/out"                              # stays ec2-user's, group mind15 may write (research runs + the engine's reports)
BK=/home/ec2-user/mind15_backups

gap_ok() {                                         # asleep between steps with more than 3 minutes of sleep left?
  local l s rem=-1                                 # the last log line alone is not enough: a long step prints nothing for minutes
  l=$(tail -1 $M/live.log)
  case "$l" in sleeping*) s=${l#sleeping }; s=${s%%s*}; rem=$(( $(stat -c %Y $M/live.log) + s - $(date +%s) ));; esac
  [ "$rem" -gt 180 ]
}

owners_back() {
  for d in $OWNED $SHARED; do sudo chown -R ec2-user:ec2-user $M/$d; done
  sudo chown -R ec2-user:ec2-user $M/secrets; sudo chmod 700 $M/secrets; sudo chmod 600 $M/secrets/* 2>/dev/null || true
}

if [ "${1:-}" = "--undo" ]; then
  O=$(ls -d $BK/*-own-user 2>/dev/null | tail -1)
  [ -n "$O" ] || { echo "no backup to undo from"; exit 1; }
  if systemctl is-active --quiet mind15; then gap_ok || { echo "STOP: the engine is mid-step or too close to the next one; run again in a gap"; exit 1; }; fi
  sudo systemctl stop mind15 mind15-telegram
  sudo cp -p "$O/mind15.service" "$O/mind15-telegram.service" $UNITS/
  cp -p "$O/mind15.env" $M/mind15.env
  # the ec2-user copy of the push key was removed after the switch (17 Nov 2026): put it back from the root-owned one
  [ -f /home/ec2-user/.ssh/mind15_web ] || sudo install -o ec2-user -g ec2-user -m 0600 $ETC/push_key /home/ec2-user/.ssh/mind15_web
  owners_back
  sudo systemctl daemon-reload && sudo systemctl start mind15 mind15-telegram
  sleep 8
  echo "UNDONE: engine $(systemctl is-active mind15), bot $(systemctl is-active mind15-telegram), running as $(ps -o user= -p "$(systemctl show mind15 -p MainPID --value)")"
  exit 0
fi

gap_ok || { echo "STOP: the engine is mid-step or within 3 minutes of the next one; run again in a gap"; exit 1; }
B=$BK/$(date -u +%Y%m%dT%H%M%SZ)-own-user
mkdir -p "$B"
cp -p $UNITS/mind15.service $UNITS/mind15-telegram.service $M/mind15.env "$B/"
echo "backup: $B"

# 1. the user, its home (only for ssh's known_hosts and caches), and the push key in a root-owned place
id mind15 >/dev/null 2>&1 || sudo useradd --system --no-create-home --home-dir $HOMEDIR --shell /sbin/nologin mind15
sudo usermod -aG mind15 ec2-user                   # deploys, research runs and the laptop's backup keep working through the group
sudo mkdir -p $HOMEDIR/.ssh $HOMEDIR/.cache $ETC
ssh-keygen -F 98.93.142.222 -f /home/ec2-user/.ssh/known_hosts | grep -v '^#' | sudo tee $HOMEDIR/.ssh/known_hosts >/dev/null
sudo chown -R mind15:mind15 $HOMEDIR; sudo chmod 700 $HOMEDIR $HOMEDIR/.ssh; sudo chmod 644 $HOMEDIR/.ssh/known_hosts
[ -f $ETC/push_key ] || sudo install -o root -g mind15 -m 0640 /home/ec2-user/.ssh/mind15_web $ETC/push_key
sudo chown root:mind15 $ETC; sudo chmod 750 $ETC

sudo systemctl stop mind15 mind15-telegram
restore() {
  echo "FAILED: putting the old units, env file and owners back"
  sudo cp -p "$B/mind15.service" "$B/mind15-telegram.service" $UNITS/
  cp -p "$B/mind15.env" $M/mind15.env
  owners_back
  sudo systemctl daemon-reload; sudo systemctl start mind15 mind15-telegram || true
}
trap 'echo "failed at line $LINENO: $BASH_COMMAND"; restore' ERR

# 2. who owns what. State: the service user's. Code, tests, tools and the Python environment: ec2-user's, read-only to it.
for d in $OWNED; do sudo mkdir -p $M/$d; done
for d in $SHARED; do sudo chgrp -R mind15 $M/$d; done
for d in $OWNED; do sudo chown -R mind15:mind15 $M/$d; done
for d in $OWNED $SHARED; do sudo chmod -R g+rwX $M/$d; sudo find $M/$d -type d -exec chmod g+s {} +; done
sudo chown ec2-user:mind15 $M/research/out/rl          # this folder itself is in git: a deploy's tar must be able to set its mode
sudo chown -R ec2-user:mind15 $M/secrets; sudo chmod 750 $M/secrets; sudo chmod 640 $M/secrets/*   # the bot reads its key through the group
sudo chgrp mind15 $M/mind15.env; chmod 640 $M/mind15.env
sudo chmod -R go-w $M/engine15 $M/tools $M/tests $M/configs $M/docs $M/web /data/venv
sudo chmod go-w $M $M/research $M/run_live.sh $M/*.md 2>/dev/null || true
sudo find $M/research -maxdepth 2 -name '*.py' -exec chmod go-w {} +
/data/venv/bin/python -m compileall -q $M/engine15 >/dev/null     # the service cannot write .pyc files any more: compile them now

# 3. the env file points at the key's new place
sed -i -e "s|^ENGINE15_PUSH_KEY=.*|ENGINE15_PUSH_KEY=$ETC/push_key|" -e "s|^MIND15_PULL_KEY=.*|MIND15_PULL_KEY=$ETC/push_key|" $M/mind15.env

# 4. what the service user must be able to reach, checked before any start
sudo -u mind15 test -r $M/engine15/config.py
sudo -u mind15 test -x /data/venv/bin/python
sudo -u mind15 test -r $M/mind15.env
sudo -u mind15 test -r $ETC/push_key
sudo -u mind15 test -r $M/secrets/telegram_token
sudo -u mind15 test -w $M/data/live_state.json
sudo -u mind15 test -w $M/journal
sudo -u mind15 test -w $M/out/live/page.json
sudo -u mind15 test -r /var/www/aitrading/forecasts.json
sudo -u mind15 ls /data/estate >/dev/null
! sudo -u mind15 test -w $M/engine15/config.py

SANDBOX='UMask=0002
NoNewPrivileges=yes
CapabilityBoundingSet=
AmbientCapabilities=
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=yes
RestrictRealtime=yes
LockPersonality=yes
RemoveIPC=yes'
OTHERS='-/etc/aitrading-auth -/var/lib/aitrading-auth -/data/aitrading/backups -/etc/letsencrypt'

sudo tee $UNITS/mind15.service >/dev/null <<UNIT
[Unit]
Description=Mind 15 live loop (paper only; pushes page.json to the web box); own user + sandbox since 17 Nov 2026
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mind15
Group=mind15
WorkingDirectory=/data/mind15
Environment=ENGINE15_PUSH=1
Environment=HOME=$HOMEDIR
Environment=XDG_CACHE_HOME=$HOMEDIR/.cache
Environment=MPLCONFIGDIR=$HOMEDIR/.cache/matplotlib
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/data/mind15/run_live.sh
Restart=always
RestartSec=30
StandardOutput=append:/data/mind15/live.log
StandardError=append:/data/mind15/live.log
# sandbox: the whole file system is read-only except the engine's own state; the bot key and the site's secrets are out of reach
# /var/www/aitrading-m15: the web folder for setups.json (created and served by the AI Trading Bot session; MIND15_SETUPS_WEB_DIR)
ReadWritePaths=$M/data $M/journal $M/out $M/research/out $HOMEDIR -/var/www/aitrading-m15
InaccessiblePaths=-$M/secrets $OTHERS
$SANDBOX

[Install]
WantedBy=multi-user.target
UNIT

sudo tee $UNITS/mind15-telegram.service >/dev/null <<UNIT
[Unit]
Description=Mind 15 Telegram alerts and daily summary (reads the engine outputs only); own user + sandbox since 17 Nov 2026
After=network-online.target mind15.service
Wants=network-online.target

[Service]
Type=simple
User=mind15
Group=mind15
WorkingDirectory=/data/mind15
Environment=PYTHONUNBUFFERED=1
Environment=HOME=$HOMEDIR
Environment=XDG_CACHE_HOME=$HOMEDIR/.cache
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/data/venv/bin/python -W ignore -m engine15.telegram_notify
Restart=always
RestartSec=60
Nice=5
StandardOutput=append:/data/mind15/telegram.log
StandardError=append:/data/mind15/telegram.log
# sandbox: it may write only its own state file's folder; the push key is out of reach
ReadWritePaths=$M/data
InaccessiblePaths=-$ETC $OTHERS
$SANDBOX

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl start mind15 mind15-telegram
sleep 15
systemctl is-active --quiet mind15
systemctl is-active --quiet mind15-telegram
trap - ERR
echo "engine: $(systemctl is-active mind15), runs as $(ps -o user= -p "$(systemctl show mind15 -p MainPID --value)")"
echo "bot:    $(systemctl is-active mind15-telegram), runs as $(ps -o user= -p "$(systemctl show mind15-telegram -p MainPID --value)")"
for s in mind15 mind15-telegram; do echo "sandbox score $s: $(systemd-analyze security $s.service 2>/dev/null | tail -1 | grep -oE '[0-9.]+ [A-Z]+')"; done
sudo -u mind15 sudo -n true 2>/dev/null && echo "sudo for mind15: YES (bad)" || echo "sudo for mind15: no"
tail -n 3 $M/live.log | cut -c1-160
echo "NOT yet proven: a full step. Watch the next close for 'step done' and 'web push: pushed'; if it fails: bash $0 --undo"
