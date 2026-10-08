# 06: Sealing proofs and verifier

**What to build:** Sealing a batch produces proof of its date that does not rely on trusting Span, and anyone can check a revealed forecast against the fingerprint published at sealing.

**Blocked by:** 02

**Status:** ready-for-agent

- [ ] The batch fingerprint is anchored by two independent time-stamping methods
- [ ] The fingerprint and the list of trials are pushed to the public repository; forecast content is not
- [ ] A verifier confirms that a revealed forecast belongs to a sealed batch, and rejects an altered one
- [ ] Sealing refuses to run when no registered protocol is recorded
- [ ] Sealing refuses to run when any trial in the batch lacks an eligible screening record
- [ ] The steps only a person can do (public repository, time-stamp setup) are walked through once and recorded
- [ ] Needs the study lead: creating the public repository

## Comments

**2026-10-08, from ticket 02's review.** The batch has one fingerprint over everything. That proves the whole batch existed, but it cannot prove a single trial's forecast at reveal without disclosing every other forecast in the batch, which ADR-0001 forbids. This ticket needs a commitment per forecast (for example a salted fingerprint for each, listed in the public record, or a tree of fingerprints) so that one forecast can be revealed and verified alone. Reading a batch back already refuses contents that no longer match the batch fingerprint.
