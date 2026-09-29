"""Authentication header providers for the two V2 access types."""

from __future__ import annotations

from typing import Protocol


class AuthProvider(Protocol):
    """Supplies the authentication header for one request."""

    async def async_get_headers(self) -> dict[str, str]:
        """Return the headers that authenticate the next request."""
        ...


class ApiKeyAuth:
    """Fleet Access: a static App API Key sent as X-API-Key."""

    def __init__(self, api_key: str) -> None:
        """Store the key."""
        self._api_key = api_key

    async def async_get_headers(self) -> dict[str, str]:
        """Return the X-API-Key header."""
        return {"X-API-Key": self._api_key}


class BearerTokenAuth:
    """Site Access: an OAuth 2.0 access token supplied by a callable that refreshes it."""

    def __init__(self, token_getter: TokenGetter) -> None:
        """Store the callable that returns a currently valid access token."""
        self._token_getter = token_getter

    async def async_get_headers(self) -> dict[str, str]:
        """Return the Authorization header with a fresh token."""
        return {"Authorization": f"Bearer {await self._token_getter()}"}


class TokenGetter(Protocol):
    """Returns a valid access token, refreshing it first when needed."""

    async def __call__(self) -> str:
        """Return the access token."""
        ...
