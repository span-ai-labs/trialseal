---
status: accepted
---

# Sponsor type follows the registry, with a published list of corrections

The registered primary analysis is on industry-led trials (ADR-0003), and a trial's sponsor type was taken from the registry's class for its lead sponsor alone. The registry gets some of these wrong: on 2026-10-09 it classed ten companies that develop or sell a drug or a device as "other", among them Shanghai Junshi with 16 trials. Their trials would have been left out of the primary comparison, and two were counted as positive results in the base rate for trials that are not industry-led.

A sponsor on a fixed list of such companies is industry-led whatever the registry says. The list is in the code (`COMPANIES_THE_REGISTRY_CLASSES_OTHERWISE`) and is published with the protocol. A correction only ever makes a sponsor industry-led; it never makes one not. A sponsor is listed only if it is plainly a company developing or selling a product for profit: cooperative groups, foundations, hospital corporations and non-profit trial organisations stay as the registry has them, whatever legal form their name carries.

The sponsor type is sealed with each trial in a batch, so a name added to the list later changes only batches sealed afterwards and can never move a sealed trial into or out of the primary analysis set.

We rejected classifying sponsors ourselves from their names or from a lookup of each one: it would put a judgement on every trial where the registry's class is right nearly always. We also rejected leaving the registry's class alone, since the errors run one way and fall on exactly the trials the primary claim is about.

The list was found by reading the names of lead sponsors that the registry does not class as industry and that look like company names. A company whose name does not look like one will have been missed.
