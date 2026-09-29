# Design

## Layers

The integration has two layers with one boundary between them.

- `custom_components/solaredge_v2/api/` is a small asyncio client for the
  Basic Monitoring API v2. It imports nothing from Home Assistant. It takes an
  `aiohttp.ClientSession` from the caller and an `AuthProvider` that returns
  the authentication header for each request, so the same client serves both
  access types. It returns typed dataclasses with every power value in watts
  and every energy value in watt-hours, whatever unit the API chose.
- The Home Assistant layer (`__init__.py`, `coordinator.py`, `sensor.py`,
  `config_flow.py`, `application_credentials.py`) owns setup, polling,
  entities, and error translation.

Owning the client in-tree, instead of depending on a PyPI package, is what
satisfies the Platinum rules `async-dependency`, `inject-websession`, and
`strict-typing` together: the code is asyncio, it uses Home Assistant's shared
session, and mypy checks it under `strict = true` with `py.typed` shipped. The
same pattern closed those rules in ha_int_elkm1. No V2 library exists on PyPI
today (checked 2026-09-29: the core integration's `aiosolaredge==1.0.2` targets
V1).

## Authentication

`AuthProvider` has two implementations.

- `ApiKeyAuth` returns `X-API-Key: <key>` for Fleet Access.
- `BearerTokenAuth` awaits a token getter and returns
  `Authorization: Bearer <token>` for Site Access. In `__init__.py` the getter
  is `OAuth2Session.async_ensure_token_valid()` followed by reading the stored
  access token, so refresh happens transparently before any call.

The header is computed before the request's `try` block. That placement is
deliberate: Home Assistant's OAuth errors subclass `aiohttp.ClientError`, and
catching them as connection errors would turn a revoked refresh token into an
endless retry instead of a reauthentication.

`application_credentials.py` subclasses the core `AuthImplementation` only to
send the token request as JSON, which SolarEdge's token endpoint requires, and
to add `scope` and `access_duration` to the authorize URL. Error mapping
mirrors the core helper: HTTP 429 and 5xx are transient, other 4xx need
reauthentication.

## Coordinator cadences

One `DataUpdateCoordinator` per site. The monthly credit quota, not freshness,
is the binding constraint, so data is split by how fast it changes.

| Cadence | Calls | Why |
| --- | --- | --- |
| Update interval (default 60 min) | overview, power; telemetry when enabled | Production and power change continuously. |
| 6 hours | site metadata, lifetime energy, open alerts | Lifetime energy only needs to be close; alerts are advisory. |
| 12 hours | device inventory | Devices are added or replaced rarely. |

`_async_setup` loads metadata and inventory once so entities exist before the
first refresh, and the first refresh then fetches the slow data immediately.

Every time-series call sends an explicit window in site wall-clock time, taken
from the site's `location.timezone` (Home Assistant's zone as a fallback),
because the API's default window runs from midnight and exceeds the 12-hour
limit for 15-minute buckets after noon. Site power reads the last hour at 15
minutes. Device telemetry reads midnight to now at `HOUR` so the "today"
totals are sums over one day inside the 24-hour limit; device power is
therefore an hourly average. Lifetime energy sums `YEAR` buckets from the
installation date, the only resolution the API documents as unlimited.

Telemetry calls are made only for device families the inventory reports as
active, so a site without a battery never spends a credit on storage.

## Error translation

`_ErrorTranslator` is the single place where client and OAuth errors become
coordinator exceptions:

| Error | Result |
| --- | --- |
| HTTP 401, or an OAuth refresh rejected with 4xx | `ConfigEntryAuthFailed` (reauthentication) |
| HTTP 429 with `x-ratelimit-remaining-minute` above 0 (credit limit) | Repair issue plus `UpdateFailed` retrying in 6 hours |
| HTTP 429 otherwise (per-minute limit) | `UpdateFailed` honoring `retry-after` |
| HTTP 403 on device telemetry | Telemetry stops until reload, repair issue, site data continues |
| Anything else from the client, OAuth transient errors, aiohttp errors | `UpdateFailed` |

## Devices and entities

The site is a service device (`DeviceEntryType.SERVICE`) registered in
`async_setup_entry`. Inverters, meters, and batteries link to it with
`via_device_id`, resolved through `async_get_device_id_by_identifier`, because
`via_device` is deprecated since 2026.8 with removal in 2027.8.

Unique IDs are `<site_id>_<key>` for site sensors and `<serial>_<key>` for
device sensors, so they survive a change of access type.

Dynamic devices: the sensor platform adds entities for any new serial after
each refresh. Stale devices: when the inventory refresh no longer lists a
serial, its device is removed from the registry; `async_remove_config_entry_device`
also lets the user delete such a device by hand.
