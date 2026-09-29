"""Application credentials for SolarEdge Site Access (OAuth 2.0)."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any, cast, override

from aiohttp import ClientResponseError
from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    OAuth2TokenRequestReauthError,
    OAuth2TokenRequestTransientError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import OAUTH2_ACCESS_DURATION_MONTHS, OAUTH2_AUTHORIZE, OAUTH2_SCOPES, OAUTH2_TOKEN


class SolarEdgeOAuth2Implementation(AuthImplementation):
    """SolarEdge's token endpoint takes a JSON body, not form encoding."""

    @property
    @override
    def extra_authorize_data(self) -> dict[str, Any]:
        """Request both scopes and the longest grant SolarEdge Connect allows."""
        return {"scope": OAUTH2_SCOPES, "access_duration": OAUTH2_ACCESS_DURATION_MONTHS}

    @override
    async def _token_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Post the token request as JSON and map failures like the core helper."""
        payload = {**data, "client_id": self.client_id, "client_secret": self.client_secret}
        session = async_get_clientsession(self.hass)
        resp = await session.post(self.token_url, json=payload)
        try:
            resp.raise_for_status()
        except ClientResponseError as err:
            kwargs: dict[str, Any] = {
                "request_info": err.request_info,
                "history": err.history,
                "status": err.status,
                "message": err.message,
                "headers": err.headers,
                "domain": self.domain,
            }
            if err.status == HTTPStatus.TOO_MANY_REQUESTS or err.status >= 500:
                raise OAuth2TokenRequestTransientError(**kwargs) from err
            raise OAuth2TokenRequestReauthError(**kwargs) from err
        return cast(dict[str, Any], await resp.json(content_type=None))


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> SolarEdgeOAuth2Implementation:
    """Return the SolarEdge implementation for a stored credential."""
    return SolarEdgeOAuth2Implementation(
        hass,
        auth_domain,
        credential,
        AuthorizationServer(authorize_url=OAUTH2_AUTHORIZE, token_url=OAUTH2_TOKEN),
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> dict[str, str]:
    """Links shown in the Add Application Credentials dialog."""
    return {
        "developer_console": "https://developer.solaredge.com",
        "self_access_guide": (
            "https://api-docs.solaredge.com/docs/developer-platform/"
            "df8kx5j4z9vi0-homeowner-and-self-access-guide"
        ),
        "redirect_url": "https://my.home-assistant.io/redirect/oauth",
    }
