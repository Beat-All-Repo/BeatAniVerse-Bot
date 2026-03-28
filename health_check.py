"""
Health check endpoint for external monitoring.

Routes:
  GET /        → Health check (plain OK)
  GET /health  → Health check (plain OK)
  GET /ping    → JSON alive response
  GET /readme  → Serves README.html from project root
  GET /docs    → Same as /readme (alias)

PORT is read from the PORT environment variable (Render sets this to 10000).
Fallback is 10000 if the variable is not set.
"""
import os
import aiohttp
from aiohttp import web
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Read port from environment (Render sets PORT=10000 automatically) ─────────
_PORT: int = int(os.environ.get("PORT", 10000))

# ── Path to README.html in the project root (same folder as this file) ────────
README_HTML_PATH = Path(__file__).parent / "README.html"


def _load_readme_html() -> str:
    """Load README.html, with a friendly fallback page if not found."""
    try:
        return README_HTML_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            f"README.html not found at {README_HTML_PATH}. "
            "Place README.html in your project root to enable the /readme route."
        )
        return """<!DOCTYPE html>
<html>
<head>
  <title>BeatAniVerse Bot</title>
  <style>
    body {{ background: #0a0a0a; color: #ccc; font-family: monospace;
           text-align: center; padding: 80px; }}
    h1   {{ color: #E50914; font-size: 60px; margin-bottom: 10px; }}
    p    {{ color: #888; }}
  </style>
</head>
<body>
  <h1>BEATANIVERSE</h1>
  <p>README.html not found. Place it in the project root.</p>
  <p style="color:#555">Expected path: {path}</p>
</body>
</html>""".format(path=README_HTML_PATH)


class HealthCheckServer:
    def __init__(self, port: int = _PORT):
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.last_activity = datetime.now()

        # ── Register all routes ────────────────────────────────────────────────
        self.app.router.add_get("/",       self.health_check)
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/ping",   self.ping)
        self.app.router.add_get("/readme", self.readme)   # HTML README viewer
        self.app.router.add_get("/docs",   self.readme)   # alias for /readme

    async def health_check(self, request: web.Request) -> web.Response:
        """Plain-text health check for UptimeRobot / Render port scanner."""
        return web.Response(text="OK", status=200)

    async def ping(self, request: web.Request) -> web.Response:
        """JSON ping — updates last_activity timestamp."""
        self.last_activity = datetime.now()
        return web.json_response({
            "status":    "alive",
            "timestamp": self.last_activity.isoformat(),
            "bot":       "BeatAniVerse",
            "version":   "2.0.0",
        })

    async def readme(self, request: web.Request) -> web.Response:
        """Serve the styled HTML README."""
        html = _load_readme_html()
        return web.Response(
            text=html,
            content_type="text/html",
            charset="utf-8",
            status=200,
        )

    async def _self_ping_loop(self) -> None:
        """
        Self-ping loop: hits /health every 10 minutes to prevent Render free-tier
        spin-down (which happens after 15 min of no HTTP traffic).
        Also sends a Telegram getMe() call to keep the bot connection warm.
        """
        import asyncio as _aio
        await _aio.sleep(60)  # wait 1 min after startup before first ping
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://localhost:{self.port}/health",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            self.last_activity = datetime.now()
                            logger.debug("[keep-alive] self-ping OK")
            except Exception as exc:
                logger.debug(f"[keep-alive] self-ping failed (non-fatal): {exc}")
            await _aio.sleep(600)  # ping every 10 minutes

    async def start(self) -> None:
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()
            logger.info(f"Health check server running on port {self.port}")
            logger.info(f"   -> /health  (uptime check)")
            logger.info(f"   -> /ping    (JSON status)")
            logger.info(f"   -> /readme  (HTML README viewer)")
            logger.info(f"   -> /docs    (alias for /readme)")
            # Start keep-alive loop to prevent Render free-tier spin-down
            import asyncio as _aio
            _aio.ensure_future(self._self_ping_loop())
            logger.info("   -> keep-alive loop started (pings /health every 10 min)")
        except Exception as exc:
            logger.error(f"Failed to start health server: {exc}")

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()


# ── Instantiate using the port read from environment ──────────────────────────
health_server = HealthCheckServer(port=_PORT)
