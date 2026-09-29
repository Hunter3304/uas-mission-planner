# 1. Droniq / TraX

Reviewed: 2026-09-29. Decision: **conditional, later dynamic-traffic integration**.

## Verified source characteristics

TraX is an app/web product with subscription tiers. Droniq separately offers
external live-air-traffic integration, including integrations with edp:map and
CommandX. Therefore “no external interface exists” would be incorrect, but a
TraX subscription is not evidence of a general developer API entitlement.
Sources: [TraX product](https://droniq.de/en/trax-abomodelle/),
[external interface product](https://droniq.de/produkte/live-luftlage-daten-schnittstelle/).

Droniq's FAQ identifies radar, ADS-B, FLARM and optional Remote ID as inputs to
its external traffic interface. The reviewed public material did not establish
a downloadable API schema, authentication mechanism, wire format, update
interval, latency guarantee or positional accuracy for our intended integration.
Source: [Droniq FAQ, Datenschnittstelle](https://droniq.de/faq/).

| Requested field | Assessment |
| --- | --- |
| Access | App/web access; provider-arranged external integration. Research access must be confirmed. |
| Format | Machine-to-machine interface exists; JSON, XML, REST or streaming protocol must not be assumed. |
| Update frequency | Live product; numerical cadence, timestamp semantics and maximum age remain unknown. |
| Spatial resolution | Track positions rather than a population grid. Accuracy, low-altitude coverage and detection completeness remain unknown. |
| Automatic use | Potentially possible after obtaining interface documentation and authorization. Not validated here. |

## Proposed use in this project

Engineering proposal: introduce a separate time-dependent traffic adapter,
not another OSM tag table. Normalize track identity, observation time, position,
altitude reference, velocity and quality only when supported by the feed.

First show time-stamped tracks and their age. Later evaluate conflicts between
candidate route timing and track predictions. Missing or stale traffic must
remain “unknown”; an empty response must not imply empty airspace. This cannot
be represented adequately by a permanent 2D exclusion polygon.

The current demo has neither route timing nor a live-data lifecycle. Making this
feed the first integration would introduce several dependencies simultaneously.

## Questions needed before implementation

- Is a university/research API account available for a custom Python application?
- Which protocol, schema, sample messages and authentication method are supplied?
- What are the geographic/altitude coverage, update rate, latency and quality fields?
- May observations be stored and replayed for reproducible experiments?
- What attribution, retention, redistribution, quota and cost conditions apply?

These are a preparation list; no inquiry has been sent. Until resolved, use this
source as a documented integration dependency rather than promising live routing.
