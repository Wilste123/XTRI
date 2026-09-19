# Lofoten AI Coach (V3)

Slack-coach via **DM-samtale** og **proaktive meldinger** (morgen, ukentlig, ny økt i Intervals). Leser **intervals.icu** og **LOFOTEN-2027**, svarer via OpenAI.

## Bruk

| Kanal | Hva |
|-------|-----|
| DM til XTRI Coach | Fri chat («Hva bør jeg gjøre i morgen?») |
| Automatisk | Daglig morgenbrief, søndag ukestatus, melding ved ny aktivitet |

Valgfritt: slash med `SLACK_ENABLE_SLASH=true` (legacy).

## Oppsett

**Din sjekkliste:** [docs/COACH_V3_USER_CHECKLIST.md](../docs/COACH_V3_USER_CHECKLIST.md)

1. [SETUP_ENV.md](SETUP_ENV.md)
2. [docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md) – Socket Mode
3. [docs/DEPLOY.md](../docs/DEPLOY.md) – Fly.io
4. [docs/INTERVALS_QUICKSTART.md](../docs/INTERVALS_QUICKSTART.md)

## Kjøre lokalt

```bash
./scripts/start.sh
```

`SLACK_MODE=socket` (standard). Ingen tunnel.

Health: `GET /health` (default port **8080**)

Manuelle jobber:

```bash
python -m coach_bot.jobs morning
python -m coach_bot.jobs weekly
python -m coach_bot.jobs poll
```

## Tester

```bash
pip install -e ".[dev]"
pytest
```

## Verifikasjon

- [ ] DM → norsk coachesvar
- [ ] `jobs morning` → melding i Slack
- [ ] Ny økt i Intervals → oppfølging innen poll-intervall
