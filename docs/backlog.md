# Backlog

- 2026-09-29: Verify against the live API with a real Site Access grant: that
  SolarEdge Connect echoes `state` and tolerates `response_type` and
  `redirect_uri` on the authorize URL; that repeated `types` parameters return
  meters and batteries; that `YEAR` energy from the installation date sums to
  the portal's lifetime figure; the meaning of the `PERCENTAGE_100` unit. Each
  is marked unverified in [protocol.md](protocol.md).
- 2026-09-29: Revoke the Site Access token on entry removal
  (`POST /v2/oauth2/revoke-token`).
- 2026-09-29: Consider importing hourly device energy as long-term statistics
  so device history survives an interval of several hours.
- 2026-09-29: Read `x-ratelimit-remaining-minute` into a diagnostic value
  once live responses confirm the header is sent on success, not only on 429.
