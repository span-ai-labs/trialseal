# 12: Readout monitor

**What to build:** Candidate readouts are surfaced wherever they first appear and queued for a person to confirm. How many it finds is measured against the reference set.

**Blocked by:** 04, 05

**Status:** ready-for-agent

- [ ] Sources include company announcements, US filings, Hong Kong and Shanghai exchange announcements, conference abstracts, the literature and registry postings
- [ ] Matching uses the alias record, and sister trials of the same drug are not confused
- [ ] Every candidate readout goes to a confirmation queue; nothing is resolved automatically
- [ ] Recall and false-match rate are reported against the traced reference set
- [ ] Trials whose registry record has gone stale are flagged for a manual check
- [ ] The monitor runs on a schedule and records what it checked each time
