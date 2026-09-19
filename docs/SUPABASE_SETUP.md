# Supabase – XTRI Coach database

Coach bruker Supabase (Postgres) for:

- **CURRENT STATUS** – versjonerte snapshots (`coach_status_snapshots`)
- **Slack-historikk** – DM til LLM-kontekst (`coach_messages`)
- **Ny økt dedup** – erstatter JSON på Fly (`coach_activity_dedup`)
- **Notater** – fremtidig `/logg` (`coach_notes`)

Intervals.icu forblir source of truth for **økter**. Git/repo er fortsatt arkiv; Supabase er **levende coach-minne**.

## 1. Opprett prosjekt

1. [supabase.com/dashboard](https://supabase.com/dashboard) → **New project**
2. Noter **Project URL** og **service_role** key (Settings → API → `service_role` – **kun server**, aldri i frontend)

## 2. Kjør SQL

1. Dashboard → **SQL Editor** → New query
2. Lim inn hele filen [coach-bot/supabase/schema.sql](../coach-bot/supabase/schema.sql)
3. **Run**

## 3. Env / Fly secrets

```bash
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

Lokal: `coach-bot/.env`  
Fly: `fly secrets set SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=...`

Uten disse kjører boten **fil-modus** (repo + lokal JSON).

## 4. Første sync av CURRENT_STATUS

Etter SQL + env:

```bash
cd coach-bot
source .venv/bin/activate
python -m coach_bot.jobs sync-status
```

Ved **første oppstart** importeres også `CURRENT_STATUS.md` automatisk hvis tabellen er tom.

## 5. Nyeste status i SQL

```sql
select content_md, source, created_at
from coach_status_snapshots
order by created_at desc
limit 1;
```

Ukentlig brief lagrer ny snapshot (`source = coach_weekly`).

## 6. Sikkerhet

- RLS er på; ingen policies for anon → kun **service_role** fra coach-bot
- Roter service_role hvis den lekker
- Ikke commit nøkler til git
