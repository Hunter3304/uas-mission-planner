# 5. SORA 2.5

Reviewed: 2026-09-29. Decision: **methodological input from the start**.

## Source and version

JARUS publishes the SORA 2.5 package dated 13 May 2024, with main body and annexes:
[official publications](https://jarus-rpas.org/publications/). For a German/EU
scenario, distinguish this from the EASA implementation introduced through
[ED Decision 2025/018/R](https://www.easa.europa.eu/en/document-library/agency-decisions/ed-decision-2025018r).
The [June 2026 Easy Access Rules release](https://www.easa.europa.eu/en/newsroom-and-events/news/easa-published-revision-june-2026-easy-access-rules-unmanned-aircraft-systems)
incorporates that decision and offers PDF, online and machine-readable XML.

| Requested field | Assessment |
| --- | --- |
| Access | Public JARUS publications and EASA rule documents; no geographical-data endpoint required. |
| Format | PDF; EASA additionally HTML/XML. Machine-readable text is not an executable risk engine. |
| Update frequency | Versioned document revisions, not a live geographic feed. Pin edition and amendments. |
| Spatial resolution | Not applicable to the document. Population assessment has operation-dependent grid guidance. |
| Automatic use | Selected calculations and completeness checks can be implemented after specifying inputs and interpretation. Full assessment is not supplied by map data alone. |

## Routing-relevant meaning

EASA's [AMC1 Article 11, Step 2](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-unmanned-aircraft-systems?erules-id=ERULES-1963177438-24086)
relates intrinsic ground risk to population density, aircraft characteristic
dimension and maximum speed. It uses the highest-density segment within the
iGRC footprint and discusses appropriate population-map scale and authority
acceptability. Consequently, a route-average population score is not an iGRC.

## Proposed use in this project

Engineering proposal: keep two clearly labeled outputs:

1. A research routing objective, with explicit costs and weights.
2. A versioned assessment report listing supported checks and missing evidence.

Define the mission, aircraft parameters, operational volume, ground-risk buffer,
timing, airspace context and claimed mitigations before choosing which assessment
steps to encode. GHSL may supply a population input; it does not supply those
other inputs or automatically establish acceptable population data for an operation.

For a first experiment, calculate transparent population statistics over an
explicitly defined footprint and list intersected zones. Leave unavailable risk
classes unresolved. Do not translate the existing Ramke 0–4 tag costs directly
into GRC, ARC or SAIL.

## Next validation

Select the EASA/JARUS edition explicitly, identify the exact sections needed for
the chosen mission, and create an input-to-rule traceability table. Any encoded
table must have boundary tests and documented units. This assessment has not
transcribed thresholds or implemented compliance logic.
