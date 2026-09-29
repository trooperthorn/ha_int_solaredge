"""SolarEdge Monitoring API v2 client owned by this integration."""

from .auth import ApiKeyAuth, AuthProvider, BearerTokenAuth
from .client import BASE_URL, SolarEdgeClient
from .exceptions import (
    SolarEdgeAuthenticationError,
    SolarEdgeConnectionError,
    SolarEdgeCreditLimitError,
    SolarEdgeError,
    SolarEdgeForbiddenError,
    SolarEdgeRateLimitError,
    SolarEdgeResponseError,
)
from .models import (
    Alert,
    Device,
    DeviceType,
    Sample,
    Series,
    SiteData,
    SiteMetadata,
    SiteOverview,
    SiteSummary,
    Telemetry,
)

__all__ = [
    "BASE_URL",
    "Alert",
    "ApiKeyAuth",
    "AuthProvider",
    "BearerTokenAuth",
    "Device",
    "DeviceType",
    "Sample",
    "Series",
    "SiteData",
    "SiteMetadata",
    "SiteOverview",
    "SiteSummary",
    "SolarEdgeAuthenticationError",
    "SolarEdgeClient",
    "SolarEdgeConnectionError",
    "SolarEdgeCreditLimitError",
    "SolarEdgeError",
    "SolarEdgeForbiddenError",
    "SolarEdgeRateLimitError",
    "SolarEdgeResponseError",
    "Telemetry",
]
