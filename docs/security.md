# Security

## Trust boundaries

| Boundary | What crosses it | Control | Enforced or not |
| --- | --- | --- | --- |
| Home Assistant to `monitoringapi.solaredge.com` | API key or bearer token, site ID | HTTPS through Home Assistant's shared aiohttp session with certificate verification; credentials only in headers | Enforced by the client: no code path puts a credential in a URL, and a test asserts the key never appears in any request URL |
| Browser to `connect.solaredge.com` | The user's mySolarEdge sign-in | SolarEdge's consent screen; Home Assistant never sees the password | Enforced by SolarEdge |
| OAuth callback to Home Assistant | Authorization code and signed `state` | Home Assistant verifies the JWT `state` before accepting a code | Enforced by core |
| Config entry storage | API key, access and refresh tokens, client secret (in application credentials) | `.storage` files readable by anything running as the Home Assistant user | Not protected against other code in the same process or on the same host |

## Credential scope

- A Fleet Access key carries every scope for every site associated with the
  account; SolarEdge applies no scope filter to API keys (documented). Treat
  it as account-wide read access.
- A Site Access token is limited to the approved site and the scopes chosen
  on the consent screen. Requesting only `SITE_DATA` narrows it further at the
  cost of device telemetry.
- Neither credential can change anything: the Basic Monitoring API is read
  only.

## Diagnostics

Diagnostics redact `api_key`, `token`, `access_token`, and `refresh_token`.
They keep the site ID, site name, device serial numbers, and alert details,
which identify the installation; review a diagnostics file before sharing it
publicly.

## Revocation

Rotating or deleting the application in the SolarEdge developer console
invalidates its credentials. A single Site Access token can be revoked with
`POST /v2/oauth2/revoke-token`. The integration does not call revocation on
removal; that is listed in [backlog.md](backlog.md).
