# Lofoten AI Coach

Slack **DM**-coach: leser **intervals.icu** og **LOFOTEN-2027**, svarer via OpenAI.

## Bruk

1. Sett opp [docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md) (Socket Mode).
2. `cp .env.example .env` – se [SETUP_ENV.md](SETUP_ENV.md).
3. `./scripts/start.sh`
4. Skriv til boten i Slack DM – f.eks. «status», «ukestatus», «hva i morgen?».

Valgfri morgenbriefing: `MORNING_BRIEFING_ENABLED=true` i `.env`.

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
