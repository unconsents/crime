import asyncio
import os
import sys
import time

import psutil

STATS_UPDATE_INTERVAL_SECONDS = 3

process = psutil.Process(os.getpid())
process.cpu_percent(interval=None)

START_TIME = time.monotonic()

counters = {
    "gateway_events": 0,
    "http_requests": 0,
}

def bump_event():
    counters["gateway_events"] += 1

def bump_request():
    counters["http_requests"] += 1

def uptime_str():
    secs = int(time.monotonic() - START_TIME)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"

def set_window_title(title):
    if sys.platform.startswith("win"):
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(str(title))
    else:
        sys.stdout.write(f"\x1b]0;{title}\x07")
        sys.stdout.flush()

def build_title(username):
    cpu = process.cpu_percent(interval=None)
    who = username or "connecting..."
    return (
        f"crime | {who} | "
        f"CPU {cpu:.1f}% | "
        f"Events {counters['gateway_events']} | "
        f"Requests {counters['http_requests']} | "
        f"Uptime {uptime_str()}"
    )

async def title_update_loop(get_username):
    while True:
        try:
            title = build_title(get_username())
            set_window_title(title)
        except Exception:
            pass
        await asyncio.sleep(STATS_UPDATE_INTERVAL_SECONDS)