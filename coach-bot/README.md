# Lofoten AI Coach (V1)

Slack-bot som leser **intervals.icu** (økter, wellness, kalenderplan) og **LOFOTEN-2027**-repoet, og svarer som coach via OpenAI.

## Kommandoer

| Slack | Beskrivelse |
|-------|-------------|
| `/status` | LOFOTEN 2027 STATUS |
| `/imorgen` | Plan i morgen + anbefaling |
| `/ukestatus` | Ukentlig oppsummering |

## Oppsett

1. Kopier `.env.example` → `.env` og fyll inn nøkler.
2. Les [docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md) for Slack-app og tunnel.
3. Legg ukentlig plan som **events** i intervals.icu.
4. Oppdater [LOFOTEN-2027/CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md).

## Kjøre lokalt

```bash
cd coach-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m coach_bot.main
```

Server på `http://localhost:3000` – Slack Request URL: `https://<tunnel>/slack/events`.

Health: `GET /health`

## Tester

```bash
pip install -e ".[dev]"
pytest
```

## Verifikasjon (manuell)

- [ ] `/status` returnerer norsk status uten timeout
- [ ] `/imorgen` viser events fra Intervals eller sier at plan mangler
- [ ] `/ukestatus` har seksjonene Gjennomført … Neste uke
- [ ] Ukjent Slack-bruker blokkeres når `ALLOWED_SLACK_USER_IDS` er satt

## Arkitektur

Se [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
