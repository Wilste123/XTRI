"""Coach orchestration for Slack DM."""

from __future__ import annotations

from slack_sdk import WebClient

from coach_bot.charts import render_ctl_atl_chart, render_discipline_week_chart
from coach_bot.coach_reply import CoachReply
from coach_bot.context_builder import ContextBuilder
from coach_bot.intent import (
    Intent,
    asks_capabilities,
    asks_for_charts,
    asks_for_plan_sync,
    detect_intent,
    strip_log_prefix,
)
from coach_bot.intervals_client import IntervalsClient
from coach_bot.intervals_planner import events_for_active_week, parse_single_workout_request
from coach_bot.llm_client import LlmClient
from coach_bot.repo_reader import RepoReader
from coach_bot.repo_writer import RepoWriter
from coach_bot.session_store import SessionStore
from coach_bot.slack_delivery import post_dm
from coach_bot.slack_format import briefing_blocks, parse_brief_sections, week_preview_blocks


class CoachOrchestrator:
    def __init__(
        self,
        context: ContextBuilder,
        llm: LlmClient,
        sessions: SessionStore | None = None,
        repo_writer: RepoWriter | None = None,
        intervals: IntervalsClient | None = None,
        repo: RepoReader | None = None,
        max_bulk_events: int = 14,
    ) -> None:
        self._context = context
        self._llm = llm
        self._sessions = sessions
        self._repo_writer = repo_writer
        self._intervals = intervals
        self._repo = repo
        self._max_bulk_events = max_bulk_events

    def _history_messages(self, user_id: str) -> list[dict[str, str]]:
        if not self._sessions or not user_id:
            return []
        msgs = self._sessions.get_messages(user_id)
        if msgs and msgs[-1]["role"] == "user":
            return msgs[:-1]
        return msgs

    def _wrap_llm_reply(self, text: str, intent: Intent, title: str) -> CoachReply:
        sections = parse_brief_sections(text)
        hook = sections[0][1].strip().split("\n")[0][:200] if sections else text[:200]
        blocks = briefing_blocks(title, hook or text[:200], sections[1:] or sections)
        return CoachReply(text=text, blocks=blocks)

    def _attach_charts(self, reply: CoachReply, bundle: dict, as_of) -> CoachReply:
        paths = []
        p1 = render_ctl_atl_chart(bundle.get("wellness") or [])
        p2 = render_discipline_week_chart(bundle.get("activities") or [], as_of)
        if p1:
            paths.append(p1)
        if p2:
            paths.append(p2)
        reply.image_paths = paths
        return reply

    def run_chat(self, user_message: str, user_id: str = "") -> CoachReply:
        text = (user_message or "").strip()
        has_history = bool(self._sessions and user_id and self._sessions.get_messages(user_id))

        if text.lower() in ("nullstill", "reset", "ny samtale"):
            if self._sessions and user_id:
                self._sessions.clear(user_id)
            return CoachReply(text="Samtalehistorikk nullstillet. Hva vil du ta opp?")

        briefing_reply = self._handle_briefing_command(text, user_id)
        if briefing_reply:
            return briefing_reply

        confirmed = self._try_confirm_pending(text, user_id)
        if confirmed:
            self._remember(user_id, text, confirmed.text)
            return confirmed

        intent = detect_intent(text, has_history=has_history)

        if intent == Intent.LOG and self._repo_writer:
            note = strip_log_prefix(text)
            if not note:
                return CoachReply(text="Skriv f.eks. `logg: kne 3/10 etter løp`.")
            self._repo_writer.append_status_note(note)
            reply = CoachReply(text=f"Notert i CURRENT_STATUS: {note}")
            self._remember(user_id, text, reply.text)
            return reply

        sync_reply = self._handle_sync_week(text, user_id, intent)
        if sync_reply:
            return sync_reply

        single_reply = self._handle_single_workout(text, user_id)
        if single_reply:
            return single_reply

        history_messages = self._history_messages(user_id)
        ctx = self._context.for_chat(text, intent=intent)
        llm_text = self._llm.complete_chat(
            ctx,
            text,
            intent=intent,
            history_messages=history_messages if history_messages else None,
        )

        title = {
            Intent.STATUS: "LOFOTEN 2027 STATUS",
            Intent.WEEK: "UKESTATUS",
            Intent.TOMORROW: "I dag / i morgen",
            Intent.ANALYSIS: "Analyse",
            Intent.CHART: "Grafer",
        }.get(intent, "Coach")

        reply = self._wrap_llm_reply(llm_text, intent, title)

        if intent in (Intent.WEEK, Intent.STATUS, Intent.CHART, Intent.ANALYSIS) and self._intervals:
            bundle = self._intervals.fetch_coach_bundle()
            from coach_bot.aggregates import build_training_snapshot

            snap = build_training_snapshot(bundle["activities"], tz=self._context._tz)
            reply = self._attach_charts(reply, bundle, snap.as_of)
            if intent in (Intent.WEEK, Intent.CHART, Intent.ANALYSIS) and not reply.image_paths:
                reply.text += "\n\n_(Grafer mangler – for lite wellness/øktdata i Intervals.)_"

        self._remember(user_id, text, reply.text)
        return reply

    def _remember(self, user_id: str, user_msg: str, assistant_msg: str) -> None:
        if self._sessions and user_id:
            self._sessions.append(user_id, "user", user_msg)
            self._sessions.append(user_id, "assistant", assistant_msg)

    def _handle_briefing_command(self, text: str, user_id: str) -> CoachReply | None:
        lower = text.lower().strip()
        if not lower.startswith("briefing:"):
            return None
        sub = lower.split(":", 1)[1].strip()
        if sub == "test":
            return CoachReply(
                text="Coach-bot proaktiv test OK – Slack DM fungerer.",
                blocks=briefing_blocks(
                    "Proaktiv test",
                    "Coach-bot kan sende meldinger til deg uten at du skriver først.",
                    [("Neste steg", "Prøv `briefing: morgen` eller `briefing: uke` for full briefing.")],
                ),
            )
        if sub in ("morgen", "morning"):
            body = self.run_morning_briefing()
            return self._wrap_llm_reply(body, Intent.TOMORROW, "Morgenbriefing")
        if sub in ("uke", "week", "ukentlig"):
            body = self.run_weekly_briefing()
            reply = self._wrap_llm_reply(body, Intent.WEEK, "Ukebriefing")
            if self._intervals:
                bundle = self._intervals.fetch_coach_bundle()
                from coach_bot.aggregates import build_training_snapshot

                snap = build_training_snapshot(bundle["activities"], tz=self._context._tz)
                reply = self._attach_charts(reply, bundle, snap.as_of)
            return reply
        return CoachReply(text="Ukjent briefing. Prøv `briefing: test`, `briefing: morgen` eller `briefing: uke`.")

    def _try_confirm_pending(self, text: str, user_id: str) -> CoachReply | None:
        if not self._sessions:
            return None
        lower = text.lower().strip()
        if lower in ("avbryt", "nei", "cancel"):
            if self._sessions.has_pending(user_id):
                self._sessions.pop_pending(user_id)
                return CoachReply(text="Avbrutt – ingen endringer i Intervals.")
            return None
        if lower not in ("ja", "yes", "legg inn", "ok", "gjør det"):
            return None
        pending = self._sessions.pop_pending(user_id)
        if not pending:
            return CoachReply(
                text="Ingen ventende ukeplan å bekrefte. Skriv «synk kalender» eller «legg inn uke i intervals» først."
            )
        if not self._intervals:
            return None
        action_type, payload = pending
        if action_type != "intervals_week":
            return None
        events = payload.get("events") or []
        if len(events) > self._max_bulk_events:
            return CoachReply(text=f"Maks {self._max_bulk_events} økter per sync – del opp uken.")
        try:
            created = self._intervals.bulk_upsert_events(events)
            n = len(created) if created else len(events)
            return CoachReply(
                text=f"Lagt inn {n} økter i Intervals-kalenderen. Sjekk kalenderen i appen.",
                blocks=week_preview_blocks(events),
            )
        except Exception as e:
            return CoachReply(text=f"Kunne ikke skrive til Intervals: {e}")

    def _handle_sync_week(self, text: str, user_id: str, intent: Intent) -> CoachReply | None:
        if intent != Intent.SYNC_WEEK or not self._repo or not self._sessions:
            return None
        events = events_for_active_week(self._repo)
        if not events:
            return CoachReply(text="Fant ingen økter å synce fra aktiv ukeplan i repo.")
        self._sessions.set_pending(user_id, "intervals_week", {"events": events})
        preview = "\n".join(
            f"- {(e.get('start_date_local') or '')[:10]}: {e.get('name')}" for e in events[:14]
        )
        return CoachReply(
            text=f"Forhåndsvisning ({len(events)} økter):\n{preview}\n\nSvar *ja* for å legge inn i Intervals.",
            blocks=week_preview_blocks(events),
        )

    def _handle_single_workout(self, text: str, user_id: str) -> CoachReply | None:
        if not self._intervals:
            return None
        today = self._intervals.today()
        event = parse_single_workout_request(text, today)
        if not event:
            return None
        try:
            self._intervals.create_event(event)
            d = (event.get("start_date_local") or "")[:10]
            name = event.get("name") or "Økt"
            reply = CoachReply(text=f"Lagt inn i Intervals: {d} – {name}")
            self._remember(user_id, text, reply.text)
            return reply
        except Exception as e:
            return CoachReply(text=f"Kunne ikke legge inn økt: {e}")

    def run_morning_briefing(self) -> str:
        prompt = (
            "Gi en kort morgenmelding for I DAG og I MORGEN: plan fra events, "
            "belastning siste dager, anbefalt intensitet (RPE), og ett konkret fokus."
        )
        ctx = self._context.for_chat(prompt, intent=Intent.TOMORROW)
        return self._llm.complete_chat(ctx, prompt, intent=Intent.TOMORROW)

    def run_weekly_briefing(self) -> str:
        prompt = "Gi UKESTATUS: gjennomført, belastning, risiko, endringer, neste uke."
        ctx = self._context.for_chat(prompt, intent=Intent.WEEK)
        return self._llm.complete_chat(ctx, prompt, intent=Intent.WEEK)

    def deliver_morning_briefing(self, client: WebClient, user_id: str) -> None:
        reply = self._handle_briefing_command("briefing: morgen", user_id)
        if reply:
            self._deliver_reply(client, user_id, reply, label="Morgenbriefing")

    def deliver_weekly_briefing(self, client: WebClient, user_id: str) -> None:
        reply = self._handle_briefing_command("briefing: uke", user_id)
        if reply:
            self._deliver_reply(client, user_id, reply, label="Ukebriefing")

    def _deliver_reply(self, client: WebClient, user_id: str, reply: CoachReply, label: str) -> None:
        from coach_bot.slack_post import deliver_coach_reply

        deliver_coach_reply(client, user_id, reply, label=label)
