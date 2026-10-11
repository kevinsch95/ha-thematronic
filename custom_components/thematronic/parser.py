"""Pure parsing helpers for Thematronic portal data.

Kept free of Home Assistant and aiohttp imports so it can be unit-tested
on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .const import (
    BAD_STATES,
    NO_VALUE,
    SECTION_BOILER_1,
    SECTION_BOILER_2,
    SECTION_BUFFER_1,
    SECTION_BUFFER_2,
    SECTION_DHW,
    SECTION_HC_1,
    SECTION_HC_2,
    SECTION_MODE,
    SECTION_OUTDOOR,
    SECTION_SOLAR,
    SENTINEL_TEMP,
)

_TOKEN_RE = re.compile(r"<input\b[^>]*\bname=[\"']_token_[\"'][^>]*>", re.IGNORECASE)
_VALUE_RE = re.compile(r"\bvalue=[\"']([^\"']*)[\"']", re.IGNORECASE)
_DEVICE_ID_RE = re.compile(r"deviceid\s*=\s*(\d+)", re.IGNORECASE)
_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


@dataclass(frozen=True, slots=True)
class Signal:
    """One value as returned by the DeviceSignal endpoint."""

    name: str  # "Nazev"
    value: Any  # "Hodnota" – raw value (number, bool, string)
    state: str  # "Stav" – ok / none / nezname / nepripojeno / chyba / ...
    formatted: str  # "HodnotaF" – what the web page shows, e.g. "65,0 °C"

    @property
    def is_missing(self) -> bool:
        """Return True when the web page would show '---' for this value."""
        return self.state in BAD_STATES or self.formatted.strip() == NO_VALUE


def parse_signals(payload: Any) -> dict[str, Signal]:
    """Turn the DeviceSignal JSON list into a dict keyed by signal name."""
    if not isinstance(payload, list):
        raise ValueError(f"Unexpected DeviceSignal payload: {type(payload).__name__}")
    signals: dict[str, Signal] = {}
    for item in payload:
        if not isinstance(item, dict) or "Nazev" not in item:
            continue
        name = str(item["Nazev"])
        signals[name] = Signal(
            name=name,
            value=item.get("Hodnota"),
            state=str(item.get("Stav") or ""),
            formatted=str(item.get("HodnotaF") or ""),
        )
    return signals


def extract_login_token(html: str) -> str | None:
    """Return the Nette CSRF token (_token_) from the sign-in page."""
    tag = _TOKEN_RE.search(html)
    if not tag:
        return None
    value = _VALUE_RE.search(tag.group(0))
    return value.group(1) if value else None


def extract_device_ids(html: str) -> list[int]:
    """Return the controller ids found in the dashboard (ng-init="deviceid=…")."""
    seen: list[int] = []
    for match in _DEVICE_ID_RE.finditer(html):
        device_id = int(match.group(1))
        if device_id not in seen:
            seen.append(device_id)
    return seen


def iso_duration_to_hours(value: Any) -> float | None:
    """Convert an ISO-8601 duration such as 'PT1H30M' or 'P2DT3H' to hours."""
    if not isinstance(value, str):
        return None
    match = _DURATION_RE.match(value.strip())
    if not match or value.strip() in ("P", "PT"):
        return None
    parts = {k: float(v) if v else 0.0 for k, v in match.groupdict().items()}
    hours = (
        parts["days"] * 24
        + parts["hours"]
        + parts["minutes"] / 60
        + parts["seconds"] / 3600
    )
    return round(hours, 3)


def number(signals: dict[str, Signal], key: str) -> float | None:
    """Numeric value of a signal, or None when the web page shows '---'."""
    signal = signals.get(key)
    if signal is None or signal.is_missing:
        return None
    value = signal.value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value == SENTINEL_TEMP:
        return None
    return float(value)


def flag(signals: dict[str, Signal], key: str) -> bool | None:
    """Boolean value of a signal (pumps, fan, flame, alarms)."""
    signal = signals.get(key)
    if signal is None:
        return None
    value = signal.value
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return None


def schema_code(signals: dict[str, Signal]) -> str:
    """Return the 3-digit hydraulic schema code (s_o_schema), e.g. '421'."""
    signal = signals.get("s_o_schema")
    if signal is None:
        return ""
    return str(signal.formatted or signal.value or "").strip()


def configured_sections(schema: str) -> set[str]:
    """Which dashboard boxes the controller's hydraulic schema actually uses.

    Mirrors the logic in the portal's DashboardCtrl JavaScript. The web page
    still draws every box; we use this only to decide which entities are
    enabled by default.
    """
    sections = {SECTION_BOILER_1, SECTION_OUTDOOR, SECTION_MODE, SECTION_HC_1}
    if len(schema) < 3:
        # Unknown schema: treat everything as in use.
        return sections | {
            SECTION_BOILER_2,
            SECTION_HC_2,
            SECTION_BUFFER_1,
            SECTION_BUFFER_2,
            SECTION_DHW,
            SECTION_SOLAR,
        }
    first, second, third = schema[0], schema[1], schema[2]
    if first in "5678":
        sections.add(SECTION_BOILER_2)
    sections |= {
        "2": {SECTION_HC_2},
        "3": {SECTION_DHW},
        "4": {SECTION_HC_2, SECTION_DHW},
        "5": {SECTION_DHW, SECTION_SOLAR},
        "6": {SECTION_HC_2, SECTION_DHW, SECTION_SOLAR},
    }.get(second, set())
    sections |= {
        "1": {SECTION_BUFFER_1},
        "2": {SECTION_BUFFER_1},
        "3": {SECTION_BUFFER_1, SECTION_BUFFER_2},
        "4": {SECTION_BUFFER_1, SECTION_BUFFER_2},
        "5": {SECTION_BUFFER_1, SECTION_SOLAR},
        "6": {SECTION_BUFFER_1, SECTION_SOLAR},
        "7": {SECTION_BUFFER_1, SECTION_BUFFER_2, SECTION_SOLAR},
        "8": {SECTION_BUFFER_1, SECTION_BUFFER_2, SECTION_SOLAR},
    }.get(third, set())
    return sections


# --- Values that need translating the way the web page does -------------

ROOM_TARGET_PROGRAM = {"ku_komfort": "comfort", "ku_utlum": "reduced", "ku_stop": "stop"}
ROOM_TARGET_THERMOSTAT = {
    "term_komfort": "comfort",
    "term_stop": "stop",
    "term_auto": "auto",
}
ROOM_TARGET_OPTIONS = ["comfort", "reduced", "stop", "auto", "sensor"]


def room_target_mode(signals: dict[str, Signal], zone: int) -> str | None:
    """'Raum Temp SOLL' tile: comfort / reduced / stop / auto / sensor."""
    mode = signals.get(f"dev_rezim_z{zone}")
    setpoint = signals.get(f"dev_set_z{zone}")
    if mode is None or setpoint is None:
        return None
    if mode.formatted == "program":
        return ROOM_TARGET_PROGRAM.get(setpoint.formatted)
    if mode.formatted == "termostat":
        return ROOM_TARGET_THERMOSTAT.get(setpoint.formatted)
    if mode.formatted == "cidlo":
        return "sensor"
    return None


def room_target_temperature(signals: dict[str, Signal], zone: int) -> float | None:
    """Room set-point in °C implied by the current mode, when there is one."""
    mode = signals.get(f"dev_rezim_z{zone}")
    setpoint = signals.get(f"dev_set_z{zone}")
    if mode is None or setpoint is None:
        return None
    if mode.formatted == "cidlo":
        return number(signals, f"dev_set_z{zone}")
    target = room_target_mode(signals, zone)
    if target == "comfort":
        return number(signals, f"dev_z{zone}_komfort")
    if target == "reduced":
        return number(signals, f"dev_z{zone}_utlum")
    return None


DHW_TARGET_OPTIONS = ["stop", "eco", "comfort"]


def dhw_target(signals: dict[str, Signal]) -> str | None:
    """'WW Soll' tile: stop / eco / comfort (the page shows STOP/EKO/KOMFORT)."""
    signal = signals.get("s_t_tuv_poz")
    if signal is None or isinstance(signal.value, bool):
        return None
    try:
        level = int(signal.value)
    except (TypeError, ValueError):
        return None
    return {0: "stop", 1: "eco", 2: "comfort"}.get(level)


def dhw_target_temperature(signals: dict[str, Signal]) -> float | None:
    """Explicit hot-water set-point when the controller reports one (> 2)."""
    value = number(signals, "s_t_tuv_poz")
    if value is None or value <= 2:
        return None
    return value


def blocking_difference(signals: dict[str, Signal], key: str) -> float | None:
    """'Sperrdifferenz' tile; the page shows '---' while it is zero."""
    value = number(signals, key)
    if value is None or value <= 0:
        return None
    return value


def season(signals: dict[str, Signal]) -> str | None:
    """'Modus' tile: summer or winter."""
    summer = flag(signals, "s_o_leto")
    if summer is None:
        return None
    return "summer" if summer else "winter"
