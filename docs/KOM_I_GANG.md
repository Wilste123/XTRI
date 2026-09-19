# Kom i gang – Lofoten 2027 + AI Coach (DM)

**Sist oppdatert:** 2026-09-19  
Én sjekkliste fra null til coach i Slack-DM.

---

## 1 – Intervals.icu

- [ ] Klokke/sykkel synker til [intervals.icu](https://intervals.icu)
- [ ] Athlete ID + API key i `coach-bot/.env`
- [ ] **Kalender:** gro plan for **denne + neste uke** som events
- [ ] (Anbefalt) Wellness når du kan

Detaljer: [INTERVALS_QUICKSTART.md](INTERVALS_QUICKSTART.md)

---

## 2 – OpenAI

- [ ] `OPENAI_API_KEY` i `coach-bot/.env`
- [ ] `COACH_MODEL=gpt-4o-mini`

---

## 3 – Slack (DM, Socket Mode)

- [ ] Følg [SLACK_SETUP.md](SLACK_SETUP.md) (Socket Mode, scopes, `message.im`)
- [ ] `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`, `ALLOWED_SLACK_USER_IDS`
- [ ] `REPO_ROOT` = absolutt sti til dette repoet
- [ ] `cp coach-bot/.env.example coach-bot/.env` – **commit aldri `.env`**
- [ ] `./coach-bot/scripts/start.sh`
- [ ] `curl http://localhost:3000/ready`
- [ ] Åpne DM med appen og skriv f.eks. «status»

Env-sjekkliste: [coach-bot/SETUP_ENV.md](../coach-bot/SETUP_ENV.md)

---

## 4 – Prosjektminne

- [ ] [LOFOTEN-2027/CURRENT_STATUS.md](../LOFOTEN-2027/CURRENT_STATUS.md)
- [ ] [08_UTSTYR.md](../LOFOTEN-2027/08_UTSTYR.md)

---

## 5 – Trening

- [ ] [baseline-uke.md](../LOFOTEN-2027/ukeplan/baseline-uke.md)
- [ ] [06_TESTRESULTATER.md](../LOFOTEN-2027/06_TESTRESULTATER.md) etter tester

---

## 6 – Ukentlig

[WEEKLY_RITUAL.md](WEEKLY_RITUAL.md) – DM «ukestatus», oppdater CURRENT_STATUS og Intervals.

---

## Nøkler lekket?

Hvis `.env` har vært i git: roter Slack-, Intervals- og OpenAI-nøkler. Se SETUP_ENV.
