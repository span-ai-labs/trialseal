# Readout trace, sample B (35 trials) — notes

Traced 2026-10-07. Data: `trace_B.csv` (one row per trial, same order as `sample_B.csv`).
"First" means the earliest source I could open and verify, not necessarily the true first.

## Counts

| disclosed | n |
|---|---|
| yes | 22 |
| no (nothing public found, trial plausibly not read out) | 10 |
| unclear (registry record stale, status UNKNOWN, completion date passed, nothing found either way) | 3 |

Primary result, among the 22 disclosed (left blank for the other 13):

| primary_result | n | trials |
|---|---|---|
| met | 13 | CheckMate 227 (first-disclosed primary), POLARGO, DeLLphi-304, KEYNOTE-B96, XZP-3621, MajesTEC-3, lidERA, PEAK, KEYNOTE-522 (pCR), LOTIS-5, CELESTIMO, SHR-A1811-307, HS-20093 |
| not_met | 6 | RELATIVITY-098, RATIONALE-311, TROPiCS-04, TiNivo-2, CAPItello-290, XPORT-EC-042 |
| mixed | 1 | NILE (one dual primary met, one missed) |
| stopped_futility | 1 | OBI-822 GLORIA |
| terminated_no_analysis | 1 | VIALE-T |

## Lag from registry primary completion date (PCD) to first disclosure

- All 22 disclosed: median **61.5 days**, range **-2454 to +460**.
- 7 of 22 were disclosed **before** the registry PCD (-34 to -2454 days). These are interim-analysis readouts, or trials whose registry PCD tracks final follow-up rather than the primary analysis (CheckMate 227, KEYNOTE-522, CAPItello-290, TiNivo-2, TROPiCS-04, OBI-822, HS-20093).
- The 15 disclosed on or after PCD: median **72 days**, range **41 to 460**. Eleven of the 15 fall between 41 and 106 days; the long tail is the two registry-only results (254, 460), a congress-first result (197) and the listing-document case (133).
- Restricting to ACTUAL PCDs (18 trials): median 66.5 days.

## Hazard ratios

- A numeric hazard ratio was in the first disclosure for **7 of 22 (32%)**: POLARGO, RATIONALE-311, XZP-3621, VIALE-T (descriptive only), PEAK, LOTIS-5 (no CI), XPORT-EC-042.
- For 9 trials the hazard ratio for the disclosed endpoint came later: median **57 days** after first disclosure, range **22 to 191** (lidERA 22, DeLLphi-304 52, MajesTEC-3 54, TiNivo-2 57, CheckMate 227 70, CAPItello-290 87, RELATIVITY-098 110, KEYNOTE-B96 156, TROPiCS-04 191). Across all 16 trials with a hazard ratio for the disclosed endpoint, the median delay is 37 days.
- KEYNOTE-522 is kept out of those figures: its first disclosure was pCR, which has no hazard ratio. The CSV carries the first public EFS hazard ratio (62 days later) and says so in the notes.
- No hazard ratio is public yet for 5: OBI-822 (stopped, no numbers released), NILE, CELESTIMO, SHR-A1811-307, HS-20093 (all 2026 toplines awaiting a congress).

## Which source came first

| first_source_type | n |
|---|---|
| press_release | 15 |
| exchange_announcement | 4 (HKEX listing document, HKEX voluntary announcement, Taiwan material-information notice, AstraZeneca quarterly results announcement) |
| registry | 2 (RATIONALE-311, VIALE-T — both negative or terminated, no press release) |
| conference | 1 (POLARGO) |

No trial in this sample was first disclosed by a journal paper or a regulator notice.

## Sponsors outside US SEC reporting

By my reading, **15 of the 27 distinct lead sponsors (20 of 35 trials)** do not file periodic reports with the SEC: Roche (4 trials), Henlius (2), CSPC (2), Johnpro, Xuanzhu, Fosun, OBI Pharma, EpicentRx (private), AVEO (owned by LG Chem since 2023), Akeso, Shanghai Pharma, Hengrui, Hansoh, Bio-Thera, Chia Tai Tianqing. This classification is from general knowledge of where each company is listed; I did not check EDGAR sponsor by sponsor.

Of the 22 disclosed trials, 8 belong to these non-SEC sponsors, so an EDGAR-only monitor would have missed them. Of the 13 undisclosed or unclear trials, 12 also sit with non-SEC sponsors (the exception is MANDARIN, Boston Scientific).

## Patterns that make automatic detection hard

1. **Registry PCD is a poor anchor.** A third of disclosed trials read out before their registry PCD, two by more than six years. TiNivo-2 lists an ACTUAL PCD 18 months after its topline; CAPItello-290 still shows an ESTIMATED PCD 21 months after it failed.
2. **Negative and terminated trials surface quietly.** RATIONALE-311 and VIALE-T have no press release, abstract or paper; the only disclosure is the ClinicalTrials.gov results posting, 15 and 8 months after PCD.
3. **Results buried in larger documents.** NILE first appears as one row of a pipeline table in a 43-page quarterly results announcement, with no stand-alone release. XZP-3621's phase 3 hazard ratio first appears (as far as I could verify) inside a Hong Kong IPO listing document.
4. **Topline releases carry no numbers.** 15 of 22 first disclosures say only "met" or "did not meet"; the hazard ratio follows at a congress weeks to months later, once at a regional congress (ESMO Asia).
5. **Names in the registry do not match names in the news.** Trial acronyms missing from the registry acronym field, and sometimes from the whole record (lidERA, TiNivo-2, KEYNOTE-B96, DIAMOND-2, ARTEMIS-011, COMPASSION-22, GLORIA); drug codes replaced by INNs (XZP-3621 → dirozalkib, HS-20093 → risvutatug rezetecan, SHR-A1811 → trastuzumab rezetecan, RRx-001 → nibrozetone); sponsor renamed (BeiGene → BeOne).
6. **Chinese-language and Asian-exchange disclosure.** SHR-A1811-307 was found only in Chinese business press; OBI-822's notice is a Taiwanese material-information filing whose English text is password-protected. Sister trials of the same drug (benmelstobart + anlotinib in NSCLC) return positive toplines that are easy to mis-attribute to the SCLC trial in this sample.
7. **Stale registry records.** Five records have status UNKNOWN and have not been updated for two to five years; for three of them I could not tell whether the trial ran to completion.
8. **Several primaries, staggered.** CheckMate 227, KEYNOTE-522, KEYNOTE-B96 and NILE have more than one primary comparison; "first primary result" and "the result that mattered" can be years apart.
9. **Fetch friction.** SEC.gov rejects scripted requests without a declared contact; Business Wire and some investor sites return 403; ESMO meeting pages have moved and return 404.

## Caveats on specific rows

- **XZP-3621 (NCT05204628):** low confidence on the date. The listing document is dated from its HKEX file name (17 Sep 2025); an earlier application (25 Nov 2024) and the May 2024 NDA acceptance probably carried the same result but I could not open a source that states it. The registry primary endpoint does not say who assesses PFS; the disclosed figure is investigator-assessed.
- **POLARGO (NCT04182204):** date is that of the earliest dated congress coverage I opened (14 Jun 2025). The EHA abstract may have been online from mid-May 2025.
- **OBI-822 (NCT03562637):** "stopped_futility" rests on a DSMB stop recommendation at an interim analysis as reported by Taiwanese press; the company gave no efficacy data.
- **VIALE-T (NCT04161885):** the registry hazard ratio is descriptive; the sponsor states no hypothesis test was run.
- **SHR-A1811-307 (NCT06057610):** secondary source only; the original Hengrui notice was not opened.
- **CheckMate 227 and KEYNOTE-522:** rows describe the first primary endpoint to read out; later primaries were not traced.
- **"no" rows:** absence of evidence from roughly five to eight English and Chinese searches each, not proof that nothing exists. Only AK104-306 is backed by a recent sponsor document that lists the trial without a readout.
