# Current status (AI snapshot)

**Sist oppdatert:** 2026-09-19  
Oppdater etter baseline, ukestatus eller viktige beslutninger. Belastningstall hentes fra intervals.icu – ikke dupliser full økthistorikk her.

---

## LOFOTEN 2027 STATUS (kort)

| | |
|---|---|
| **Race** | Lofoten Triathlon Half Extreme, **20. aug 2027**, Svolvær |
| **Tid til start** | ~335 dager (fra prosjektstart 19. sep 2026) |
| **Fase** | **Base_0** – kontinuitet, kalibrering, baseline |
| **Hovedmål** | Fullføre med **god cutoff-margin** – sluttid følger av trening |

---

## Fase og fokus (neste 2–4 uker)

- **Fokus:** Baseline-testuke → deretter uke 01–04 i [ukeplan/](ukeplan/)
- **Svøm:** Teknikk og jevnhet før volum; basseng 2–3×/uke når mulig
- **Sykkel:** Moderat Z2, gradvis lengde – ikke «gammel juniorvolum» tidlig
- **Løp:** Forsiktig oppbygging; baseline tir, deretter lav risiko Z2
- **Styrke:** Vedlikehold 2×/uke (lett–moderat)

## Nåværende treningsnivå

| Parameter | Status | Kilde |
|-----------|--------|--------|
| Timer/uke (siste 4–8 uker) | **Ukjent** – for lav/ujevn historikk | Antakelse / Intervals når synket |
| Svøm | Svakste ben; teknikk-gap | [03_DAGENS_NIVA.md](03_DAGENS_NIVA.md) |
| Sykkel | Sterk historisk, nå **avkondisjonert** | Profil |
| Løp | Motivert; MSK må bygges | Profil |
| Vekt | ~89 kg | Profil |
| Skader / smerte | **Ikke logget** – oppdater ved behov | — |

## Aerob kapasitet og belastning

- Ingen ferdig baseline ennå → **ikke** konkludere FTP/pace/threshold
- Etter baseline: fyll [06_TESTRESULTATER.md](06_TESTRESULTATER.md) og oppdater denne seksjonen
- Coach henter aggregert belastning fra Intervals (28 d) når API er aktivt

## Risiko og flagg

| Flag | Status | Notat |
|------|--------|-------|
| Smerte / skade | Ukjent | Rapporter i DM til coach eller wellness |
| Livsstress / søvn | — | Logg i Intervals wellness når mulig |
| Volumsprang | **Høy risiko** | Prioriter skadefrihet over motivasjon |
| Reise / avvik | — | |

## Siste tester

Se [06_TESTRESULTATER.md](06_TESTRESULTATER.md) – **baseline ikke fullført ennå** (plan: tir løp / ons svøm / fre sykkel).

## Neste milepæler

- [ ] Fullfør baseline-testuke + resultater i 06
- [ ] 4 uker Base_0 logget i Intervals uten store hull
- [ ] Gro kalenderplan (denne + neste uke) som events i Intervals
- [ ] XTRI Coach V3 på Fly: DM + morgenbrief + ny-økt-varsler

## Største utfordring nå

**Kontinuitet etter lang pause** – bygge jevn uke uten å overdrive sykkel/løp før data og baseline sitter.

## Viktigste fokus neste 2–4 uker

1. Gjennomfør baseline og oppdater testresultater  
2. Hold 5–7 t/uke jevnt (Base_0), ikke hero-uker  
3. Svøm teknikk + to ukentlige svøm som minimum  
4. Fyll [08_UTSTYR.md](08_UTSTYR.md) (puls, watt, basseng)

---

## Coach / verktøy

| | Status |
|---|--------|
| GitHub | https://github.com/Wilste123/XTRI |
| Intervals athlete | `i303008` (API key i lokal `.env` / Fly secrets – ikke i git) |
| Slack coach | **V3** – Socket Mode DM + proaktive meldinger ([docs/COACH_V3_USER_CHECKLIST.md](../docs/COACH_V3_USER_CHECKLIST.md)) |
| Slack bruker (William) | `U0BSCE53YF2` |
| Repo på Mac | `/Users/william/XTRI` |

## Kort notat

Prosjekt og masterplan på plass. Coach-bot oppgradert til samtale + push (PR #2). Neste: Slack Socket Mode ferdig, Fly deploy, baseline i gang.
