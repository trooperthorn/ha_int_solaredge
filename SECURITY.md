# Security Policy

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, private
addresses, or logs. Use GitHub's private vulnerability-reporting feature for
this repository. If private reporting is unavailable, open a minimal issue
asking the maintainer to establish a private channel; omit technical details.

Include the affected version/commit, prerequisites, impact, a minimal
reproduction, and suggested remediation. Remove tokens, API keys, cookies,
usernames, site IDs, and private network details.

## Response targets

These are project targets, not an SLA: acknowledge critical/high reports in
three business days, establish severity and containment in seven, and publish
a coordinated fix/advisory as soon as safely validated. Lower-severity issues
are prioritized by exploitability and impact.

## Supported version

Only the latest published release and the default branch receive security
fixes. Operators should update Home Assistant and this integration promptly and
retain a tested rollback/backup.

## Security boundaries

This integration is a read-only client of the SolarEdge cloud API. It holds a
Fleet Access API key or a Site Access OAuth token in the Home Assistant config
entry and sends it only to `monitoringapi.solaredge.com` over HTTPS, in a
header, never in a URL. Any code running in the same Home Assistant process
can read those credentials; the integration cannot prevent that. The trust
boundaries are described in [docs/security.md](docs/security.md).
