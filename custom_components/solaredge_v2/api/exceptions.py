"""Exceptions raised by the SolarEdge Monitoring API v2 client."""

from __future__ import annotations


class SolarEdgeError(Exception):
    """Base class for every error the client raises."""


class SolarEdgeConnectionError(SolarEdgeError):
    """The API could not be reached or did not answer in time."""


class SolarEdgeResponseError(SolarEdgeError):
    """The API answered with an unexpected status or an unparseable body."""

    def __init__(self, status: int, detail: str) -> None:
        """Store the HTTP status and the problem detail."""
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


class SolarEdgeAuthenticationError(SolarEdgeResponseError):
    """HTTP 401: the API key or OAuth token is missing, invalid, expired, or revoked."""


class SolarEdgeForbiddenError(SolarEdgeResponseError):
    """HTTP 403: no access to this site, a missing OAuth scope, or a tier gate."""


class SolarEdgeRateLimitError(SolarEdgeResponseError):
    """HTTP 429 with the per-minute window exhausted; retry after the window."""

    def __init__(self, status: int, detail: str, retry_after: int | None) -> None:
        """Store the retry-after hint in seconds, when the API sent one."""
        super().__init__(status, detail)
        self.retry_after = retry_after


class SolarEdgeCreditLimitError(SolarEdgeResponseError):
    """HTTP 429 with the monthly credit quota exhausted; retrying will not help."""
