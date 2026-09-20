"""Entry point – Slack Socket Mode + health HTTP."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

from flask import Flask, jsonify, request
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from coach_bot.config import get_settings
from coach_bot.context_builder import ContextBuilder
from coach_bot.intervals_client import IntervalsClient
from coach_bot.llm_client import OpenAILlmClient
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.proactive import start_proactive_schedulers
from coach_bot.repo_reader import RepoReader
from coach_bot.repo_writer import RepoWriter
from coach_bot.github_repo import GitHubRepoSync
from coach_bot.memory_learn import MemoryLearner
from coach_bot.session_store import SessionStore
from coach_bot.slack_handlers import register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_health_app(
    intervals: IntervalsClient,
    repo: RepoReader,
    orchestrator: CoachOrchestrator | None = None,
    settings=None,
    slack_client: WebClient | None = None,
) -> Flask:
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

    @flask_app.route("/admin/briefing", methods=["POST"])
    def admin_briefing():
        if not settings or not orchestrator or not slack_client:
            return jsonify({"ok": False, "error": "not configured"}), 503
        secret = settings.admin_briefing_secret.strip()
        if not secret or request.headers.get("X-Admin-Secret") != secret:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        btype = (request.args.get("type") or "test").lower()
        user_ids = list(settings.allowed_user_id_set)
        if not user_ids:
            return jsonify({"ok": False, "error": "no ALLOWED_SLACK_USER_IDS"}), 400
        from coach_bot.slack_post import deliver_coach_reply

        for uid in user_ids:
            if btype == "morning":
                orchestrator.deliver_morning_briefing(slack_client, uid)
            elif btype == "week":
                orchestrator.deliver_weekly_briefing(slack_client, uid)
            else:
                deliver_coach_reply(
                    slack_client,
                    uid,
                    orchestrator.run_chat("briefing: test", user_id=uid),
                    label="Admin test",
                )
        return jsonify({"ok": True, "type": btype, "users": len(user_ids)})

    return flask_app


def main() -> None:
    settings = get_settings()
    os.environ.setdefault("TZ", settings.tz)

    bot_root = Path(__file__).resolve().parent.parent.parent
    db_path = bot_root / settings.session_db_path

    intervals = IntervalsClient(settings)
    github = GitHubRepoSync(settings)
    if github.enabled:
        pulled = github.pull_sync_files()
        if pulled:
            logger.info("GitHub sync pulled: %s", ", ".join(pulled))
    repo = RepoReader(settings)
    from coach_bot.repo_health import check_week_plan

    check_week_plan(repo, settings)
    week_ov = settings.coach_week_override.strip() or None
    context = ContextBuilder(intervals, repo, settings.tz, week_override=week_ov)
    llm = OpenAILlmClient(settings)
    sessions = SessionStore(db_path, settings.session_max_turns)
    repo_writer = RepoWriter(settings, github=github if github.enabled else None)
    memory_learner = MemoryLearner(settings, github if github.enabled else None)
    orchestrator = CoachOrchestrator(
        context,
        llm,
        sessions,
        repo_writer,
        intervals=intervals,
        repo=repo,
        memory_learner=memory_learner,
        github=github if github.enabled else None,
        max_bulk_events=settings.intervals_max_bulk_events,
    )

    bolt = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    register_handlers(bolt, orchestrator, settings)

    slack_client = WebClient(token=settings.slack_bot_token)
    try:
        auth = slack_client.auth_test()
        logger.info(
            "Slack bot connected: user_id=%s user=%s team=%s",
            auth.get("user_id"),
            auth.get("user"),
            auth.get("team"),
        )
    except Exception as e:
        logger.error("Slack auth_test failed – sjekk SLACK_BOT_TOKEN: %s", e)

    start_proactive_schedulers(settings, slack_client, orchestrator)

    health_app = create_health_app(
        intervals, repo, orchestrator, settings, slack_client=slack_client
    )
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
