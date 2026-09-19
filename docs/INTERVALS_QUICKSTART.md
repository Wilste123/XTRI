# Intervals.icu – rask start for coach

## Sync

1. Koble Garmin, Wahoo, Strava eller annen kilde under **Settings → Connections**.
2. Bekreft at nye økter dukker opp på aktivitetslisten.

## API (coach-bot)

1. **Settings** → noter **Athlete ID** (f.eks. `i123456`).
2. **Settings** → **Developer** → opprett **API key**.
3. I `coach-bot/.env`:
   ```
   INTERVALS_ATHLETE_ID=i123456
   INTERVALS_API_KEY=din_nøkkel
   ```
4. Del aldri nøkkelen i chat eller git.

## Kalenderplan (viktig for `/imorgen`)

Plan i Intervals er **source of truth** i V1.

1. Gå til **Calendar** i Intervals.
2. For hver treningsdag denne og neste uke: opprett **event/workout** med:
   - Tittel (f.eks. «Løp 45 min Z2»)
   - Type / sport
   - Varighet (minutter)
3. Gro oversikt er nok – detaljerte intervaller kan komme senere.

Coach-bot henter events via `GET .../events.json?oldest=&newest=`.

## Wellness (anbefalt)

Under **Wellness** daglig eller etter økt: søvn, HRV, vekt, kort notat. Tom wellness → bot sier at data mangler.
