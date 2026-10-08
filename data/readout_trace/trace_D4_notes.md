# Readout trace, sample D4 (26 trials) — notes

Traced 2026-10-09. Data: `trace_D4.csv` (one row per trial, same order as `sample_D4.csv`). Input: `sample_D4.csv`.

## Conventions used

Same as `trace_A_notes.md` and `trace_C1_notes.md`. Points that mattered in this tranche:

- Dual primary endpoints on the same comparison, either sufficing: one met is `met`, with the missed one named in `which_endpoint` (LEAP-015).
- A win at an interim analysis with the trial continuing is `met` (DESTINY-Breast05, LEAP-015 PFS).
- A trial that the registry shows as suspended, with no analysis and no formal end, is `disclosed = no` with a blank `primary_result` (EndoTAG-1, ICT-107), not `terminated_no_analysis`.
- Six registry dates are month-only; only one of them (FRUSICA-2, 2025-01, taken as the 15th) is a disclosed row and enters a lag.
- Summary statistics use the 6 `disclosed = yes` rows only.

## A limit on this tranche: the web-search allowance ran out

The session's shared web-search allowance was exhausted after about 25 searches. From then on I used only sources I could address directly: ClinicalTrials.gov, PubMed, the Hong Kong exchange's announcement index and PDFs (Hengrui, CSPC, RemeGen, Lepu, Biostar, Genor, Hutchmed), AstraZeneca's results documents and 6-K list on SEC EDGAR, Pfizer's Q2 2026 earnings release, and the Roche, SynCore and Puhe websites. Twelve rows had no general web search at all: NCT03002103, NCT06759857, NCT04619433, NCT02546102, NCT05945901, NCT06082635, NCT06296706, NCT06319313, NCT04639180, NCT06152575, NCT06417814, NCT06618664. Each says so in `search_notes`. For the Hengrui, CSPC and AstraZeneca rows the sponsor's own documents are a strong substitute; for the four small unlisted sponsors (SynCore, Chia Tai Fenghai, Precision Life Sciences, TargetRx) they are not, and those rows are `confidence = low`.

## Counts

| disclosed | n |
|---|---|
| yes | 6 |
| no | 20 |
| unclear | 0 |

| primary_result | n |
|---|---|
| met | 5 |
| not_met | 1 |
| terminated_no_analysis | 1 |
| blank (not read out) | 19 |

Of the 6 disclosed trials: 5 met (LEAP-015 on PFS only, FRUSICA-2, AcceleRET-Lung, DESTINY-Breast05, LEONARDA-2), 1 not met (CARES). The 20 `no` rows are 1 termination without a primary analysis (SHR-1210-III-324, 48 patients) and 19 with nothing read out, of which two are suspended on the registry (EndoTAG-1, ICT-107) and one has had its enrolment suspended by the sponsor (utidelone, below).

Confidence: 6 high, 12 medium, 8 low.

## Lag from registry primary completion date to first disclosure

- All 6 disclosed: median **88 days**, range **-674 to +234 days**.
- 1 of 6 was disclosed before the registry date: LEONARDA-2, -674 days, on a registry record that has not been updated since May 2023.
- The 5 disclosed after the registry date: median **89 days**, range 62 to 234. Four fall between 62 and 99 days; the outlier is AcceleRET-Lung (234), a terminated trial with no press release.
- By registry date type: ACTUAL (n=4) median 94 days; ESTIMATED (n=2) 62 and -674.

## Hazard ratios

- Numeric HR in the first disclosure: **0 of 6**.
- A numeric HR for the primary endpoint is public for 4 of 6. Delay from first disclosure to first HR: DESTINY-Breast05 19 days, LEAP-015 127, AcceleRET-Lung 168, FRUSICA-2 209 (median 147.5).
- No HR: CARES (the primary endpoint is a win ratio, so the cells are blank by rule; the win ratio is in the note) and LEONARDA-2 (nothing found).
- FRUSICA-2 has an HR (0.373) but no confidence interval in any source opened.
- The AcceleRET-Lung HR was first public as a ClinicalTrials.gov results posting, 12 weeks before the conference.

## Which source came first

| first source | n |
|---|---|
| press release | 4 |
| exchange announcement (annual results, HKEX) | 1 |
| other (sponsor's lay summary of results) | 1 |

Two of the six were not stand-alone announcements. LEONARDA-2 is one sentence in Genor's 2023 annual results. AcceleRET-Lung is a plain-language results summary for trial participants on Roche's trial page, with no press release, pipeline line or exchange notice found. Twenty-one of the 26 trials have a lead sponsor that does not file with the SEC (the Chinese and Taiwanese sponsors other than Hutchmed, plus Roche, Daiichi Sankyo and Precision Life Sciences); 3 of the 6 first disclosures came from them (Roche, Genor, and Daiichi Sankyo, whose DESTINY-Breast05 release was joint with AstraZeneca, an SEC registrant).

## Rows to treat with care

- **NCT04222972 (AcceleRET-Lung)**: the first-disclosure date (2025-09-18) is the date printed on Roche's lay summary, not a verified posting date. Web-archive copies of the trial page bracket the posting between 12 Sep and 14 Dec 2025. The summary gives medians only; "met" rests on the registry results (HR 0.59, p=0.0027, posted 2026-03-05) and ASCO 2026 coverage. If the adjudicators want a date at which statistical significance was public, it is 2026-03-05. The trial is registered as terminated, yet had a primary analysis.
- **NCT04662710 (LEAP-015)**: `met` on PFS under the either-endpoint rule; OS, the other dual primary, was missed and the trial is generally read as negative. Could be argued as `mixed`.
- **NCT05673590 (utidelone vs docetaxel)**: `no`, but the sponsor's interim results of 26 Aug 2026 describe an ORR and PFS advantage without numbers, say OS (the primary) has not been reached, and say enrolment is suspended at about 300 of 612 with the trial to be restarted or terminated. Could be argued as `unclear`; may become `terminated_no_analysis`. Data are due at ESMO, 23-27 Oct 2026.
- **NCT05851014 (LEONARDA-2)**: matched to Genor's statement by drug, line and comparator, not by protocol number; no HR or presentation found. An earlier investor presentation is possible but none appears in the HKEX index between Oct 2023 and Mar 2024.
- **NCT04512235 (CARES)**: the topline was reported pooled across this trial and its sibling NCT04504825; the endpoint is a win ratio.
- **NCT04619433 (SHR-1210-III-324)**: `terminated_no_analysis` is inferred from 48 enrolled; the registry gives no reason.
- **NCT03002103 (EndoTAG-1)** and **NCT02546102 (ICT-107)**: suspended, not terminated, on the registry; coded `no` with a blank result. A 2022 SynCore notice about ending an unnamed phase 3 trial may refer to the first.
- **NCT06759857 (FHND9041)**, **NCT06082635 (TGRX-326)**, **NCT05767892 (YK-029A)**, **NCT05594927 (icaritin)**, **NCT05518318 (GLS-010)**, **NCT05868707 (OH2)**: `no` from the registry, PubMed and (for some) one web search only. These are unlisted Chinese sponsors whose first disclosure would be a Chinese-language notice or a conference abstract. Absence of evidence, not proof.
- **NCT06152575 (MagnetisMM-32)**: nothing after Pfizer's Q2 2026 release of 4 Aug 2026 could be checked.
- **Hengrui rows (NCT04691063, NCT05945901, NCT04639180)**: `no` rests on the 2026 interim results and on reading all 26 filing-acceptance notices Hengrui put on HKEX between Aug 2025 and 9 Oct 2026. Hengrui was not on HKEX before May 2025, so an earlier Shanghai-only notice would not be in that set; the 2026 pipeline table still lists limited-stage SCLC as phase 3.
- **NCT06417814 (TROPION-Lung15)** and **NCT06618664 (KYLIN-02)**: registry dates fall in Sept-Oct 2026; AstraZeneca guides TROPION-Lung15 to H2 2026, so that row may change within weeks.
