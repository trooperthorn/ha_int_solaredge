# Changelog

## Unreleased

- Added tests proving that the API key, access token, refresh token, and
  client secret never reach a log line, an error message, or a request URL
  when the site call or the token refresh fails. Prompted by the core V1
  `solaredge` integration writing its API key to the log on a 503; see
  docs/security.md (Logs) and docs/decisions.md.
- Test fixture `mock_api` accepts an exception to fail a route at the
  transport level.

## 2026.09.29.2

- First release. Reads a SolarEdge site through the Monitoring API v2 with
  Site Access (OAuth 2.0) or Fleet Access (App API Key), replacing the V1 API
  that SolarEdge switches off on November 3, 2026.
