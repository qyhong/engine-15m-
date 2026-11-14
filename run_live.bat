@echo off
rem Mind 15: keep the paper engine stepping after every 15-minute close.
rem Leave this window open. Close it (or press Ctrl+C) to stop. Paper only: no orders are placed.
cd /d "%~dp0"
py -3 -u -m engine15 live >> out\live.log 2>&1
