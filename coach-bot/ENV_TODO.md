# .env-todoliste – få alle nye coach-features til å virke

**Sist sjekket:** 2026-09-20  
**GitHub `main`:** `33a3c85` — Merge PR #14 (ENV_TODO + utvidet `.env`). **Oppdatert.**  
**Denne Macen / lokal clone:** kjør `git pull origin main` før du fyller nøkler. Snapshot-miljøer kan ligge titalls commits bak.

Kjernedata (Slack, Intervals, OpenAI) ligger allerede i `coach-bot/.env`. Det som **mangler** er nøkler og Slack-scopes som ble lagt til etter PR #5–#13. Tomme felt i `.env` gir trygge defaults (feature av), ikke krasj.

Etter `git pull`: åpne denne filen + `coach-bot/.env`. Kryss av mens du går.

---

## 0 – Kode først (påkrevd)

- [ ] `git pull origin main` i XTRI-repoet
- [ ] Stopp gammel bot (Ctrl+C) og start på nytt: `cd coach-bot && ./scripts/start.sh`
- [ ] `curl http://localhost:3000/ready` → `"ok": true`
- [ ] DM `ping` i Slack → Pong

Uten dette kjører du V1/tidlig V2 og tror nye features «ikke virker».

---

## 1 – Allerede satt (ikke gjør om med mindre nøkler er rottert)

| Variabel | Status på `main` | Feature |
|----------|------------------|---------|
| `SLACK_BOT_TOKEN` | satt | DM |
| `SLACK_APP_TOKEN` | satt | Socket Mode |
| `SLACK_SIGNING_SECRET` | satt | Slack-signatur |
| `ALLOWED_SLACK_USER_IDS` | `U0BSCE53YF2` | bare William får svar + briefing |
| `REPO_ROOT` | `/Users/william/XTRI` | leser `LOFOTEN-2027/` |
| `INTERVALS_ATHLETE_ID` / `INTERVALS_API_KEY` | satt | økter, wellness, kalenderskriving |
| `OPENAI_API_KEY` / `COACH_MODEL` | satt (`gpt-4o-mini`) | chat, tool-calling, Atlas-læring |
| `TZ` | `Europe/Oslo` | cron |
| `MORNING_BRIEFING_ENABLED` | `true` | proaktiv DM kl. 07:00 |
| `MORNING_BRIEFING_HOUR` / `MINUTE` | `7` / `0` | |

---

## 2 – Må gjøres av deg (nye features)

### A. Slack-grafer (PR #5 / V2)

Uten `files:write` svarer boten, men **laster ikke opp CTL/ATL-grafer**.

- [ ] Slack API → appen → **OAuth & Permissions** → Bot Token Scope `files:write`
- [ ] **Reinstall to Workspace**
- [ ] Kopier **nytt** `SLACK_BOT_TOKEN` inn i `.env` (og Fly secrets hvis du deployer)
- [ ] Restart bot
- [ ] DM `briefing: uke` eller «vis grafer» — forvent PNG i DM

Valgfritt: `reactions:write` for ⏳ mens coach tenker.

### B. Atlas + GitHub-synk (PR #13) — påkrevd på Fly, anbefalt lokalt

Uten token lærer coachen lokalt til `11_ATLAS.md`, men **committer ikke** til GitHub. På Fly er disk ephemeral: hukommelse forsvinner ved restart.

- [ ] GitHub → Settings → Developer settings → **Personal access token** (fine-grained mot `wilste123/xtri`, eller classic)
  - Scope: **Contents: Read and write** (Contents API)
- [ ] Sett i `.env` **eller** `gh auth login` på Mac (da henter `./scripts/start.sh` token automatisk):
  ```
  GITHUB_TOKEN=ghp_...   # eller github_pat_... (kan stå tom lokalt hvis gh er innlogget)
  GITHUB_REPO=Wilste123/XTRI
  GITHUB_BRANCH=main
  MEMORY_AUTO_LEARN=true
  ATLAS_CONTEXT_MAX_CHARS=2500
  ```
- [ ] Restart bot. I logg: GitHub-synk enabled (ikke stille skip)
- [ ] DM noe varig («jeg sykler Canyon Aeroad») → sjekk `LOFOTEN-2027/11_ATLAS.md` og at commit lander på `main`

### C. Ferske fakta / web-søk (PR #11) — valgfritt men nødvendig for «søk nettet»

Uten nøkkel faller coachen tilbake til intern kunnskapsbase (fungerer, men ikke live).

- [ ] Konto på [tavily.com](https://tavily.com) → API key
- [ ] `TAVILY_API_KEY=tvly-...` i `.env` (og Fly)
- [ ] Restart. Test i DM: spør om noe ferskt (f.eks. årets Lofoten-dato / vær) og sjekk at svaret siterer kilder, ikke «web-søk er ikke konfigurert»

### D. Admin HTTP-briefing — valgfritt

- [ ] Generer en hemmelig streng, sett `ADMIN_BRIEFING_SECRET=...`
- [ ] Test:
  ```bash
  curl -X POST "http://localhost:3000/admin/briefing?type=test" \
    -H "X-Admin-Secret: din-streng"
  ```
Tom verdi = endepunktet er av (trygt).

### E. Søndags-ukebriefing — av som default

Morgenbriefing er på. Ukebriefing er **av** (beslutning 2026-09-20).

- [ ] Bare hvis du vil ha den: `WEEKLY_BRIEFING_ENABLED=true` (søndag 18:00 Oslo som default)

### F. Fly.io always-on (proaktiv 07:00 + Atlas i sky)

Dockerfile kopierer **ikke** `.env`. Secrets må settes eksplisitt.

- [ ] `fly launch --config coach-bot/fly.toml --no-deploy` (første gang)
- [ ] Sett secrets (se [SETUP_ENV.md](SETUP_ENV.md)), minst:
  - alle Slack + Intervals + OpenAI
  - `MORNING_BRIEFING_ENABLED=true`
  - `GITHUB_TOKEN` + `GITHUB_REPO=Wilste123/XTRI` + `MEMORY_AUTO_LEARN=true`
  - `TAVILY_API_KEY` hvis du vil ha web-søk
  - `files:write`-oppdatert bot token
  - **Ikke** importer `REPO_ROOT` fra `.env` (Mac-sti ødelegger ukeplan på Fly). `REPO_ROOT=/app` kommer fra `fly.toml` + Dockerfile.
- [ ] Eksempel: `grep -v '^REPO_ROOT=' coach-bot/.env | fly secrets import -a lofoten-coach`
- [ ] `cd coach-bot && fly deploy -a lofoten-coach --dockerfile Dockerfile --build-context ..`
- [ ] Sjekk start-logg: `Morning briefing at 07:00 Europe/Oslo`
- [ ] Ikke kjør lokal `start.sh` **og** Fly samtidig (to Socket Mode-klienter = duplikatsvar)

---

## 3 – Defaults du kan la stå

Disse ligger nå i `.env` / `.env.example`. Endre bare ved behov.

| Variabel | Default | Betydning |
|----------|---------|-----------|
| `WEEKLY_BRIEFING_ENABLED` | `false` | søndags-ukestatus |
| `WEEKLY_BRIEFING_WEEKDAY` | `6` | søndag (APScheduler: 0=man) |
| `WEEKLY_BRIEFING_HOUR` / `MINUTE` | `18` / `0` | |
| `COACH_WEEK_OVERRIDE` | tom | tving ukeplan-fil, ellers auto |
| `SESSION_MAX_TURNS` | `10` | kort DM-minne i SQLite |
| `INTERVALS_MAX_BULK_EVENTS` | `14` | tak på uke-synk |
| `PORT` | `3000` | `/health` `/ready` |
| `MEMORY_AUTO_LEARN` | `true` | Atlas etter hver DM |
| `ATLAS_CONTEXT_MAX_CHARS` | `2500` | hvor mye Atlas i prompt |

---

## 4 – Hva hver nøkkel skrur på

| Feature (merge på `main`) | Virker uten ekstra nøkkel? | Du må |
|---------------------------|----------------------------|-------|
| Slack DM + ping + status | ja (tokens satt) | pull + restart |
| Tool-calling, kunnskap, kalender-manipulasjon (`ja`/flytt/slett/last) | ja (OpenAI + Intervals) | live-test i DM |
| Intervals-skriving (ukeplan / enkeltøkt) | ja | DM «legg inn …» → `ja` |
| Proaktiv morgen kl. 07 | ja i `.env`; **nei på Fly** uten secret | always-on prosess |
| Grafer i Slack | nei | `files:write` + reinstall |
| Atlas auto-lær lokalt | ja (`MEMORY_AUTO_LEARN`) | |
| Atlas overlever Fly-restart / deles via git | nei | `GITHUB_TOKEN` + `GITHUB_REPO` |
| Live web-søk | nei | `TAVILY_API_KEY` |
| `POST /admin/briefing` | nei | `ADMIN_BRIEFING_SECRET` |
| Søndags-ukebriefing | av | `WEEKLY_BRIEFING_ENABLED=true` |

---

## 5 – Etter nøkler: live-sjekk

Se [VERIFY.md](VERIFY.md). Minimum:

1. `ping`
2. `briefing: morgen`
3. `briefing: uke` (graf)
4. «legg inn løp 45 min i morgen» → preview → `ja` (sjekk intervals.icu)
5. Fortell et varig faktum → `11_ATLAS.md` oppdatert
6. (hvis Tavily) spør om noe som krever ferske kilder

---

## 6 – Ikke gjør

- Ikke fjern `coach-bot/.env` fra git uten ny beslutning i `10_LOGG.md`.
- Ikke commit Tavily/GitHub-PAT i chat eller screenshots.
- `docs/KOM_I_GANG.md` sier «commit aldri `.env`» — det er utdatert; prototype-beslutningen er at filen **skal** ligge i git.
