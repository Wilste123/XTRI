# Logg – beslutninger og notater

### NOTAT – 2026-09-20

**Notat:** `coach-bot/ENV_TODO.md` er sjekklisten for miljøvariabler etter merge av PR #5–#13. Tracked `.env` fikk tomme felter for GitHub, Tavily, ukebriefing og admin-secret (defaults = feature av). Kjernetokens var allerede satt.

**Hvorfor:** `main` på GitHub var oppdatert, men `.env` manglet nøkler for Atlas-synk, grafer (`files:write`), web-søk og Fly secrets.

---

### BESLUTNING – 2026-09-20

**Beslutning:** Langsiktig personlig hukommelse i `11_ATLAS.md` (Atlas). Coach lagrer varige fakta via verktøy + auto-læring fra DM; git/GitHub forblir source of truth (ikke Supabase for profil).

**Begrunnelse:** William skal oppleve at coachen blir smartere over tid (utstyr, preferanser, helse) uten duplikat database.

---

### BESLUTNING – 2026-09-20

**Beslutning:** Proaktiv morgenbriefing aktivert (`MORNING_BRIEFING_ENABLED=true`, kl. 07:00 Europe/Oslo). Ukebriefing forblir av.

**Begrunnelse:** OP/Slack DM skal gi daglig status uten manuell forespørsel; flagget stod på `false`, så APScheduler startet aldri.

---

### BESLUTNING – 2026-09-19

**Beslutning:** `coach-bot/.env` skal ligge i git (test/prototype). Agenter skal ikke fjerne eller gitignore den uten ny beslutning.

**Begrunnelse:** Unngå gjentatt manuell token-inntasting under utvikling; repo er privat test.

---

### BESLUTNING – 2026-09-19

**Beslutning:** Lofoten Triathlon Half Extreme 2027 er hovedmål.

**Begrunnelse:** Passer ønsket om ekstremt triatlonmål; mer realistisk enn full Extreme/Norseman som første steg. Langsiktig ambisjon (Norseman m.fl.) skal ikke styre volum nå.

---

### BESLUTNING – 2026-09-19

**Beslutning:** Ingen detaljert helårsplan før baseline + 6–8 uker logg.

**Begrunnelse:** Data mangler; prioritere kontinuitet og kalibrering (Base_0).

---

### BESLUTNING – 2026-09-19

**Beslutning:** Konkurransedato satt til 20. august 2027 (Arctic Triple listing) inntil offisiell 2027-manual.

**Begrunnelse:** Dokumentert på arrangørens 2027-eventside; verifiser ved påmelding.

---

### BESLUTNING – 2026-09-19

**Beslutning:** Coach-bot kan skrive planlagte økter til Intervals via API. Hele uke krever bekreftelse (`ja`); enkeltøkt kan legges inn direkte.

**Begrunnelse:** Kalender i Intervals er operativ plan; reduserer risiko for feil bulk-sync.
