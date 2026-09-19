# `.env` sjekkliste

```bash
cd coach-bot
cp .env.example .env
```

Fyll inn (ingen av disse i git):

| Variabel | Hvor finner du det |
|----------|-------------------|
| `SLACK_BOT_TOKEN` | Slack app → OAuth → Bot User OAuth Token |
| `SLACK_SIGNING_SECRET` | Slack app → Basic Information |
| `SLACK_APP_TOKEN` | Slack app → Socket Mode → App-Level Token (`connections:write`) |
| `ALLOWED_SLACK_USER_IDS` | Slack profil → Copy member ID (`U0BSCE53YF2` for William) |
| `SLACK_NOTIFY_USER_IDS` | Samme som over (proaktive meldinger) |
| `REPO_ROOT` | `/Users/william/XTRI` |
| `INTERVALS_ATHLETE_ID` | `i303008` (intervals.icu Settings) |
| `INTERVALS_API_KEY` | intervals.icu Settings → Developer |
| `OPENAI_API_KEY` | platform.openai.com |
| `COACH_MODEL` | `gpt-4o-mini` (standard) |

**Rask start (Mac):** etter `git pull`, fra `coach-bot/`:

```bash
./scripts/bootstrap-env.sh   # lager .env med Intervals + Slack user ID + V3 defaults
# Lim inn Slack-tokens og OPENAI_API_KEY i .env
./scripts/start.sh
```

Fly: `./scripts/fly-secrets-from-env.sh` når `.env` er komplett.

Valider at filen ikke er tracket:

```bash
git status   # skal ikke vise coach-bot/.env
```

## Feilsøking: `SSL: CERTIFICATE_VERIFY_FAILED` (Mac)

Typisk når Python er installert fra [python.org](https://www.python.org/downloads/) (f.eks. 3.13). Boten krasjer ved oppstart på `auth.test` mot Slack.

**A – Anbefalt (engangsfix på Mac):**

```bash
/Applications/Python\ 3.13/Install\ Certificates.command
```

(Juster versjonstall hvis du bruker 3.12 osv. – mappen ligger under `/Applications/Python 3.x/`.)

**B – Rask workaround (samme terminal som bot):**

```bash
cd coach-bot && source .venv/bin/activate
export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
python -m coach_bot.main
```

Nyere `scripts/start.sh` setter dette automatisk via `certifi` (transitiv avhengighet av `httpx`).

**Verifiser:**

```bash
python -c "import urllib.request; urllib.request.urlopen('https://slack.com'); print('SSL ok')"
```

## Feilsøking: `account_inactive` / `token is invalid`

SSL fungerer, men `auth.test` svarer `account_inactive`. Da er **`SLACK_BOT_TOKEN` ugyldig** for workspace (gammel token, app avinstallert, feil app, eller kopiert App Token i stedet for Bot Token).

1. [api.slack.com/apps](https://api.slack.com/apps) → velg **Lofoten Coach** (eller opprett app på nytt).
2. **OAuth & Permissions** → **Reinstall to Workspace** (eller Install App).
3. Kopier **Bot User OAuth Token** (`xoxb-...`) – ikke App-Level Token (`xapp-...`).
4. Lim inn i `coach-bot/.env` som `SLACK_BOT_TOKEN=...` (ingen anførselstegn, ingen mellomrom).
5. Hvis ny app: oppdater også `SLACK_SIGNING_SECRET` under Basic Information.
6. Start bot på nytt.

Test token (bytt ut token):

```bash
curl -s -H "Authorization: Bearer xoxb-DIN-TOKEN" https://slack.com/api/auth.test | python3 -m json.tool
```

Forventet: `"ok": true`. Ved `account_inactive` → reinstall og ny `xoxb-` token.
