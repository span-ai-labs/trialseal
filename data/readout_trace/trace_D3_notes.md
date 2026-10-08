# Readout trace, sample D3 (26 trials) — notes

Traced 2026-10-09. Data: `trace_D3.csv` (one row per trial, same order as `sample_D3.csv`). Input: `sample_D3.csv`.

## Read this first: the search was cut short

The general web-search allowance for the session ran out after about 30 queries, part-way through the tranche. Every trial was still worked, but from that point only by opening sources directly: the registry (API), Hong Kong exchange title lists and documents, SEC filing lists and exhibits, sponsor results announcements and pipeline documents, sponsor news pages, and PubMed. No conference-abstract search, trade-press search or Chinese-language search was possible for the later rows.

- **Searched by acronym, drug and sponsor on the open web before the cut:** COMPEL, INSPIRE, QL1706-302, the dabrafenib thyroid trial, HARMONi-6, POTOMAC, CAEL101-301, ETER100, IMvigor011, the Telix trial, evERA, FURVENT, REFRaME-O1, AK105-304, KEYNOTE-676, PACIFIC-9.
- **Traced from direct sources only (no open-web search):** NCT06548347 (linperlisib), NCT05673512 (IAH0968), NCT03391934 (CinnaGen cetuximab), NCT06313983 (Hemay022), NCT06998108 (BEBT-209), NCT06492941 (HB1801), NCT06079346 (STOP-PC), NCT06738251 (SHR-A2102), NCT05254171 (ASPIRE), NCT06591520 (HARMONi-GI1, found in Akeso's exchange title list).

The `no` rows in the second group meet the brief's minimum only in part. They are marked `low` where nothing but the registry and PubMed could be checked, `medium` where a recent sponsor document was read.

## Conventions used

Same as `trace_A_notes.md`. Points that mattered here:

- `first_disclosure_date` is the earliest source I could open and read. Three conference rows carry the date of the first dated coverage, not a confirmed session day.
- An Akeso or Sino Biopharm notice read from the Hong Kong exchange is `exchange_announcement`, as in tranche A, even where a wire copy exists. The HARMONi-6 notice was published at 07:45 Hong Kong time on 23 April 2025; the wire copy is datelined 22 April.
- A win at an interim analysis with the trial continuing is `met` (INSPIRE, HARMONi-6, ETER100, AK105-304, HARMONi-GI1).
- Two registry dates are month-only and were taken as the 15th (NCT04523272, 2025-06; NCT06591520, 2026-10).
- For quarterly documents: AstraZeneca Q1 2025, H1 2025, 9M 2025, FY 2025, Q1 2026 and H1 2026 results announcements (and the Q1 2025 and H1 2026 trial appendices), Roche Q1, half-year and Q3 2025 slides, Novartis Q1 to Q3 2025 reports and slides, Merck's Q2 2026 release, Akeso results from 2023 to 2025, and Hengrui, CSPC and SUNHO results were downloaded and searched. None moved a first-disclosure date earlier in this tranche.
- Summary statistics use the 12 `disclosed = yes` rows.

## Counts

| disclosed | n |
|---|---|
| yes | 12 |
| no | 14 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 9 |
| not_met | 2 |
| unclear | 1 |
| terminated_no_analysis | 2 |
| blank (not read out, or nothing found) | 12 |

Of the 12 disclosed trials: 9 met (75%), 2 not met (CAEL101-301, FURVENT), 1 unclear (COMPEL). The 14 `no` rows are 2 terminations without a primary analysis (Telix 177Lu-TLX591-002, REFRaME-O1), 2 with a sponsor statement that the readout is still to come (PACIFIC-9, expected by end of 2026; SHR-A2102, launch planned for 2028), and 10 where nothing was found.

## Lag from registry primary completion date to first disclosure

- All 12 disclosed: median **59 days**, range **-448 to +417 days**.
- 4 of 12 (33%) were disclosed *before* the registry date (median -347 days): INSPIRE, ETER100, AK105-304, HARMONi-GI1. All four are interim-analysis wins by Chinese sponsors whose registry date is an estimate.
- The 8 disclosed after the registry date: median **67.5 days**, range 36 to 417. Five fall between 36 and 68 days (POTOMAC 36, HARMONi-6 54, IMvigor011 64, CAEL101-301 67, evERA 68). The tail is two congress-first results with no topline release (the dabrafenib thyroid trial 273, COMPEL 313) and FURVENT (417, against a registry estimate the sponsor never updated).
- By registry date type: ACTUAL (n=7) median 67 days; ESTIMATED (n=5) median -306 days.

## Hazard ratios

- Numeric HR in the first disclosure: **5 of 12 (42%)**. Three were conference presentations (COMPEL, INSPIRE, the dabrafenib thyroid trial), one a regulator's approval notice (AK105-304) and one a topline press release for a failed trial (FURVENT).
- A numeric HR is public for 10 of 12. For the 5 where it came later, the delay from first disclosure was 26 to 179 days, median 116 (evERA 26, IMvigor011 63, ETER100 116, POTOMAC 162, HARMONi-6 179). Four of those five were shown at ESMO.
- No HR for 2: CAEL101-301 (the endpoint is a win ratio, so none applies) and HARMONi-GI1 (topline only, six weeks old).

## Which source came first

| first source | n |
|---|---|
| press release | 5 |
| exchange announcement (HKEX) | 3 |
| conference presentation | 3 |
| other (FDA approval notice) | 1 |

One of the five press releases came from a collaborator, not the sponsor (Natera for IMvigor011). Seven of the 12 disclosed trials have a lead sponsor that does not file with the SEC: Akeso (HARMONi-6, AK105-304, HARMONi-GI1), Chia Tai Tianqing / Sino Biopharm (ETER100), Qilu (INSPIRE) and Roche / Genentech (evERA, IMvigor011). For IMvigor011 the first disclosure nonetheless came from an SEC filer, Natera. None of the 12 was first disclosed as a line in a quarterly results or pipeline document.

## Rows to treat with care

- **NCT04765059 (COMPEL)**: `yes / unclear`. HR 0.43 (0.27-0.70) favours the experimental arm, but enrolment stopped at 98 patients, coverage calls the study underpowered for its primary endpoint, and neither the paper's abstract nor the registry gives a p-value or says the endpoint was met. Could be argued as `met`.
- **NCT04974398 (AK105-304, penpulimab)**: dated 2025-04-23 from the FDA approval notice, the first source that states the result. Two earlier hints do not state it: an sNDA submitted in December 2023 (disclosed 18 March 2024) and the Chinese approval of 16 March 2025. If a filing counts as disclosure, the date moves back by 13 months. No stand-alone topline notice exists in either company's exchange filings.
- **NCT04940052 (dabrafenib plus trametinib, thyroid)**: date is the first dated coverage (22 October 2025); the ESMO session was between 17 and 21 October and the abstract was probably online about a week before.
- **NCT04632758 (INSPIRE)**: date is WCLC 2023 coverage. Qilu is unlisted and a Chinese-language notice or an earlier Chinese congress may predate it; not searched. The interval in the HR cells is as reported at the congress; the paper calls it a 98.02% interval.
- **NCT04660344 (IMvigor011)**: first disclosure is Natera's release, not Roche's. If only sponsor statements count, the date is ESMO, 20 October 2025.
- **NCT04504825 (CAEL101-301)**: the topline pooled this trial with its sibling CAEL101-302; the trial-level figure appeared only in the registry on 2026-07-02. Endpoint is a win ratio.
- **NCT03528694 (POTOMAC)**: CI cells are blank because the first dated source with the HR gave none; the interval (0.50-0.93) is in the note.
- **NCT05306340 (evERA)**: HR cells hold the ITT value; the ESR1m co-primary is in the note.
- **NCT05254171 (ASPIRE)**: `no`, confidence low. An interim analysis was due in Q1 2025, just as Panbela defaulted on its debt and stopped filing with the SEC. A result or a quiet stop may exist outside EDGAR.
- **NCT05576272 (QL1706), NCT06548347 (linperlisib), NCT03391934 (CinnaGen), NCT06313983 (Hemay022), NCT06998108 (BEBT-209)**: `no` on the registry and PubMed alone (plus one web search for QL1706). Absence of evidence from a thin search; all five sponsors publish little in English and none is on the Hong Kong exchange.
- **NCT05673512 (IAH0968)**: last sponsor statement is from August 2025; SUNHO has been suspended from trading since April 2026 and has published no results since.
- **NCT03711032 (KEYNOTE-676)**: `no` rests on Merck's Q2 2026 release, its news page and pipeline page; the 10-Q and 10-K were not read. Registry estimate (2026-07-31) has just passed.
- **NCT06548347**: the registry's 2024-12-31 date belongs to a trial that had not started recruiting; it is not a credible phase 3 readout date.
- **NCT05870748 (REFRaME-O1)**: registry lists 600 as actual enrolment, which appears to be the planned number.
- **Designs for the exclusion review**: NCT03391934 is a biosimilar equivalence trial; NCT04504825 uses a win-ratio endpoint; NCT03711032 and NCT06548347 pair a response-rate primary with a time-to-event primary.
