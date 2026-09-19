"""Entry point – Slack Socket Mode + health HTTP."""

from __future__ import annotations

import logging
import os
import threading

from flask import Flask, jsonify
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from coach_bot.config import get_settings
from coach_bot.context_builder import ContextBuilder
from coach_bot.intervals_client import IntervalsClient
from coach_bot.llm_client import OpenAILlmClient
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.proactive import start_morning_scheduler
from coach_bot.repo_reader import RepoReader
from coach_bot.slack_handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_health_app(intervals: IntervalsClient, repo: RepoReader) -> Flask:
    flask_app = Flask(__name__)

    @flask_app.route("/health", methods=["GET"])
    def health():
        return jsonify({"ok": True, "service": "lofoten-coach", "mode": "socket"})

    @flask_app.route("/ready", methods=["GET"])
    def ready():
        checks: dict[str, str] = {}
        ok = True

        if repo.has_current_status():
            checks["repo"] = "ok"
        else:
            checks["repo"] = "missing CURRENT_STATUS.md under LOFOTEN-2027"
            ok = False

        try:
            intervals.ping()
            checks["intervals"] = "ok"
        except Exception as e:
            checks["intervals"] = str(e)
            ok = False

        return jsonify({"ok": ok, "checks": checks}), 200 if ok else 503

    return flask_app


def main() -> None:
    settings = get_settings()
    os.environ.setdefault("TZ", settings.tz)

    intervals = IntervalsClient(settings)
    repo = RepoReader(settings)
    context = ContextBuilder(intervals, repo, settings.tz)
    llm = OpenAILlmClient(settings)
    orchestrator = CoachOrchestrator(context, llm)

    bolt = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    register_handlers(bolt, orchestrator, settings)

    slack_client = WebClient(token=settings.slack_bot_token)
    start_morning_scheduler(settings, slack_client, orchestrator)

    health_app = create_health_app(intervals, repo)
    threading.Thread(
        target=lambda: health_app.run(
            host="0.0.0.0",
            port=settings.port,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
    ).start()
    logger.info("Health on http://0.0.0.0:%s/health and /ready", settings.port)

    handler = SocketModeHandler(bolt, settings.slack_app_token)
    logger.info("Lofoten coach – Slack Socket Mode (DM)")
    handler.start()


if __name__ == "__main__":
    main()
