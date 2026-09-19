# Lofoten AI Coach – arkitektur

## Data-eierskap

| System | Source of truth |
|--------|-----------------|
| intervals.icu | Økter, wellness (CTL/ATL), belastning, kalenderplan (events) |
| LOFOTEN-2027/ | Mål, masterplan, CURRENT_STATUS, ukeplan, beslutninger |
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
| `RepoReader` / `RepoWriter` | Les plan; `logg:` → CURRENT_STATUS |
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

## Senere

- Godkjent planendring → Intervals events
- Web-UI
