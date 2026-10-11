# Retained Hannover DIPUL source and rule audit

Verified 2026-10-11 from `hannover-part1-v4`; reproducible with
`doc/experiments/iteration-010/audit-dipul.py`. Original geometries are not exported.

31 layers, 324 features and 63 original DIPUL files verified by checksum.

## Complete layer inventory

| Layer | Features | Required review topic |
|---|---:|---|
| `dipul:bahnanlagen` | 17 | infrastructure |
| `dipul:behoerden` | 33 | facility_consent_and_applicability |
| `dipul:binnenwasserstrassen` | 11 | infrastructure |
| `dipul:bundesautobahnen` | 10 | infrastructure |
| `dipul:bundesstrassen` | 11 | infrastructure |
| `dipul:diplomatische_vertretungen` | 2 | facility_consent_and_applicability |
| `dipul:ffh-gebiete` | 7 | nature |
| `dipul:flugbeschraenkungsgebiete` | 0 | airspace |
| `dipul:flughaefen` | 1 | airspace |
| `dipul:flugplaetze` | 4 | airspace |
| `dipul:freibaeder` | 22 | operating_hours |
| `dipul:industrieanlagen` | 82 | facility_consent_and_applicability |
| `dipul:internationale_organisationen` | 1 | facility_consent_and_applicability |
| `dipul:justizvollzugsanstalten` | 4 | facility_consent_and_applicability |
| `dipul:kontrollzonen` | 4 | airspace |
| `dipul:kraftwerke` | 0 | facility_consent_and_applicability |
| `dipul:krankenhaeuser` | 27 | facility_consent_and_applicability |
| `dipul:labore` | 0 | facility_consent_and_applicability |
| `dipul:militaerische_anlagen` | 6 | facility_consent_and_applicability |
| `dipul:nationalparks` | 0 | nature |
| `dipul:naturschutzgebiete` | 8 | nature |
| `dipul:polizei` | 30 | facility_consent_and_applicability |
| `dipul:schifffahrtsanlagen` | 4 | infrastructure |
| `dipul:seewasserstrassen` | 0 | infrastructure |
| `dipul:sicherheitsbehoerden` | 18 | facility_consent_and_applicability |
| `dipul:stromleitungen` | 10 | infrastructure |
| `dipul:temporaere_betriebseinschraenkungen` | 0 | temporary_notice |
| `dipul:umspannwerke` | 2 | facility_consent_and_applicability |
| `dipul:vogelschutzgebiete` | 0 | nature |
| `dipul:windkraftanlagen` | 0 | facility_consent_and_applicability |
| `dipul:wohngrundstuecke` | 10 | residential |

Topics describe missing applicability/evidence checks, not blanket prohibitions or automatic permission rules.

## Primary endpoint audit

| Source | Endpoint scope | Original reference | Original vertical limits |
|---|---|---|---|
| `dipul:flugplaetze/flugplaetze.106` | destination | § 21h, Abs. 3 (1.) LuftVO | 0 m AGL; upper absent |
| `dipul:kontrollzonen/kontrollzonen.57` | origin and destination | NfL 2026-1-3960 | 510.82678799999996 ft MSL; 2500 ft MSL |
| `dipul:krankenhaeuser/krankenhaeuser.2275` | destination | § 21h, Abs. 3 (10.) LuftVO | 0 m AGL; upper absent |
| `dipul:wohngrundstuecke/wohngrundstuecke.1398` | origin | § 21h, Abs. 3 (7.) LuftVO | 0 m AGL; upper absent |

All four source features remain unresolved without supplied scenario evidence. The control-zone reference is NfL 2026-1-3960, not an inferred universal prohibition.
Its MSL floor cannot be compared directly with 100 m AGL and NHN terrain; no datum conversion or permission is invented.
The other three references are conditional geographic-area provisions. Evaluate the actual task/category, applicable conditions and any authorization; the source footprint alone does not prove a prohibition.

## Missing evidence and functional acceptance

Every feature has a legal reference and lower vertical fields; only four have upper vertical fields.
The retained nonempty properties supply no explicit validity interval. Permission/condition evidence is not part of these original WFS features.
A zero-count flight-restriction or temporary layer is an empty response within this snapshot scope; it is not a complete NOTAM clearance.

The implemented engine supports compatible vertical nonintersection, reviewed canonical notice time nonintersection and scoped supplied assessments.
Every other legal condition/exception stays unresolved until evaluated. Reviewed active prohibitions take precedence over generic, expired or wrong-scope allowances.
Source signatures for the four features are retained in the local audit JSON and computed by the UI; no real permission profiles are supplied.

Official references checked for this audit:

- [DIPUL WFS/WMS](https://www.dipul.de/homepage/de/informationen/geografische-gebiete/wfs-wms/)
- [DFS geographic areas and restrictions](https://www.dfs.de/homepage/de/drohnenflug/faq-zum-drohnenflug/)
- [LuftVO §21h](https://www.gesetze-im-internet.de/luftvo_2015/__21h.html)

The ordinance reference is also preserved in the original source records; publication-specific NfL conditions and complete NOTAM access remain explicit review gaps.
