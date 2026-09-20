# Lofoten AI Coach – arkitektur

## Data-eierskap

| System | Source of truth |
|--------|-----------------|
| intervals.icu | Økter, wellness (CTL/ATL), belastning, kalenderplan (events) |
| LOFOTEN-2027/ | Mål, masterplan, CURRENT_STATUS, ukeplan, beslutninger |
| LOFOTEN-2027/11_ATLAS.md | **Langsiktig personlig hukommelse** (utstyr, preferanser, helse, hendelser) |
| Slack DM | Brukergrensesnitt |
| coach-bot/data/sessions.db | Kort samtaleminne (lokal/sky) |

## Flyt

```mermaid
flowchart TB
  DM[Slack DM]
  Intent[intent.py]
  Insights[coach_insights.py]
  Ctx[ContextBuilder]
  LLM[OpenAI]
  Mem[session_store]
  DM --> Intent
  Intent --> Ctx
  Insights --> Ctx
  Mem --> LLM
  Ctx --> LLM
  LLM --> DM
  Log[repo_writer] --> Repo[LOFOTEN-2027]
```

Transport: **Slack Socket Mode**. Health HTTP på port 3000.

## Moduler (coach-bot)

| Modul | Rolle |
|-------|--------|
| `IntervalsClient` | Activities, events, wellness (+ cache) |
| `aggregates` | Volum, plan_vs_actual, wellness trends |
| `coach_insights` | **COACH_BRIEF** (deterministisk analyse) |
| `intent` | Klassifiser DM (status, uke, i morgen, logg, …) |
| `RepoReader` / `RepoWriter` | Les plan; `logg:` → CURRENT_STATUS (+ GitHub commit i sky) |
| `atlas` / `memory_learn` | Atlas R/W, auto-læring etter DM; verktøy `remember_fact` |
| `github_repo` | Valgfri GitHub sync (pull ved oppstart, commit ved skriv) |
| `ContextBuilder` | Intent-trimmet kontekst + COACH_BRIEF |
| `SessionStore` | SQLite, siste N turner |
| `CoachOrchestrator` | run_chat, morgen/uke-briefing |
| `proactive` | APScheduler morgen + søndag uke |

## DM-kommandoer (naturlig språk)

- Status, ukestatus, i morgen, race/spørsmål, smerte
- `logg: …` → append under «Kort notat» i CURRENT_STATUS
- `ping` → connectivity test (uten LLM)

## Deploy

Se [DEPLOY.md](DEPLOY.md) – Docker/Fly med `LOFOTEN-2027` baked in.

## V2 (implementert)

- Proaktiv DM + `briefing: test|morgen|uke`
- Block Kit, matplotlib-grafer, multi-turn chat (`SessionStore` → OpenAI messages)
- COACH_BRIEF ADVANCED (ACWR, adherence, konsistens)
- Intervals write: uke-preview + `ja`, enkeltøkt auto (`intervals_planner` + bulk upsert)
- `POST /admin/briefing` med `X-Admin-Secret`

## Persistens (SQLite vs Supabase vs Atlas)

- **Atlas (`11_ATLAS.md`):** Varige fakta om William – source of truth i git. Coach får relevant utdrag i hver DM; modellen kan kalle `remember_fact`; etter hver tur kjører **auto-læring** (kort LLM-ekstraksjon, dedupe). På Fly: sett `GITHUB_TOKEN` + `GITHUB_REPO` for pull/commit.
- **Nå:** [`session_store.py`](../coach-bot/src/coach_bot/session_store.py) (SQLite) – kort samtale + `pending_actions` for Intervals-bekreftelse.
- **Fly:** Ephemeral disk – `sessions.db` kan nullstilles ved redeploy (pending «ja» kan forsvinne). Valgfritt Fly volume eller restart etter deploy.
- **Fase 2 (valgfri):** Supabase kun som `SessionStore`-backend (samme API, tabeller `turns` + `pending_actions`). **Ikke** flytt Atlas, COACH_BRIEF, Intervals eller repo-hit dit. Intervals + git forblir source of truth.

## Senere

- Web-UI
