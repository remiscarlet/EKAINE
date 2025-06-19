import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from starlette.datastructures import URL

from ekaine.common.constants import (
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URI,
    GRAFANA_URL,
    REDIS_DSN,
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
)
from ekaine.common.logging import configure_logger, get_logger
from ekaine.postgresql import AsyncSessionLocalGrafana

configure_logger(logging.INFO)
logger = get_logger(__name__)

"""EKAINE FastApi

Currently only used as a custom implemented OAuth2 proxy for Discord OAuth2
Originally tried using oauth2-proxy but I couldn't get it configured to work with Discord
with the available providers. As such, this file is a relatively lightweight implementation for it.

The file contains four real endpoints and everything else gets proxied directly to the Grafana container that's
only accessible through the local Docker network. In other words, any and all requests to Grafana is processed and
responded to by this proxy.
- /oauth2/callback
- /login
- /logout
    - Grafana doesn't offer a custom logout url so we have to match Grafana's hardcoded path

Communication Flow:
[Browser]
    V
[OAuth2 Proxy] (Public IP) <-> [Discord Servers] (Token Validation)
    V
[Grafana Cluster] (Accessible only through internal Docker network)
    V
[Postgresql] (Internal docker network OR mTLS)
"""

# Initialize
app = FastAPI()
redis: Redis = Redis.from_url(
    REDIS_DSN,
    encoding="utf-8",
    decode_responses=True,
)


async def maybe_initialize_cache(user_id: str) -> None:
    """
    Grafana inserts these caches per query. If multiple queries are executing simultaneously on a cold cache,
    a race condition can occur with multiple INSERT INTO's with no ON CONFLICT. This can then fail, failing the request.

    We bypass this by initializing the cache before we proxy the request to Grafana.
    """
    key = f"authn-proxy-sync-ttl:{user_id}"
    async with AsyncSessionLocalGrafana() as session:
        await session.execute(
            text(
                """
                INSERT INTO cache_data (cache_key, data, created_at, expires)
                VALUES (
                    :key,
                    '{}',
                    EXTRACT(EPOCH FROM now())::BIGINT,
                    EXTRACT(EPOCH FROM now() + interval '1 hour')::BIGINT
                )
                ON CONFLICT DO NOTHING
            """
            ),
            {"key": key},
        )


def _session_key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_current_user(request: Request) -> Dict[str, Any]:
    session_id: Optional[str] = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        raise HTTPException(status_code=401)

    try:
        data: Optional[str] = await redis.get(_session_key(session_id))
    except RedisError:
        raise HTTPException(status_code=500, detail="Session store error")

    if not data:
        raise HTTPException(status_code=401)

    return json.loads(data)  # type: ignore


@app.get("/login")
async def login(next: str = "/") -> RedirectResponse:
    # Pass original path in state for post-auth redirect
    auth_url = URL("https://discord.com/api/oauth2/authorize").include_query_params(
        client_id=DISCORD_CLIENT_ID,
        redirect_uri=DISCORD_REDIRECT_URI,
        response_type="code",
        scope="identify",
        state=next,
    )
    return RedirectResponse(str(auth_url))


@app.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    session_id: Optional[str] = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        await redis.delete(_session_key(session_id))

    response = RedirectResponse(url="/login")
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/oauth2/callback")
async def oauth2_callback(request: Request) -> RedirectResponse:
    code: Optional[str] = request.query_params.get("code")
    state: str = request.query_params.get("state", "/")
    if not code:
        raise HTTPException(status_code=400, detail="Missing code")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        user_resp = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        user_resp.raise_for_status()
        user = user_resp.json()

    # Create a new session
    session_id = str(uuid.uuid4())
    await redis.set(
        _session_key(session_id),
        json.dumps({"id": user["id"], "username": user["username"]}),
        ex=SESSION_TTL_SECONDS,
    )

    response = RedirectResponse(state)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, path: str) -> Response:
    # Authenticate manually to catch 401s
    try:
        user = await get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            # Redirect to login, preserving original path
            return RedirectResponse(url=f"/login?next=/{path}")
        raise

    # Build target URL
    target = f"{GRAFANA_URL}/{path}"

    # Forward headers (excluding hop-by-hop)
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower()
        not in (
            "host",
            "connection",
            "keep-alive",
            "proxy-authenticate",
            "proxy-authorization",
            "te",
            "trailers",
            "transfer-encoding",
            "upgrade",
        )
    }

    logger.info(user)

    # Inject Grafana auth headers
    username = user.get("username", "")
    if not username:
        logger.error("Got a user from current context yet did not contain a valid username!")
        return RedirectResponse(url="/logout")

    headers["X-Forwarded-Discord-Username"] = username

    await maybe_initialize_cache(username)

    # Forward the request
    async with httpx.AsyncClient(follow_redirects=True) as client:
        proxied = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            content=await request.body(),
            params=request.query_params,
            timeout=60.0,
        )

    # Build the response
    return Response(
        content=proxied.content,
        status_code=proxied.status_code,
        headers={
            k: v
            for k, v in proxied.headers.items()
            if k.lower()
            not in (
                "content-encoding",
                "transfer-encoding",
                "connection",
            )
        },
    )
