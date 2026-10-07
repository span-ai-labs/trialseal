# Readout trace, sample A (35 trials) — notes

Traced 2026-10-07. Data: `trace_A.csv` (one row per trial). Input: `sample_A.csv`.

## Conventions used

- `first_disclosure_date` is the earliest source I could open and read, not necessarily the true first. Conference dates carry about one day of uncertainty where only meeting coverage was available (flagged per row).
- `first_source_type` describes the document, not where I fetched it: a company announcement read from an SEC 6-K/8-K exhibit is `press_release`; `exchange_announcement` is used for notices that exist only as Hong Kong / Shanghai exchange filings.
- `disclosed = no` rows that have simply not read out have a blank `primary_result`. Two trials stopped with no primary analysis are `disclosed = no`, `primary_result = terminated_no_analysis`.
- HR columns come from `hr_source_url`. If that source gave no confidence interval the CI cells are blank and the CI is in `search_notes`.
- Lag is computed against the primary completion date in the input file. One month-only date (NCT05118776, 2025-06) was taken as the 15th.
- Summary statistics below use the 23 `disclosed = yes` rows only.

## Counts

| disclosed | n |
|---|---|
| yes | 23 |
| no | 11 |
| unclear | 1 |

| primary_result | n |
|---|---|
| met | 14 |
| not_met | 6 |
| stopped_futility | 3 |
| terminated_no_analysis | 2 |
| unclear | 1 |
| blank (not read out) | 9 |

Of the 23 disclosed trials: 14 met (61%), 6 not met, 3 stopped for futility.

## Lag from registry primary completion date to first disclosure

- All 23 disclosed: median **32 days**, range **-1,329 to +151 days**.
- 9 of 23 (39%) were disclosed *before* the registry primary completion date (median -395 days). These are interim-analysis readouts or records where the registry date tracks final data collection rather than the primary analysis.
- The 14 disclosed after the registry date: median **56.5 days**, range 12 to 151.
- By registry date type: ACTUAL (n=19) median 39 days; ESTIMATED (n=4) median -253.5 days.

## Hazard ratios

- Numeric HR in the first disclosure: **6 of 23 (26%)**. Three of those six were conference presentations, where the first disclosure is the data itself.
- A numeric HR is public for 18 of 23. Delay from first disclosure to first HR: median **75 days** across all 18; median **145 days** (range 57 to 985) for the 12 where the HR came later.
- No numeric HR public yet for 5: FIBROSARC, ASTER, SHR-A1811-III-306, ARGSARC, SERENA-4.
- Two HR dates are registry results postings because nothing earlier was found (ZEAL-1L, 366 days; RELATIVITY-123, 985 days).

## Which source came first

| first source | n |
|---|---|
| press release (incl. RNS / 6-K / 8-K exhibits) | 14 |
| exchange announcement (HKEX / SSE only) | 4 |
| conference presentation | 3 |
| registry record | 1 |
| other (trade press quoting sponsor) | 1 |

No trial was first disclosed by a journal paper or a regulator notice. Two of the 14 "press releases" were not stand-alone: the result was a sentence or paragraph inside a quarterly financial release (ZEAL-1L, FIBROSARC). The single `unclear` row (ASC40) is the same pattern.

## Sponsors that do not file with the US SEC

- **22 of 35 trials** (20 of 29 distinct sponsor groups) have a lead sponsor that is not an SEC registrant: Akeso (2), Chia Tai Tianqing / Sino Biopharm, SMT bio, AGO Research, TYK Medicines, Ascletis, Fosun Pharma, Henlius, Miracogen / Lepu, Sichuan Biokin, Roche, Philogen, Dizal, Hengrui (2), Polaris, Eleison, Hansoh, Daiichi Sankyo, Mabwell, JMT-Bio / CSPC.
- SEC registrants (13 trials): Novocure, GSK (2), BMS, Pfizer / Seagen (2), Immunome, Novartis (Anthos), AstraZeneca (3), Merck, BeOne.
- **12 of the 23 first disclosures** came from non-SEC sponsors, so an EDGAR-only monitor would miss about half. Eleison filed an S-1 in 2022 (seen in search summary only); I counted it as a non-filer.

## Patterns that make automatic detection hard

1. **Registry primary completion date is not the readout date.** Interim-analysis wins and futility stops were announced 6 to 44 months before the registry date (SKYSCRAPER-01, ECHELON-3, RELATIVITY-123, DESTINY-Gastric04, AK104-302, REMARK, CARES-336). Any model anchored on that date will see large negative lags.
2. **Stale or late registry records**, mostly Chinese and Korean sponsors: status "recruiting" or "not yet recruiting" years after a result was announced or the date passed (NCT06569420 was registered only weeks before its readout; NCT05990127, NCT05754853, NCT05429697 not updated since 2022-2023).
3. **Results buried in other documents**: quarterly results (ZEAL-1L, FIBROSARC, ASC40), a partner's reference-data PDF (TROPION-Lung12), regulatory-filing acceptance notices that do not name the protocol (both Hengrui trials), a registry "why stopped" field (ARGSARC), a trade-press quote (ASTER).
4. **Topline without numbers.** 17 of 23 first disclosures had no HR; the number arrived at a later conference, usually as a late-breaking abstract released on the day.
5. **Names change.** Acronyms assigned after registration (ANCHOR, REMARK, COMPASSION-15, CARES-336, PANKU-Esophagus01, ASTRUM-015); code names replaced by INNs (AL102 to varegacestat, DZD9008 to sunvozertinib, BL-B01D1 to iza-bren, SHR-A1811 to trastuzumab rezetecan, SAF-189s to foritinib); sponsors renamed or acquired (Ayala to Immunome, Anthos to Novartis, Seagen to Pfizer, BeiGene to BeOne, Tesaro to GSK).
6. **Sibling trials of the same drug** produce false positives: TY-9591 phase 2 ESAONA vs phase 3 FLETEO; JMT101 exon-20 trial vs JMT101-018; CARES-005 vs CARES-336; ASTRUM-015 phase 2 vs phase 3 stage.
7. **Conflicting or staggered outcomes.** ANCHOR was reported as "non-inferiority met" at ASCO 2025, but the 2026 paper says it failed the margin. SKYSCRAPER-01 disclosed one co-primary endpoint in 2022, leaked an interim HR for the other in 2023, and finished in 2024-2025.
8. **Language and access.** Three first disclosures are Chinese-only company notices (Sichuan Biokin, Hengrui twice), and the REMARK conference readout was found only through Chinese-language coverage. Business Wire, pfizer.com and Fierce return 403 to scripts; SEC full-text search rejects a generic user agent.
9. **Quiet terminations.** INTerpath-007 and TROPION-Lung12 ended with no press release; the registry shows "business reasons" or still "active, not recruiting".

## Rows to treat with care

- **NCT04854668 (ANCHOR)**: recorded `not_met` on the strength of the peer-reviewed paper; the first disclosure framed it as met.
- **NCT05118776 (ASC40)**: `unclear`. The company says only that it terminated the programme "after analysis".
- **NCT05171049 (ASTER)**: `stopped_futility` rests on one trade-press article quoting a Novartis spokesperson; the registry says "sponsor decision".
- **NCT05814354 (SHR-A1811-III-306)**: matched to the Hengrui filing notice by design, not by protocol number.
- **NCT05712694 (ARGSARC)**: registry is the only source; a Taiwan exchange notice may predate it.
- **NCT04294810 (SKYSCRAPER-01)**: HR columns hold the interim OS HR, not PFS.
- **NCT05320692 (CARES-336)**: `hr_first_public_date` is the date of the source I opened and is probably 2 to 4 weeks late.
- **NCT01954992 (glufosfamide)**: registry primary completion date has moved from 2026-06 (input file) to 2028-03.
- The "no" rows for NCT04547166, NCT05754853 and NCT06196736 rely on company statements seen in search summaries, not opened in full.
