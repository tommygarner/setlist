import os
from pathlib import Path
import httpx
import inspect

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
# Always load backend/.env so local project settings win over stale shell env vars.
load_dotenv(BASE_DIR / ".env", override=True)

# Work around environments where installed httpx expects "proxies" but
# upstream auth clients pass "proxy". Keep behavior identical otherwise.
if "proxy" not in inspect.signature(httpx.Client.__init__).parameters:
    _httpx_client_init = httpx.Client.__init__

    def _patched_httpx_client_init(self, *args, proxy=None, **kwargs):
        if proxy is not None and "proxies" not in kwargs:
            kwargs["proxies"] = proxy
        return _httpx_client_init(self, *args, **kwargs)

    httpx.Client.__init__ = _patched_httpx_client_init

from routers import concerts, artists, friends, messages, spotify, discovery, preferences

app = FastAPI(title="The Setlist API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(concerts.router,     prefix="/api/concerts",     tags=["concerts"])
app.include_router(artists.router,      prefix="/api/artists",      tags=["artists"])
app.include_router(friends.router,      prefix="/api/friends",      tags=["friends"])
app.include_router(messages.router,     prefix="/api/messages",     tags=["messages"])
app.include_router(spotify.router,      prefix="/api/spotify",      tags=["spotify"])
app.include_router(discovery.router,    prefix="/api/discovery",    tags=["discovery"])
app.include_router(preferences.router,  prefix="/api/preferences",  tags=["preferences"])


@app.get("/health")
def health():
    return {"status": "ok"}
