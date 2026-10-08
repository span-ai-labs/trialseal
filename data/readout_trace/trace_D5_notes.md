# Readout trace, sample D5 (26 trials) — notes

Traced 2026-10-09. Data: `trace_D5.csv` (one row per trial, same order as `sample_D5.csv`). Input: `sample_D5.csv`.

## Conventions used

Same as `trace_A_notes.md` and `trace_C1_notes.md`. Points that mattered in this tranche:

- `first_disclosure_date` is the earliest source I could open and read. Where the sponsor's page was blocked (pfizer.com) the row carries the dated copy I did open and says so.
- Dual primary endpoints on the same comparison, where either suffices: one met is recorded as `met`, with the missed one named in `which_endpoint` (VERITAC-2, HARMONi).
- A win at an interim analysis with the trial continuing is `met`, not `stopped_efficacy` (KEYNOTE-A18, DUO-O, ELEVATE, CULMINATE-2, BRIGHT-3, HC-1119-04, ARTEMIS-008).
- `first_source_type = other` is used for a results slide deck (SKYSCRAPER-03) and a listing document (BRIGHT-3).
- Three disclosed rows have a month-only registry date, taken as the 15th (NCT03851640, NCT03769506, NCT03539744).
- Summary statistics use the 19 `disclosed = yes` rows only.

**Search limit.** The session's web-search allowance ran out about two thirds of the way through. From then on I worked only from documents fetched directly: sponsor results announcements and pipeline documents, the HKEX issuer filing index, SEC filing indexes, company news pages, the registry and PubMed. That found four first disclosures that had not surfaced by search (CS1003-305, CULMINATE-2, BRIGHT-3, ARTEMIS-008) but leaves the gaps listed per row; no general web search was run for MONO-OLA1, HE071-031, HB1901-008 or ARTEMIS-008.

## Counts

| disclosed | n |
|---|---|
| yes | 19 |
| no | 7 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 13 |
| not_met | 4 |
| stopped_futility | 2 |
| blank (not read out) | 7 |

Of the 19 disclosed trials: 13 met (68%), 4 not met, 2 stopped for futility. None of the 7 `no` rows is a termination; all are simply not read out as far as could be found.

## Lag from registry primary completion date to first disclosure

- All 19 disclosed: median **8 days**, range **-1,177 to +314 days**.
- 9 of 19 (47%) were disclosed *before* the registry date (median -337 days; HC-1119-04, CANOVA, DUO-O, KEYNOTE-A18, VIKTORIA-1, CAPItello-280, POPLAR-NF2, ARTEMIS-008, BRIGHT-3). These are interim-analysis wins, futility stops, or stale registry records.
- The 10 disclosed after the registry date: median **53 days**, range 8 to 314. Seven fall between 8 and 62 days; the tail is ELEVATE (141), ASP-1929-301 (166) and KN026-003 (314), all against estimated registry dates.
- By registry date type: ACTUAL (n=10) median 27.5 days; ESTIMATED (n=9) median -82 days.

## Hazard ratios

- Numeric HR in the first disclosure: **5 of 19 (26%)** — HARMONi, VIKTORIA-1, CANOVA, ASP-1929-301 (press releases), ELEVATE (conference).
- A numeric HR is public for 13 of 19. Delay from first disclosure to first HR: median **59 days** across all 13; median **89.5 days** (range 37 to 347) for the 8 where the HR came later.
- No numeric HR found for 6: CS1003-305, KN026-003, POPLAR-NF2, BRIGHT-3 (a 47% risk reduction is stated, with no HR or CI), CAPItello-280, ARTEMIS-008.

## Which source came first

| first source | n |
|---|---|
| press release | 12 |
| exchange announcement (HKEX) | 4 |
| other (results slide deck; listing document) | 2 |
| conference | 1 |

Four of the 19 were not stand-alone announcements: SKYSCRAPER-03 is one line on a slide of Roche's HY 2025 results deck; CULMINATE-2 is one sentence in a filing-acceptance notice; BRIGHT-3 is one sentence in a listing document; POPLAR-NF2 is a paragraph in a quarterly results release. Ten of the 19 first disclosures came from sponsors that do not file with the SEC (ITM, Roche, Betta, CStone, Sino Biopharm, CSPC/JMT-Bio, Hinova, Rakuten Medical, Xuanzhu, Hansoh); the other nine are SEC registrants (Pfizer twice, Merck, AstraZeneca twice, Summit, Recursion, Celcuity, AbbVie).

## Rows to treat with care

- **NCT05257395 (BRIGHT-3, XZP-3287-3002)**: `met` rests on "positive results in an interim analysis" in Xuanzhu's listing document of 17 Sep 2025; an earlier application proof probably says the same and would move the date by months. No HR.
- **NCT05130866 (POPLAR-NF2)**: `stopped_futility` on an uncontrolled phase 2 dose-cohort look in a phase 2/3 design with 25 patients; `terminated_no_analysis` with `disclosed = no` is arguable.
- **NCT03769506 (ASP-1929-301)**: `not_met` is my reading of a release that reports PFS HR 0.98 and OS HR 0.83 without CIs and never says whether the primary endpoints were met. The ASCO abstract was blocked and is probably about a week earlier.
- **NCT05341583 (ELEVATE)**: date read from data embedded in a script-rendered ESMO page; the session day within 17-21 Oct 2025 is not confirmed, and Shenzhen exchange notices were not searched.
- **NCT05365178 (CULMINATE-2)**: the first-disclosure notice prints a different registry number (NCT04523272) beside the matching protocol number.
- **NCT06396065 (HARMONi)** and **NCT05654623 (VERITAC-2)**: `met` on one of two dual primaries; the other was missed. HARMONi could be argued as `mixed`.
- **NCT05501886 (VIKTORIA-1)**: the row is the wild-type cohort; the mutant-cohort readout of about May 2026 was seen only in a search summary.
- **NCT04165317 (CREST)**: the 10 Jan 2025 release was not opened; date from later coverage.
- **NCT03851640 (HC-1119-04)**: the exchange notice was not opened, only the company news page; `hr_first_public_date` is the page I opened (8 Jun 2023), a few days after the poster.
- **NCT04221945 (KEYNOTE-A18)** and **NCT03737643 (DUO-O)**: rows describe the 2023 interim PFS readout; later OS disclosures were not traced.
- **NCT04884360 (MONO-OLA1)**: `no`, confidence low. Guided to H2 2026 as of July 2026; the last ten weeks of AstraZeneca releases could not be listed.
- **NCT05751850 (HR070803-301)**: `no`, confidence low. Shanghai exchange notices before May 2025 and conference abstracts were not checked.
- **Other "no" rows (NCT03721744, NCT05201404, NCT05235516, NCT05717764, NCT06929325)**: absence of evidence from sponsor filings, results documents and PubMed, not proof.
