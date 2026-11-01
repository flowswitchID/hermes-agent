#!/usr/bin/env python
"""Socket-activated launcher for universal_solver with idle auto-exit.

systemd passes the listening socket as fd 3 (LISTEN_FDS_START).
Service exits after SOLVER_IDLE_MIN minutes without requests;
the .socket unit keeps listening and re-triggers the service on demand.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IDLE_MIN = int(os.getenv("SOLVER_IDLE_MIN", "10"))
LISTEN_FDS_START = 3

fd = LISTEN_FDS_START  # systemd socket activation: fd 3 = listening socket

# import the real app (its __main__ guard prevents uvicorn.run inside)
import universal_solver
from starlette.middleware.base import BaseHTTPMiddleware

app = universal_solver.app

# Track last request time via middleware
_last_request = time.time()


class IdleTracker(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        global _last_request
        _last_request = time.time()
        return await call_next(request)


app.add_middleware(IdleTracker)


async def idle_watcher():
    global _last_request
    while True:
        await asyncio.sleep(30)
        if time.time() - _last_request > IDLE_MIN * 60:
            print(f"IDLE {IDLE_MIN}min — exiting, socket re-activates on demand",
                  flush=True)
            os._exit(0)


@app.on_event("startup")
async def _start_idle_watcher():
    asyncio.create_task(idle_watcher())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, fd=fd, log_level="info", workers=1)
