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
