from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from supabase import create_client, Client
import os

from routers import concerts, artists, friends, messages, spotify, discovery, preferences

load_dotenv()

app = FastAPI(title="The Setlist API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(concerts.router,   prefix="/api/concerts",   tags=["concerts"])
app.include_router(artists.router,    prefix="/api/artists",    tags=["artists"])
app.include_router(friends.router,    prefix="/api/friends",    tags=["friends"])
app.include_router(messages.router,   prefix="/api/messages",   tags=["messages"])
app.include_router(spotify.router,    prefix="/api/spotify",    tags=["spotify"])
app.include_router(discovery.router,    prefix="/api/discovery",    tags=["discovery"])
app.include_router(preferences.router,  prefix="/api/preferences",  tags=["preferences"])


def get_supabase() -> Client:
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))


bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    supabase: Client = Depends(get_supabase),
):
    """Verify Supabase JWT and return the user."""
    try:
        user = supabase.auth.get_user(credentials.credentials)
        if not user.user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user.user
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}
