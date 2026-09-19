# Kom i gang – Lofoten 2027 + AI Coach

**Sist oppdatert:** 2026-09-19  
Bruk denne som hoved-sjekkliste. Kryss av når du er ferdig (rediger filen eller husk mentalt).

**Git:** `main` synket med [github.com/Wilste123/XTRI](https://github.com/Wilste123/XTRI).

---

## Fase 0 – Prosjekt sikret

- [x] Remote `origin` og push (ferdig)
- [x] `.gitignore` dekker `.env` og `.venv`

---

## Fase 1 – Intervals.icu

- [ ] Klokke/sykkel/Strava synker til [intervals.icu](https://intervals.icu)
- [ ] Athlete ID notert (Settings, f.eks. `i123456`)
- [ ] API key opprettet (Settings → Developer)
- [ ] `coach-bot/.env`: `INTERVALS_ATHLETE_ID` + `INTERVALS_API_KEY`
- [ ] **Kalender:** gro plan for **denne + neste uke** som events (tittel, type, varighet)
- [ ] (Anbefalt) Wellness: søvn/HRV/vekt når du kan

---

## Fase 2 – OpenAI

- [ ] API-nøkkel fra [platform.openai.com](https://platform.openai.com)
- [ ] `OPENAI_API_KEY` i `coach-bot/.env`
- [ ] `COACH_MODEL=gpt-4o-mini` (standard)

---

## Fase 3 – Slack + bot

Se også [SLACK_SETUP.md](SLACK_SETUP.md).

- [ ] Slack-app opprettet (`chat:write`, `commands`)
- [ ] `SLACK_BOT_TOKEN` + `SLACK_SIGNING_SECRET` i `.env`
- [ ] Slash: `/status`, `/imorgen`, `/ukestatus` → `https://<tunnel>/slack/events`
- [ ] `ALLOWED_SLACK_USER_IDS` = din Slack member ID
- [ ] `REPO_ROOT=/Users/william/XTRI` i `.env`
- [ ] Start bot: `./coach-bot/scripts/start.sh` (eller se script)
- [ ] Tunnel: `cloudflared tunnel --url http://localhost:3000`
- [ ] `curl http://localhost:3000/health` → ok
- [ ] Test `/status` i Slack (15–30 s)

---

## Fase 4 – Prosjektminne

- [ ] [CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md) fylt ut
- [ ] [08_UTSTYR.md](../LOFOTEN-2027/08_UTSTYR.md) fylt ut

---

## Fase 5 – Trening

- [ ] Les [baseline-uke.md](../LOFOTEN-2027/ukeplan/baseline-uke.md) og start når klar
- [ ] Testdager gjennomført (tir/ons/fre)
- [ ] [06_TESTRESULTATER.md](../LOFOTEN-2027/06_TESTRESULTATER.md) utfylt
- [ ] Oppdater CURRENT_STATUS + 03 etter baseline
- [ ] Uke 01–04 + speil gro plan i Intervals

---

## Fase 6 – Ukentlig ritual

Se [WEEKLY_RITUAL.md](WEEKLY_RITUAL.md).

- [ ] Søndag: `/ukestatus` → oppdater CURRENT_STATUS + Intervals neste uke

---

## Minimum viable uke 1

1. Intervals synker + events i kalender  
2. `.env` + bot + tunnel + én `/status`  
3. CURRENT_STATUS oppdatert  
4. Baseline-uke startet  
