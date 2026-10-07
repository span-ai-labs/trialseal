# 01: Reference classes and trial aliases

**What to build:** Every candidate trial carries its reference class (sponsor type by endpoint type) and the alternative names under which its readout may be announced. This is groundwork for screening, base rates and the readout monitor.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] Each candidate has a sponsor type and an endpoint type with three possible values: overall survival, progression-type, other time-to-event
- [ ] A trial whose primary endpoints span more than one endpoint type is classed by its scored endpoint, the first listed in the registry record
- [ ] Each candidate has an alias record: acronym, sponsor study number, intervention names and code names, lead sponsor and collaborators
- [ ] Candidates that mention a non-inferiority design are tagged for exclusion review, not silently dropped
- [ ] Existing candidate counts by window are unchanged by this work
- [ ] Tests use made-up registry records in the style of the existing universe tests
