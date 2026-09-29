# Operations

## Configuration keys

Stored in `ConfigEntry.data` (connection):

| Key | Access type | Meaning |
| --- | --- | --- |
| `auth_type` | both | `oauth` or `api_key`; selects the header provider at setup. |
| `site_id` | both | Integer SolarEdge site ID; also the entry's unique ID (as a string). |
| `api_key` | Fleet Access | App API Key sent as `X-API-Key`. |
| `auth_implementation`, `token` | Site Access | Written by Home Assistant's OAuth helper; `token` holds the access and refresh tokens and `expires_at`. |

Stored in `ConfigEntry.options` (behavior); changing them reloads the entry:

| Key | Default | Bounds | Consequence |
| --- | --- | --- | --- |
| `scan_interval_minutes` | 60 | 15 to 360 | Fast-cadence interval. Lower than 15 spends credits on an unchanged bucket, so the form does not allow it. |
| `device_telemetry` | false | | Creates inverter, meter, and battery sensors; costs one credit per device family per update. |

## Credit budget

Every call costs one credit (documented). A 30-day month has 720 hours.

| Cadence | Calls per run | Runs in 30 days | Credits |
| --- | --- | --- | --- |
| Fast, 60-minute interval | 2 | 720 | 1,440 |
| Slow, every 6 hours | 3 | 120 | 360 |
| Inventory, every 12 hours | 1 | 60 | 60 |
| **Defaults total** | | | **1,860** |

Adding per-device telemetry costs one more credit per update for each device
family present. For a site with one inverter family and nothing else, that is
720 more at 60 minutes (2,580 total, over the Free tier's 2,000) or 480 more
at 90 minutes (fast 3 x 480 = 1,440, plus 420, for 1,860 total). A site with
inverter, meter, and battery at 120 minutes uses 5 x 360 + 420 = 2,220.

Setup and every reload spend two credits (metadata and inventory) plus one
full first refresh (five credits, more with telemetry), so repeated reloads
while troubleshooting count against the month.

When the quota runs out, the API answers 429 with no `retry-after`; the
integration raises the `credit_limit` repair issue and retries every six hours
until the billing cycle resets.

## Local gate

The Home Assistant test harness imports `fcntl`, so the suite runs under WSL
on Windows. The venv is created once:

```bash
python3.14 -m venv ~/solaredgevenv
~/solaredgevenv/bin/pip install -r requirements-dev.txt
~/solaredgevenv/bin/pip install -r requirements-core.txt
```

The harness pins the beta core it was cut from, so the stable core is pinned
in its own file and installed second; CI asserts the installed version. Then,
from the repository root:

```bash
~/solaredgevenv/bin/ruff check .
~/solaredgevenv/bin/mypy --config-file mypy.ini
~/solaredgevenv/bin/pytest --cov tests/
python3 scripts/build_release_artifacts.py --validate-only
```

Coverage must be 100 percent, lines and branches (`pyproject.toml`).

## Releases

A merge to `main` is the only release path. `release.yml` reruns the test and
validation workflows, reads the version from `manifest.json` through
`.release.json`, and publishes `v<version>` with `solaredge_v2.zip`, an SPDX
SBOM, `SHA256SUMS`, and provenance and SBOM attestations. `prepare-release.yml`
opens a version-bump pull request when release paths changed since the last
tag; it needs the release GitHub App's client ID variable and private key
secret. Versions are CalVer `YYYY.MM.DD.N` in America/Chicago time.
