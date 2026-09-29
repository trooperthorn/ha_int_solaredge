# Decisions

## 2026-09-29: New domain `solaredge_v2` instead of overriding `solaredge`

Rejected: shipping the custom integration under the core domain `solaredge`.
A custom integration with a core domain replaces the core one entirely, which
would also remove core's web-login module statistics, and the old entries
(V1 key, site ID) cannot be migrated anyway because V2 needs new credentials.
A separate domain lets both run side by side until V1 stops on
November 3, 2026.

## 2026-09-29: Own the V2 client in-tree

Rejected: depending on `aiosolaredge` (V1 only) or waiting for a V2 package.
No V2 client is on PyPI. An in-tree asyncio client that takes the shared
session closes `async-dependency`, `inject-websession`, `strict-typing`, and
`dependency-transparency` together, following the ha_int_elkm1 precedent.

## 2026-09-29: Support both Site Access and Fleet Access

Homeowners can only use Site Access (OAuth); SolarEdge says Fleet Access needs
an installer profile. Installers who already hold an account key would lose
their path if only OAuth were offered, and the API key path costs little
extra code. Rejected: OAuth only.

## 2026-09-29: Ask for the Site ID after OAuth

SolarEdge returns `site_id` on the callback, but Home Assistant's callback view
forwards only `code`, `state`, and `error` to the flow, and `GET /sites`
refuses OAuth tokens. Rejected: registering a custom callback view, which
would duplicate core's state verification. The flow asks for the ID and
proves access with `GET /sites/{id}` before creating the entry.

## 2026-09-29: Poll for the Free tier by default

Default interval 60 minutes and device telemetry off, so a single site fits
in 2,000 credits a month (1,860 used). Rejected: the core integration's
cadence, which polls overview, power flow, and energy details every 15 minutes
(its const.py); at one credit per call those three alone would be 8,640
credits in 30 days and need a paid tier.

## 2026-09-29: Explicit windows, HOUR for device telemetry, YEAR for lifetime

The API rejects more than 12 hours of 15-minute data, and every time-series
endpoint defaults to midnight-to-now, so relying on defaults fails every call
made after noon. Device telemetry uses `HOUR` from midnight to keep "today"
totals correct in one call; the alternative (two calls, one for power at 15
minutes and one for totals) doubles the telemetry cost. Lifetime energy sums
`YEAR` buckets because `TOTAL` has no documented span limit and `YEAR` is the
only resolution documented as unlimited.

## 2026-09-29: No optimizer data

The V2 Monitoring API exposes no optimizer telemetry. The web portal endpoints
that core's `solaredge_web` and the solaredgeoptimizers integration scrape are
not part of the V1 shutdown, so panel-level data stays with those. Rejected:
scraping the portal here, which would bring back username and password
storage and an unversioned, unstable surface.

## 2026-09-29: Scanner review findings that do not apply

- `oauth-clientresponseerror` in `application_credentials.py`: that code is
  the token implementation that raises `OAuth2TokenRequestReauthError` and
  `OAuth2TokenRequestTransientError`; it catches `ClientResponseError` from
  `raise_for_status()` only to translate it, exactly as the core helper does.
- `update-listener-plus-reload` in `config_flow.py`: the entry registers no
  update listener. Option changes reload through `OptionsFlowWithReload`, so
  `async_update_reload_and_abort` in reauth and reconfigure is the supported
  path.
