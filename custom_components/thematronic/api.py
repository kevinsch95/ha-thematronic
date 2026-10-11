"""Client for the Thematronic JBR-1 web portal (jbr1.thematronic.cz).

The portal has no public API. The dashboard is an AngularJS page that, after
a normal form login, calls a ServiceStack JSON API with the session cookie:

* POST /api/json/reply/DeviceSignalReload {"DeviceID": n} – ask the portal to
  refresh values from the controller (returns 204)
* POST /api/json/reply/DeviceSignal {"DeviceID": n} – list of all signals
* GET  /api/auth – current session, 401 when not signed in

This client does the same, read-only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import BASE_URL, LANGUAGE, RELOAD_SETTLE_SECONDS
from .parser import Signal, extract_device_ids, extract_login_token, parse_signals

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)
_JSON_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


class ThematronicError(Exception):
    """Base error."""


class ThematronicAuthError(ThematronicError):
    """Wrong e-mail/password or the session could not be established."""


class ThematronicConnectionError(ThematronicError):
    """Portal unreachable or returned something unexpected."""


class ThematronicApi:
    """Read-only client for one portal account."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        device_id: int | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        """Store credentials; `session` should have its own cookie jar."""
        self._session = session
        self._username = username
        self._password = password
        self._base = base_url.rstrip("/")
        self.device_id = device_id
        self._logged_in = False
        self._login_lock = asyncio.Lock()

    async def login(self) -> None:
        """Sign in through the portal's login form and find the controller id."""
        sign_in_url = f"{self._base}/{LANGUAGE}/sign/in/"
        try:
            async with self._session.get(sign_in_url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                html = await resp.text()
            token = extract_login_token(html)
            if token is None:
                raise ThematronicConnectionError("Login form token not found")

            form = {
                "_token_": token,
                "username": self._username,
                "password": self._password,
                "send": "Einloggen",
                "_do": "signInForm-submit",
            }
            async with self._session.post(
                sign_in_url, data=form, timeout=_TIMEOUT, allow_redirects=True
            ) as resp:
                resp.raise_for_status()
                dashboard_html = await resp.text()
                landed_on = str(resp.url)

            if not await self._session_valid():
                raise ThematronicAuthError("Invalid e-mail or password")

            if self.device_id is None:
                if "/sign/in" in landed_on:
                    async with self._session.get(
                        f"{self._base}/{LANGUAGE}/", timeout=_TIMEOUT
                    ) as resp:
                        resp.raise_for_status()
                        dashboard_html = await resp.text()
                ids = extract_device_ids(dashboard_html)
                if not ids:
                    raise ThematronicConnectionError(
                        "Signed in, but no controller (deviceid) found on the dashboard"
                    )
                if len(ids) > 1:
                    _LOGGER.info("Several controllers found %s, using %s", ids, ids[0])
                self.device_id = ids[0]
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ThematronicConnectionError(f"Cannot reach portal: {err}") from err

        self._logged_in = True
        _LOGGER.debug("Signed in to Thematronic portal, controller %s", self.device_id)

    async def _session_valid(self) -> bool:
        """Return True when the ServiceStack session cookie is authenticated."""
        async with self._session.get(
            f"{self._base}/api/auth", headers=_JSON_HEADERS, timeout=_TIMEOUT
        ) as resp:
            if resp.status in (401, 403):
                return False
            resp.raise_for_status()
            try:
                data = await resp.json(content_type=None)
            except ValueError:
                return False
        return isinstance(data, dict) and bool(data.get("UserId"))

    async def _post(self, endpoint: str) -> Any:
        """POST {"DeviceID": …} to an API endpoint, return parsed JSON or None."""
        async with self._session.post(
            f"{self._base}/api/json/reply/{endpoint}",
            json={"DeviceID": self.device_id},
            headers=_JSON_HEADERS,
            timeout=_TIMEOUT,
        ) as resp:
            if resp.status in (401, 403):
                raise _SessionExpired
            if "text/html" in resp.headers.get("Content-Type", ""):
                # Redirected to the login page.
                raise _SessionExpired
            resp.raise_for_status()
            if resp.status == 204:
                return None
            try:
                return await resp.json(content_type=None)
            except ValueError as err:
                raise ThematronicConnectionError(f"Invalid JSON from {endpoint}") from err

    async def _ensure_login(self, force: bool = False) -> None:
        async with self._login_lock:
            if force or not self._logged_in:
                self._logged_in = False
                await self.login()

    async def fetch_signals(self) -> dict[str, Signal]:
        """Refresh and return all controller values, signing in as needed."""
        await self._ensure_login()
        for attempt in (1, 2):
            try:
                await self._post("DeviceSignalReload")
                await asyncio.sleep(RELOAD_SETTLE_SECONDS)
                payload = await self._post("DeviceSignal")
                return parse_signals(payload)
            except _SessionExpired:
                if attempt == 2:
                    raise ThematronicAuthError("Session rejected after re-login") from None
                _LOGGER.debug("Thematronic session expired, signing in again")
                await self._ensure_login(force=True)
            except ValueError as err:
                raise ThematronicConnectionError(str(err)) from err
            except (aiohttp.ClientError, TimeoutError) as err:
                raise ThematronicConnectionError(f"Cannot reach portal: {err}") from err
        raise ThematronicConnectionError("Unreachable")  # pragma: no cover


class _SessionExpired(Exception):
    """Internal: the API answered as if we were signed out."""
