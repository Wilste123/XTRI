"""Manual triggers for proactive jobs (testing / ops)."""

from __future__ import annotations

import argparse
import sys

from coach_bot.activity_watcher import ActivityWatcher
from coach_bot.config import get_settings
from coach_bot.factory import build_coach_services


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lofoten coach manual jobs")
    parser.add_argument(
        "job",
        choices=("morning", "weekly", "poll", "chat", "sync-status"),
        help="Job to run once",
    )
    parser.add_argument(
        "--message",
        "-m",
        default="Hva bør jeg fokusere på denne uka?",
        help="For chat job",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    services = build_coach_services(settings)
    try:
        if args.job == "morning":
            text = services.orchestrator.run_morning_brief()
            services.notifier.broadcast(
                f"*God morgen – dagens coach*\n\n{text}",
                message_kind="morning_brief",
            )
        elif args.job == "weekly":
            text = services.orchestrator.run_weekly_brief()
            services.notifier.broadcast(
                f"*Ukentlig oppsummering*\n\n{text}",
                message_kind="weekly_brief",
            )
        elif args.job == "poll":
            services.watcher.poll_once()
        elif args.job == "chat":
            text = services.orchestrator.run_chat(args.message)
            services.notifier.broadcast(text, message_kind="chat")
        elif args.job == "sync-status":
            services.memory.import_status_from_repo()
            print("Synced CURRENT_STATUS.md → Supabase coach_status_snapshots.")
        print(f"Job {args.job} completed.")
        return 0
    finally:
        services.close()


if __name__ == "__main__":
    sys.exit(main())
