-- XTRI Coach – Supabase schema
-- Kjør i Supabase SQL Editor (Dashboard → SQL → New query → Run)
-- Bruk service_role key kun på server (coach-bot), aldri i frontend.

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- CURRENT STATUS (versjonerte snapshots – nyeste brukes av coach)
-- ---------------------------------------------------------------------------
create table if not exists public.coach_status_snapshots (
  id uuid primary key default gen_random_uuid(),
  content_md text not null,
  summary text,
  phase text,
  focus text,
  source text not null default 'manual'
    check (source in ('manual', 'import', 'coach', 'coach_weekly', 'coach_chat')),
  created_by text not null default 'system',
  created_at timestamptz not null default now()
);

create index if not exists coach_status_snapshots_created_at_idx
  on public.coach_status_snapshots (created_at desc);

comment on table public.coach_status_snapshots is
  'Lofoten CURRENT_STATUS-lignende markdown; nyeste rad er coach snapshot.';

-- ---------------------------------------------------------------------------
-- Slack-samtale (DM-historikk til LLM-kontekst)
-- ---------------------------------------------------------------------------
create table if not exists public.coach_messages (
  id uuid primary key default gen_random_uuid(),
  slack_user_id text not null,
  slack_channel_id text,
  thread_ts text,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  message_kind text
    check (message_kind is null or message_kind in (
      'chat', 'morning_brief', 'weekly_brief', 'post_workout', 'slash'
    )),
  created_at timestamptz not null default now()
);

create index if not exists coach_messages_user_created_idx
  on public.coach_messages (slack_user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Subjektive notater (V2 /logg)
-- ---------------------------------------------------------------------------
create table if not exists public.coach_notes (
  id uuid primary key default gen_random_uuid(),
  slack_user_id text not null,
  body text not null,
  tags text[] default '{}',
  created_at timestamptz not null default now()
);

create index if not exists coach_notes_user_created_idx
  on public.coach_notes (slack_user_id, created_at desc);

-- ---------------------------------------------------------------------------
-- Ny økt i Intervals – dedup (erstatter lokal JSON for Fly)
-- ---------------------------------------------------------------------------
create table if not exists public.coach_activity_dedup (
  intervals_activity_id text primary key,
  first_seen_at timestamptz not null default now(),
  notified_at timestamptz
);

-- ---------------------------------------------------------------------------
-- Bot state (bootstrap, DM cache, misc)
-- ---------------------------------------------------------------------------
create table if not exists public.coach_bot_state (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Row Level Security – kun service_role (coach-bot) skal skrive/lese
-- ---------------------------------------------------------------------------
alter table public.coach_status_snapshots enable row level security;
alter table public.coach_messages enable row level security;
alter table public.coach_notes enable row level security;
alter table public.coach_activity_dedup enable row level security;
alter table public.coach_bot_state enable row level security;

-- Ingen policies for anon/authenticated → kun service_role når du bruker
-- SUPABASE_SERVICE_ROLE_KEY på server.

-- ---------------------------------------------------------------------------
-- Valgfri: seed fra eksisterende tekst (lim inn CURRENT_STATUS etter deploy)
-- ---------------------------------------------------------------------------
-- insert into public.coach_status_snapshots (content_md, source, created_by, summary)
-- values ($$...markdown...$$, 'import', 'william', 'Initial import');

-- ---------------------------------------------------------------------------
-- Nyttig queries
-- ---------------------------------------------------------------------------
-- Siste status:
--   select content_md, created_at, source from coach_status_snapshots
--   order by created_at desc limit 1;
--
-- Siste meldinger:
--   select role, content, created_at from coach_messages
--   where slack_user_id = 'U0BSCE53YF2' order by created_at desc limit 20;
