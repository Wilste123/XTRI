# Miljøvariabler

**`coach-bot/.env` ligger i git** – William sitt test-oppsett. Etter `git pull` skal filen være der; rediger og commit når du roterer nøkler.

```bash
cd coach-bot
./scripts/start.sh
```

| Variabel | Hvor finner du det |
|----------|-------------------|
| `SLACK_BOT_TOKEN` | Slack app → OAuth |
| `SLACK_APP_TOKEN` | App-Level Token (`connections:write`) |
| `SLACK_SIGNING_SECRET` | Basic Information |
| `ALLOWED_SLACK_USER_IDS` | Slack member ID |
| `REPO_ROOT` | `/Users/william/XTRI` |
| `INTERVALS_*` | intervals.icu Settings |
| `OPENAI_API_KEY` | platform.openai.com |

Slack DM: [../docs/SLACK_SETUP.md](../docs/SLACK_SETUP.md)
