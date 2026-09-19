# Lofoten AI Coach (V1)

Slack-bot som leser **intervals.icu** (økter, wellness, kalenderplan) og **LOFOTEN-2027**-repoet, og svarer som coach via OpenAI.

## Kommandoer

| Slack | Beskrivelse |
|-------|-------------|
| `/status` | LOFOTEN 2027 STATUS |
| `/imorgen` | Plan i morgen + anbefaling |
| `/ukestatus` | Ukentlig oppsummering |

## Oppsett

Full sjekkliste: [docs/KOM_I_GANG.md](../docs/KOM_I_GANG.md)

1. [SETUP_ENV.md](SETUP_ENV.md) – `.env` fra `.env.example`
2. [docs/INTERVALS_QUICKSTART.md](../docs/INTERVALS_QUICKSTART.md) – sync + kalender
3. [docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md) – Slack-app og tunnel
4. [LOFOTEN-2027/CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md)
5. Verifiser: [VERIFY.md](VERIFY.md)

## Kjøre lokalt

```bash
./scripts/start.sh
```

Eller manuelt:

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
