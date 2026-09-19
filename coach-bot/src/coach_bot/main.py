"""Entry point – Socket Mode (default) or legacy HTTP."""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from coach_bot.config import get_settings
from coach_bot.factory import build_coach_services

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_flask_app(services) -> Flask:
    flask_app = Flask(__name__)
    handler = SlackRequestHandler(services.bolt)

    @flask_app.route("/slack/events", methods=["POST"])
    def slack_events():
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health():
        return jsonify({"ok": True, "service": "lofoten-coach", "mode": services.settings.slack_mode})

    return flask_app


def main() -> None:
    settings = get_settings()
    os.environ.setdefault("TZ", settings.tz)
    services = build_coach_services(settings)
    services.watcher.start()
    services.scheduler.start()

    if settings.slack_mode == "http":
        app = create_flask_app(services)
        logger.info("Lofoten coach HTTP on 0.0.0.0:%s", settings.port)
        try:
            app.run(host="0.0.0.0", port=settings.port, debug=False)
        finally:
            services.close()
        return

    health_app = create_flask_app(services)
    import threading

    threading.Thread(
        target=lambda: health_app.run(
            host="0.0.0.0", port=settings.port, debug=False, use_reloader=False
        ),
        daemon=True,
        name="health-server",
    ).start()
    logger.info("Health on 0.0.0.0:%s", settings.port)

    logger.info("Lofoten coach Socket Mode (no tunnel required)")
    handler = SocketModeHandler(services.bolt, settings.slack_app_token)
    try:
        handler.start()
    finally:
        services.close()


if __name__ == "__main__":
    main()
