"""Entry point – Flask + Slack Bolt HTTP."""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

from coach_bot.config import get_settings
from coach_bot.context_builder import ContextBuilder
from coach_bot.intervals_client import IntervalsClient
from coach_bot.llm_client import OpenAILlmClient
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.repo_reader import RepoReader
from coach_bot.slack_handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    settings = get_settings()
    os.environ.setdefault("TZ", settings.tz)

    bolt = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )

    intervals = IntervalsClient(settings)
    repo = RepoReader(settings)
    context = ContextBuilder(intervals, repo, settings.tz)
    llm = OpenAILlmClient(settings)
    orchestrator = CoachOrchestrator(context, llm)
    register_handlers(bolt, orchestrator, settings)

    flask_app = Flask(__name__)
    handler = SlackRequestHandler(bolt)

    @flask_app.route("/slack/events", methods=["POST"])
    def slack_events():
        return handler.handle(request)

    @flask_app.route("/health", methods=["GET"])
    def health():
        return jsonify({"ok": True, "service": "lofoten-coach"})

    return flask_app


def main() -> None:
    settings = get_settings()
    app = create_app()
    logger.info("Lofoten coach listening on 0.0.0.0:%s", settings.port)
    app.run(host="0.0.0.0", port=settings.port, debug=False)


if __name__ == "__main__":
    main()
