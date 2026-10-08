# 06: Sealing proofs and verifier

**What to build:** Sealing a batch produces proof of its date that does not rely on trusting Span, and anyone can check a revealed forecast against the fingerprint published at sealing.

**Blocked by:** 02

**Status:** ready-for-human

- [x] The batch fingerprint is anchored by two independent time-stamping methods
- [ ] The fingerprint and the list of trials are pushed to the public repository; forecast content is not
- [x] A verifier confirms that a revealed forecast belongs to a sealed batch, and rejects an altered one
- [x] Sealing refuses to run when no registered protocol is recorded
- [x] Sealing refuses to run when any trial in the batch lacks an eligible screening record
- [x] The steps only a person can do (public repository, time-stamp setup) are walked through once and recorded
- [ ] Needs the study lead: creating the public repository

## Comments

**2026-10-08, from ticket 02's review.** The batch has one fingerprint over everything. That proves the whole batch existed, but it cannot prove a single trial's forecast at reveal without disclosing every other forecast in the batch, which ADR-0001 forbids. This ticket needs a commitment per forecast (for example a salted fingerprint for each, listed in the public record, or a tree of fingerprints) so that one forecast can be revealed and verified alone. Reading a batch back already refuses contents that no longer match the batch fingerprint.

**2026-10-08, implemented; two items left for the study lead.** Sealing gives each forecast its own commitment (a fingerprint of the forecast mixed with a secret value), publishes a seal holding the trials and commitments and no forecast, and anchors the SHA-256 of the seal file with one service of each kind. A revealed forecast is checked with `trialseal-verify`; the anchors are checked with OpenSSL and the OpenTimestamps client directly. 116 tests pass, plus a live check against DigiCert and an OpenTimestamps calendar.

Checked against the real tools: the time-stamp request is byte-identical to OpenSSL's own; DigiCert's reply verifies with both the Homebrew OpenSSL and the system LibreSSL; the OpenTimestamps file is read correctly by the official client.

Two rounds of review found and fixed, each with a test: publishing could push other staged or unpushed work, including history later undone; anchors were accepted on a substring match; the signing day could be forged through unsigned status text; a seal file could carry extra content; a batch could be sealed on another day; trial identifiers had more than one spelling.

Left for the study lead:

- Run `scripts/setup_wizard.sh` to record the time-stamping services, create the public repository and, later, record the protocol registration.
- The first push makes the whole history public: code, glossary, decision records, the spec, the tickets and the research notes. The spec's problem statement mentions an investor declining and two null preprints. Decide what should be public before pushing.

Known limits:

- The OpenTimestamps anchor is only checked for layout and fingerprint here; whether it has reached the block chain needs the official client. At sealing it has not yet.
- Bytes appended after a valid anchor are not detected.
- Only DigiCert's replies verify against a standard certificate bundle; FreeTSA needs its own certificate.
- The private openings under `private/` have no backup.
