import logging
from pprint import pformat
from typing import cast

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from ekaine.common.constants import (
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    GRAFANA_URL,
    SESSION_SECRET,
)
from ekaine.common.logging import configure_logger, get_logger
from ekaine.postgresql import AsyncSessionLocal

configure_logger(logging.INFO)
logger = get_logger(__name__)

"""EKAINE FastApi

Currently only used as a custom implemented OAuth2 proxy for Discord OAuth2
Originally tried using oauth2-proxy but I couldn't get it configured to work with Discord
with the available providers. As such, this file is a relatively lightweight implementation for it.

The file contains four real endpoints and everything else gets proxied directly to the Grafana container that's
only accessible through the local Docker network. In other words, any and all requests to Grafana is processed and
responded to by this proxy.
- /oauth2/login
- /oauth2/callback
- /oauth2/auth
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

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

oauth = OAuth()
oauth.register(
    name="discord",
    client_id=DISCORD_CLIENT_ID,
    client_secret=DISCORD_CLIENT_SECRET,
    authorize_url="https://discord.com/api/oauth2/authorize",
    access_token_url="https://discord.com/api/oauth2/token",
    client_kwargs={"scope": "identify"},
    api_base_url="https://discord.com/api/",
)


async def maybe_initialize_cache(user_id: str) -> None:
    """
    Grafana inserts these caches per query. If multiple queries are executing simultaneously on a cold cache,
    a race condition can occur with multiple INSERT INTO's with no ON CONFLICT. This can then fail, failing the request.

    We bypass this by initializing the cache before we proxy the request to Grafana.
    """
    key = f"authn-proxy-sync-ttl:{user_id}"
    async with AsyncSessionLocal() as session:
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


@app.get("/oauth2/login")
async def login(request: Request) -> Response:
    logger.info("Calling /oauth2/login")
    logger.info(pformat(request))

    redirect_uri = request.url_for("auth_callback")
    return cast(Response, await oauth.discord.authorize_redirect(request, redirect_uri))


@app.get("/oauth2/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    logger.info("Calling /oauth2/callback")
    logger.info(pformat(request))

    token = await oauth.discord.authorize_access_token(request)
    user = await oauth.discord.get("users/@me", token=token)
    request.session["user"] = user.json()
    return RedirectResponse(url="/")  # or /grafana


@app.get("/oauth2/auth")
async def auth_check(request: Request) -> JSONResponse:
    logger.info("Calling /oauth2/auth")
    logger.info(pformat(request))

    user = request.session.get("user")
    if user:
        headers = {
            "X-Forwarded-Discord-Username": user["username"],
            "X-Forwarded-Discord-ID": user["id"],
        }
        return JSONResponse(status_code=200, content={}, headers=headers)
    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})


@app.get("/logout", response_model=None)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], response_model=None)
async def proxy_all_other_requests(request: Request, path: str) -> RedirectResponse | Response:
    # Skip auth-protected endpoints
    if path.startswith("oauth2/"):
        return Response("Not Found", status_code=404)

    user = request.session.get("user")
    if not user:
        return RedirectResponse("/oauth2/login")

    if GRAFANA_URL is None:
        return Response("Internal Server Error - Grafana Url Missing", status_code=500)

    # Build the full URL to proxy to Grafana
    target_url = f"{GRAFANA_URL}/{path}"

    username = user["username"]
    headers = dict(request.headers)
    headers["X-Forwarded-Discord-Username"] = username
    headers["X-Forwarded-Discord-ID"] = user["id"]

    await maybe_initialize_cache(username)

    body = await request.body()

    timeout = httpx.Timeout(60.0, connect=5.0, read=60.0)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        grafana_response = await client.request(
            request.method,
            target_url,
            headers=headers,
            content=body,
            cookies=request.cookies,
            params=request.query_params,
        )

    final_headers = {
        k: v
        for k, v in grafana_response.headers.items()
        if k.lower() not in ("content-encoding", "transfer-encoding", "connection")
    }

    return Response(content=grafana_response.content, status_code=grafana_response.status_code, headers=final_headers)
