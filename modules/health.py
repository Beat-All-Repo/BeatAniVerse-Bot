"""
Health check endpoint + README web viewer for BeatAniVerse Bot.

Routes:
  GET /          → Health check (plain OK)
  GET /health    → Health check (plain OK)
  GET /ping      → JSON alive response
  GET /readme    → Beautiful HTML README (Netflix × RE theme)
  GET /docs      → Same as /readme (alias)
"""

from aiohttp import web
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Path to your HTML readme file ───────────────────────────────────────────
# Place README.html in the same directory as health_check.py (project root)
# or update this path to wherever you put it.
README_HTML_PATH = Path(__file__).parent / "README.html"


def _load_readme_html() -> str:
    """Load the README.html file contents, with a fallback if not found."""
    try:
        return README_HTML_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            f"README.html not found at {README_HTML_PATH}. "
            "Place README.html in your project root to enable /readme route."
        )
        return """<!DOCTYPE html>
<html>
<head><title>BeatAniVerse Bot</title>
<style>body{background:#0a0a0a;color:#ccc;font-family:monospace;
text-align:center;padding:80px;}</style></head>
<body>
<h1 style="color:#E50914;font-size:60px;">BEATANIVERSE</h1>
<p>README.html not found. Place it in the project root.</p>
<p style="color:#555">Expected: {path}</p>
</body></html>""".format(path=README_HTML_PATH)


class HealthCheckServer:
    def __init__(self, port: int = 8080):
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.last_activity = datetime.now()

        # ── Register routes ──────────────────────────────────────────────────
        self.app.router.add_get("/",        self.health_check)
        self.app.router.add_get("/health",  self.health_check)
        self.app.router.add_get("/ping",    self.ping)
        self.app.router.add_get("/readme",  self.readme)   # ← HTML README
        self.app.router.add_get("/docs",    self.readme)   # ← alias

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def health_check(self, request: web.Request) -> web.Response:
        """Plain-text health check for UptimeRobot / Render."""
        return web.Response(text="OK", status=200)

    async def ping(self, request: web.Request) -> web.Response:
        """JSON ping — updates last_activity timestamp."""
        self.last_activity = datetime.now()
        return web.json_response({
            "status": "alive",
            "timestamp": self.last_activity.isoformat(),
            "bot": "BeatAniVerse",
            "version": "2.0.0",
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

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
            await self.site.start()
            logger.info(f"✅ Health server running on port {self.port}")
            logger.info(f"   → /health  (uptime check)")
            logger.info(f"   → /ping    (JSON status)")
            logger.info(f"   → /readme  (HTML README viewer)")
        except Exception as exc:
            logger.error(f"❌ Failed to start health server: {exc}")

    async def stop(self) -> None:
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()


health_server = HealthCheckServer()
