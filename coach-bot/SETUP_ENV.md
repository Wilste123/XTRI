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
| `ALLOWED_SLACK_USER_IDS` | Slack profil → Copy member ID |
| `REPO_ROOT` | `/Users/william/XTRI` |
| `INTERVALS_ATHLETE_ID` | intervals.icu Settings |
| `INTERVALS_API_KEY` | intervals.icu Settings → Developer |
| `OPENAI_API_KEY` | platform.openai.com |
| `COACH_MODEL` | `gpt-4o-mini` (standard) |

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
