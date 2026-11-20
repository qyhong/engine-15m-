#!/bin/bash
# Mind 15 live loop on the Singapore box. ENGINE15_PUSH comes from the caller (0 = shadow, 1 = live push).
set -a; . /data/mind15/mind15.env; set +a
cd /data/mind15
exec /data/venv/bin/python -W ignore -u -m engine15 live
