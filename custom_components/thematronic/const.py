"""Constants for the Thematronic JBR-1 integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "thematronic"

BASE_URL: Final = "https://jbr1.thematronic.cz"
LANGUAGE: Final = "de"

CONF_DEVICE_ID: Final = "device_id"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_RAW_SIGNALS: Final = "raw_signals"

DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
MIN_SCAN_INTERVAL: Final = 10  # the web dashboard itself refreshes every 10 s

# Seconds to wait between asking the portal to refresh values from the
# controller (DeviceSignalReload) and reading them (DeviceSignal). The web
# dashboard waits 1 s.
RELOAD_SETTLE_SECONDS: Final = 1.5

MANUFACTURER: Final = "Thematronic s.r.o."
MODEL: Final = "JBR-1"

# Signal "Stav" (state) values meaning the sensor is absent or faulty.
BAD_STATES: Final = frozenset({"nepripojeno", "chyba"})  # not connected / error
NO_VALUE: Final = "---"
SENTINEL_TEMP: Final = -50.1

# Dashboard sections, matching the boxes on the web page.
SECTION_BOILER_1: Final = "boiler_1"
SECTION_BOILER_2: Final = "boiler_2"
SECTION_OUTDOOR: Final = "outdoor"
SECTION_MODE: Final = "mode"
SECTION_HC_1: Final = "heating_circuit_1"
SECTION_HC_2: Final = "heating_circuit_2"
SECTION_BUFFER_1: Final = "buffer_1"
SECTION_BUFFER_2: Final = "buffer_2"
SECTION_DHW: Final = "hot_water"
SECTION_SOLAR: Final = "solar"
