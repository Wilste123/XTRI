# Lofoten AI Coach

Slack **DM**-coach: leser **intervals.icu** og **LOFOTEN-2027**, svarer via OpenAI.

## Bruk

1. Sett opp [docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md) (Socket Mode).
2. `.env` ligger i git – se [SETUP_ENV.md](SETUP_ENV.md) og sjekklisten [ENV_TODO.md](ENV_TODO.md).
3. `./scripts/start.sh`
4. Skriv til boten i Slack DM – f.eks. «status», «ukestatus», «hva i morgen?».

Morgenbriefing kl. 07:00 er på (`MORNING_BRIEFING_ENABLED=true`). Grafer, Atlas-på-Fly og web-søk krever ekstra nøkler — se ENV_TODO.

## Health

- `GET /health` – prosess lever
- `GET /ready` – repo + Intervals OK

## Tester

```bash
pip install -e ".[dev]"
pytest
```

## Arkitektur

[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
