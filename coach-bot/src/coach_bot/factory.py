"""Wire coach dependencies."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from slack_bolt import App
from slack_sdk import WebClient

from coach_bot.activity_watcher import ActivityWatcher
from coach_bot.config import Settings
from coach_bot.context_builder import ContextBuilder
from coach_bot.intervals_client import IntervalsClient
from coach_bot.llm_client import OpenAILlmClient
from coach_bot.orchestrator import CoachOrchestrator
from coach_bot.project_memory import ProjectMemory
from coach_bot.repo_reader import RepoReader
from coach_bot.scheduler_service import SchedulerService
from coach_bot.slack_handlers import register_handlers
from coach_bot.slack_notifier import SlackNotifier
from coach_bot.state_store import StateStore
from coach_bot.supabase_store import NullSupabaseStore, SupabaseStore, build_supabase_store

logger = logging.getLogger(__name__)


@dataclass
class CoachServices:
    settings: Settings
    intervals: IntervalsClient
    orchestrator: CoachOrchestrator
    memory: ProjectMemory
    state: StateStore
    db: SupabaseStore | NullSupabaseStore
    notifier: SlackNotifier
    watcher: ActivityWatcher
    scheduler: SchedulerService
    bolt: App

    def close(self) -> None:
        self.watcher.stop()
        self.scheduler.stop()
        self.intervals.close()


def build_coach_services(settings: Settings) -> CoachServices:
    bolt = App(
        token=settings.slack_bot_token,
        signing_secret=settings.slack_signing_secret,
    )
    db = build_supabase_store(settings)
    intervals = IntervalsClient(settings)
    repo = RepoReader(settings)
    memory = ProjectMemory(repo, db)
    if memory.seed_supabase_from_repo():
        logger.info("Seeded Supabase coach_status from CURRENT_STATUS.md")
    context = ContextBuilder(intervals, memory, settings.tz)
    llm = OpenAILlmClient(settings)
    orchestrator = CoachOrchestrator(context, llm, intervals, db)
    state = StateStore(settings.state_path)
    client = WebClient(token=settings.slack_bot_token)
    notifier = SlackNotifier(client, settings, state, db)
    register_handlers(bolt, orchestrator, settings, db)
    watcher = ActivityWatcher(settings, intervals, orchestrator, notifier, state, db)
    scheduler = SchedulerService(settings, orchestrator, notifier)
    return CoachServices(
        settings=settings,
        intervals=intervals,
        orchestrator=orchestrator,
        memory=memory,
        state=state,
        db=db,
        notifier=notifier,
        watcher=watcher,
        scheduler=scheduler,
        bolt=bolt,
    )
