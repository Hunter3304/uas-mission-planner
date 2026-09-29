# 6. EGRED 2

Reviewed: 2026-09-29. Decision: **scenario-dependent operational guidance**.

## Identity and evidence

EGRED means *Empfehlungen für Gemeinsame Regelungen zum Einsatz von Drohnen im
Bevölkerungsschutz*. BBK describes guidance for non-police authorities and
organizations with security responsibilities (BOS), or operations on their behalf.
It addresses coordinated operations, risk assessment and training, including
coordination when rescue/police helicopters operate nearby.
Source: [BBK introduction to EGRED 2](https://www.bbk.bund.de/SharedDocs/Pressemitteilungen/DE/2023/12/pm-18-egred2.html).

The official indexed [publication](https://www.bbk.bund.de/SharedDocs/Downloads/DE/Mediathek/Publikationen/Krisenmanagement/EGRED2.pdf?__blob=publicationFile&v=25)
identifies Version 2, June 2024, and refers readers to
[BBK's EGRED page](https://www.bbk.bund.de/egred) for revisions/change history.
The landing page could not be fetched in this session. June 2024 is the edition
located, not a verified claim about the latest edition. The PDF URL's `v=` is
not a semantic EGRED edition number.

| Requested field | Assessment |
| --- | --- |
| Access | Public BBK publication download; no geographic API identified. |
| Format | PDF guidance, tables and procedures; not a spatial dataset. |
| Update frequency | Revised editions/change history; no fixed publication interval confirmed. |
| Spatial resolution | Not applicable. Any incident geometry would come from other data or operator input. |
| Automatic use | Partial, after reviewed translation into checklists and scenario rules. Human operational inputs remain necessary. |

## Proposed use in this project

Engineering proposal: first determine whether the demonstration is a BOS response
mission, a normal civil mission, or a comparison between both. Apply EGRED through
an explicitly selected scenario, rather than assigning every map cell an “EGRED cost”.

Possible project features include recording coordination status, incident-area
boundaries, mission responsibilities and unresolved operational checks. Incident
areas and helicopter activity would be supplied separately; the document does
not provide a current map of either.

Do not infer BOS privileges from the fact that the prototype is a university
project. A BOS scenario must not automatically disable all geographical-zone checks.
Likewise, do not assume the located 2024 document incorporates EASA's later SORA
2.5 implementation; compare the cited editions when translating rules.

## Next validation

Retrieve the current edition and change log from BBK, identify applicable
sections for the selected scenario, and make a small rule/checklist mapping with
source section, required input, automatic/manual status and expected outcome.
Link to the publication rather than bundling it in the repository without a
reuse assessment. No operational rules were extracted into executable code here.
