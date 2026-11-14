# -*- coding: utf-8 -*-
"""resources -- keep RL jobs lean beside the live engine (8 GB laptop, often < 1.5 GB free).

  low_priority()   this process -> BELOW_NORMAL priority class (Windows; nice +5 elsewhere)
  free_mb()        physical memory available to new allocations, MB (GlobalMemoryStatusEx; no psutil)
  wait_for_memory  block until at least `need_mb` is free, or give up after `max_wait_s`
  MemoryLow        raised by the training guard when free memory falls under the floor

Rules (owner, Phase 2): start a seed/fold only with >= 700 MB free; stop our own process cleanly
if free memory falls under 350 MB during a run; one heavy job at a time; torch on 2 threads.
"""
import ctypes
import os
import sys
import time

START_MB = 700
FLOOR_MB = 350


class MemoryLow(RuntimeError):
    pass


def low_priority():
    try:
        if sys.platform == "win32":
            k = ctypes.windll.kernel32
            k.SetPriorityClass(k.GetCurrentProcess(), 0x00004000)     # BELOW_NORMAL_PRIORITY_CLASS
        else:
            os.nice(5)
        return True
    except Exception:
        return False


class _MemStatus(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_mb():
    """Available physical memory in MB (None if it cannot be read)."""
    try:
        if sys.platform == "win32":
            st = _MemStatus()
            st.dwLength = ctypes.sizeof(_MemStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
            return st.ullAvailPhys / 1048576.0
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024.0
    except Exception:
        return None
    return None


def wait_for_memory(need_mb=START_MB, max_wait_s=600, poll_s=20, log=None):
    """-> True once free_mb() >= need_mb; False if it never got there within max_wait_s."""
    t0 = time.time()
    while True:
        f = free_mb()
        if f is None or f >= need_mb:
            return True
        if time.time() - t0 >= max_wait_s:
            return False
        if log:
            log("waiting for memory: %.0f MB free, need %d MB" % (f, need_mb))
        time.sleep(poll_s)


def torch_lean(threads=2):
    import torch
    torch.set_num_threads(int(threads))
    try:
        torch.set_num_interop_threads(1)
    except RuntimeError:
        pass
    return torch


class MemoryPause:
    """Phase 3 rule: start heavy work only with >= start_mb free; if free memory drops under floor_mb, PAUSE
    (sleep, poll) until start_mb is free again, then carry on. Never fails; every pause is recorded."""

    def __init__(self, start_mb=START_MB, floor_mb=FLOOR_MB, poll_s=20, log=None):
        self.start_mb, self.floor_mb, self.poll_s, self.log = float(start_mb), float(floor_mb), poll_s, log
        self.events = []

    def _wait(self, why, where):
        t0 = time.time()
        f0 = free_mb()
        while True:
            f = free_mb()
            if f is None or f >= self.start_mb:
                break
            if self.log:
                self.log("memory pause (%s): %.0f MB free, waiting for %d MB" % (where, f, self.start_mb))
            time.sleep(self.poll_s)
        waited = time.time() - t0
        if waited > 1:
            self.events.append({"utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t0)), "where": where,
                                "why": why, "free_mb_at_pause": None if f0 is None else round(f0),
                                "waited_s": round(waited)})
        return waited

    def before_start(self, where=""):
        f = free_mb()
        if f is not None and f < self.start_mb:
            return self._wait("under %d MB free before starting" % self.start_mb, where)
        return 0.0

    def check(self, where=""):
        f = free_mb()
        if f is not None and f < self.floor_mb:
            return self._wait("under the %d MB floor while running" % self.floor_mb, where)
        return 0.0
