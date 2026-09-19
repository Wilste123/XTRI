"""Coach orchestration for Slack DM."""

from __future__ import annotations

import logging

from slack_sdk import WebClient

logger = logging.getLogger(__name__)

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
    wants_week_plan_write,
)
from coach_bot.intervals_client import IntervalsClient
from coach_bot.intervals_planner import events_for_active_week, parse_single_workout_request
from coach_bot.workout_extract import (
    asks_workout_for_calendar,
    extract_week_plan_from_text,
    extract_workout_from_text,
    is_commit_message,
    wants_full_plan,
    wants_intervals_write,
)
from coach_bot.llm_client import LlmClient
from coach_bot.repo_reader import RepoReader
from coach_bot.repo_writer import RepoWriter
from coach_bot.session_store import SessionStore
from coach_bot.slack_delivery import post_dm
from coach_bot.slack_compose import compact_system_message, natural_reply
from coach_bot.slack_format import single_workout_preview_blocks, week_preview_blocks


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
        # Coachens egne svar skal føles som en ekte mentor på DM – ren tekst,
        # ingen «tittelkort», og aldri en fornektelse av egne evner.
        return natural_reply(text)

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

        if asks_workout_for_calendar(text):
            reply = self._propose_workout_for_calendar(text, user_id)
            self._remember(user_id, text, reply.text)
            return reply

        # Kombinert «grafer + treningsplan»-spørsmål besvares deterministisk
        # (charts + forhåndsvisning) – før uke-sync og write-oppfølgeren, som
        # ellers fanger «legge inn …» i teksten.
        if asks_capabilities(text) or (asks_for_charts(text) and asks_for_plan_sync(text)):
            reply = self._reply_graphics_and_plan(text, user_id)
            self._remember(user_id, text, reply.text)
            return reply

        # Rene «legg inn ukeplan / synk kalender»-forespørsler -> uke-sync.
        if wants_week_plan_write(text):
            sync = self._handle_sync_week(text, user_id, Intent.SYNC_WEEK)
            if sync:
                self._remember(user_id, text, sync.text)
                return sync

        # Direkte enkeltøkt med eksplisitt idrett + varighet (f.eks.
        # «legg inn sykkel 60 min i morgen») må opprettes direkte – før
        # oppfølgings-håndtereren, som ellers fanger «legg inn …».
        single_reply = self._handle_single_workout(text, user_id)
        if single_reply:
            return single_reply

        write_reply = self._handle_intervals_write_followup(text, user_id)
        if write_reply:
            self._remember(user_id, text, write_reply.text)
            return write_reply

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
                reply.text += "\n\nNeste: logg økter/wellness i Intervals, eller sjekk files:write på Slack-appen."

        if wants_intervals_write(text) and self._sessions and self._intervals:
            event = extract_workout_from_text(
                llm_text, as_of=self._intervals.today(), user_hint=text
            )
            if event:
                self._sessions.set_pending(user_id, "intervals_single", {"event": event})
                reply.text += (
                    "\n\n---\n*Svar «ja» eller «legg den inn i Intervals»* når du vil opprette den i kalenderen."
                )
                extra = single_workout_preview_blocks(event)
                reply.blocks = (reply.blocks or []) + [{"type": "divider"}] + extra

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
            return compact_system_message(
                "Proaktiv test",
                "Coach-bot kan sende meldinger uten at du skriver først.",
                "Neste: prøv `briefing: morgen` eller `briefing: uke`.",
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
        if not is_commit_message(text):
            return None
        pending = self._sessions.get_pending(user_id)
        if not pending:
            return None
        return self._commit_pending(user_id, pending)

    def _commit_pending(self, user_id: str, pending: tuple[str, object]) -> CoachReply:
        if not self._intervals or not self._sessions:
            return CoachReply(text="Intervals-skriving er ikke tilgjengelig.")
        self._sessions.pop_pending(user_id)
        action_type, payload = pending
        if action_type == "intervals_single":
            event = (payload or {}).get("event") if isinstance(payload, dict) else None
            if not event:
                return CoachReply(text="Ventende økt mangler data – prøv på nytt.")
            try:
                self._intervals.create_event(event)
                d = (event.get("start_date_local") or "")[:10]
                name = event.get("name") or "Økt"
                return CoachReply(
                    text=f"Lagt inn i Intervals: {d} – {name}. Sjekk kalenderen i appen.",
                    blocks=single_workout_preview_blocks(event),
                )
            except Exception as e:
                return CoachReply(text=f"Kunne ikke skrive til Intervals: {e}")

        if action_type == "intervals_week":
            events = (payload or {}).get("events") or [] if isinstance(payload, dict) else []
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

        return CoachReply(text="Ukjent ventende handling.")

    def _handle_intervals_write_followup(self, text: str, user_id: str) -> CoachReply | None:
        if not self._sessions or not self._intervals:
            return None
        if wants_week_plan_write(text):
            return None
        if not wants_intervals_write(text) and not is_commit_message(text):
            return None

        pending = self._sessions.get_pending(user_id)
        if pending and is_commit_message(text):
            return self._commit_pending(user_id, pending)

        last = self._sessions.last_assistant_message(user_id)
        if not last:
            return CoachReply(
                text=(
                    "Beskriv økten først (f.eks. sykkel 60 min i morgen), eller skriv direkte: "
                    "`legg inn sykkel 60 min i morgen`."
                )
            )

        # Flerdagers plan fra chatten («legg inn hele planen» / «disse»):
        # parse alle dagene coachen nettopp foreslo, ikke bare én økt.
        if wants_full_plan(text):
            week_events = extract_week_plan_from_text(
                last, as_of=self._intervals.today()
            )
            if len(week_events) >= 2:
                self._sessions.set_pending(
                    user_id, "intervals_week", {"events": week_events}
                )
                if is_commit_message(text):
                    return self._commit_pending(
                        user_id, ("intervals_week", {"events": week_events})
                    )
                preview = "\n".join(
                    f"- {(e.get('start_date_local') or '')[:10]}: {e.get('name')}"
                    for e in week_events
                )
                reply = compact_system_message(
                    f"Plan ({len(week_events)} økter)",
                    preview,
                    "Neste: svar «ja» for å legge inn alle i Intervals.",
                )
                reply.blocks = (reply.blocks or []) + [
                    {"type": "divider"}
                ] + week_preview_blocks(week_events)
                return reply

        user_hint = text
        for msg in reversed(self._sessions.get_messages(user_id)):
            if msg["role"] == "user" and msg["content"].strip() != text.strip():
                user_hint = msg["content"] + "\n" + user_hint
                break

        event = extract_workout_from_text(
            last, as_of=self._intervals.today(), user_hint=user_hint
        )
        if not event:
            return CoachReply(
                text=(
                    "Fant ikke nok detaljer i forrige forslag. "
                    "Prøv: `legg inn sykkel 60 min i morgen`."
                )
            )

        self._sessions.set_pending(user_id, "intervals_single", {"event": event})
        if is_commit_message(text) or wants_intervals_write(text):
            return self._commit_pending(user_id, ("intervals_single", {"event": event}))

        return CoachReply(
            text=f"Forhåndsvisning: {event.get('name')} – svar *ja* for å legge inn.",
            blocks=single_workout_preview_blocks(event),
        )

    def _propose_workout_for_calendar(self, text: str, user_id: str) -> CoachReply:
        ctx = self._context.for_chat(text, intent=Intent.TOMORROW)
        llm_text = self._llm.complete_chat(
            ctx,
            text,
            intent=Intent.TOMORROW,
            history_messages=self._history_messages(user_id) or None,
        )
        today = self._intervals.today() if self._intervals else None
        event = None
        if self._intervals and today and self._sessions:
            event = extract_workout_from_text(llm_text, as_of=today, user_hint=text)
            if event:
                self._sessions.set_pending(user_id, "intervals_single", {"event": event})

        reply = self._wrap_llm_reply(llm_text, Intent.TOMORROW, "Plan for i morgen")
        reply.text += (
            "\n\n---\n*Svar «ja» eller «legg den inn i Intervals»* for å opprette økten i kalenderen."
        )
        if event:
            reply.blocks = (reply.blocks or []) + [{"type": "divider"}] + single_workout_preview_blocks(
                event
            )
        return reply

    def _reply_graphics_and_plan(self, text: str, user_id: str) -> CoachReply:
        """Deterministic answer when user asks for charts + Intervals plan (avoids LLM «kan ikke»)."""
        body = (
            "Grafer legges ved som bilder her (CTL/ATL og disiplinvolum). "
            "Ukeplan: `synk kalender` → forhåndsvisning → `ja`."
        )
        reply = compact_system_message(
            "Grafer og plan",
            body,
            "Neste: `ukestatus`, `synk kalender`, eller `legg inn sykkel 60 min i morgen`.",
        )
        if self._intervals:
            bundle = self._intervals.fetch_coach_bundle()
            from coach_bot.aggregates import build_training_snapshot

            snap = build_training_snapshot(bundle["activities"], tz=self._context._tz)
            reply = self._attach_charts(reply, bundle, snap.as_of)
            if not reply.image_paths:
                reply.text += "\n\nNeste: logg data i Intervals eller sjekk files:write på Slack-appen."
        sync = self._handle_sync_week(text, user_id, Intent.SYNC_WEEK)
        if sync:
            reply.text += f"\n\n{sync.text}"
            extra_blocks = sync.blocks or []
            reply.blocks = (reply.blocks or []) + [{"type": "divider"}] + extra_blocks
        return reply

    def _handle_sync_week(self, text: str, user_id: str, intent: Intent) -> CoachReply | None:
        if intent != Intent.SYNC_WEEK and not wants_week_plan_write(text):
            return None
        if not self._repo or not self._sessions:
            return None
        pending = self._sessions.get_pending(user_id)
        if pending and pending[0] == "intervals_single":
            return compact_system_message(
                "Ventende økt",
                "Du har et enkeltøktforslag som ikke er bekreftet ennå.",
                "Neste: skriv `ja` / `avbryt`, eller `nullstill`.",
            )
        week_ref = self._repo.active_training_week()
        logger.info("Week sync: active plan %s", week_ref.filename)
        events = events_for_active_week(self._repo)
        if not events:
            return compact_system_message(
                "Ingen ukeplan",
                f"Fant ingen økter å synce fra {week_ref.filename}. Rebuild deploy hvis du nettopp oppdaterte ukeplan i git.",
                "Neste: sjekk LOFOTEN-2027/ukeplan eller skriv en enkeltøkt.",
            )
        self._sessions.set_pending(user_id, "intervals_week", {"events": events})
        preview = "\n".join(
            f"- {(e.get('start_date_local') or '')[:10]}: {e.get('name')}" for e in events[:14]
        )
        reply = compact_system_message(
            f"Ukeplan ({len(events)} økter)",
            preview,
            "Neste: svar `ja` for å legge inn i Intervals.",
        )
        reply.blocks = (reply.blocks or []) + [{"type": "divider"}] + week_preview_blocks(events)
        return reply

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
