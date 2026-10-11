"""Binary sensors for the pumps, fan, flame and alarm icons on the dashboard."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    SECTION_BOILER_1,
    SECTION_BOILER_2,
    SECTION_BUFFER_1,
    SECTION_BUFFER_2,
    SECTION_DHW,
    SECTION_HC_1,
    SECTION_HC_2,
    SECTION_SOLAR,
)
from .coordinator import ThematronicConfigEntry, ThematronicCoordinator
from .entity import ThematronicEntity
from .parser import Signal, flag

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class ThematronicBinaryDescription(BinarySensorEntityDescription):
    """Describes one on/off icon on the dashboard."""

    section: str
    value_fn: Callable[[dict[str, Signal]], bool | None]


def _flag(
    key: str,
    signal: str,
    section: str,
    device_class: BinarySensorDeviceClass,
) -> ThematronicBinaryDescription:
    return ThematronicBinaryDescription(
        key=key,
        translation_key=key,
        section=section,
        device_class=device_class,
        value_fn=lambda s, _k=signal: flag(s, _k),
    )


def _stb_tripped(signals: dict[str, Signal]) -> bool | None:
    # The page highlights "STB" when s_o_hav_term is false (safety limiter open).
    ok = flag(signals, "s_o_hav_term")
    return None if ok is None else not ok


RUNNING = BinarySensorDeviceClass.RUNNING
HEAT = BinarySensorDeviceClass.HEAT
PROBLEM = BinarySensorDeviceClass.PROBLEM

BINARY_SENSORS: tuple[ThematronicBinaryDescription, ...] = (
    _flag("boiler_fan", "s_o_ko_vent", SECTION_BOILER_1, RUNNING),
    _flag("boiler_pump", "s_o_ko_cerp", SECTION_BOILER_1, RUNNING),
    _flag("boiler_flame", "s_o_z1_hori", SECTION_BOILER_1, HEAT),
    _flag("boiler_fault", "s_o_zd1_porucha", SECTION_BOILER_1, PROBLEM),
    _flag("boiler_deactivated", "s_o_zd_deaktivovan", SECTION_BOILER_1, PROBLEM),
    ThematronicBinaryDescription(
        key="safety_limiter",
        translation_key="safety_limiter",
        section=SECTION_BOILER_1,
        device_class=PROBLEM,
        value_fn=_stb_tripped,
    ),
    _flag("boiler_2_flame", "s_o_zdroj2_top", SECTION_BOILER_2, HEAT),
    _flag("hc1_pump", "s_o_zona_top", SECTION_HC_1, RUNNING),
    _flag("hc2_pump", "s_o_zona2_top", SECTION_HC_2, RUNNING),
    _flag("buffer1_transfer_pump", "s_o_cerp_r1", SECTION_BUFFER_1, RUNNING),
    _flag("buffer2_transfer_pump", "s_o_cerp_r2", SECTION_BUFFER_2, RUNNING),
    _flag("dhw_pump", "s_o_tuv_top", SECTION_DHW, RUNNING),
    _flag("solar_pump", "s_o_re_slar", SECTION_SOLAR, RUNNING),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThematronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        ThematronicBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class ThematronicBinarySensor(ThematronicEntity, BinarySensorEntity):
    """An on/off state from the dashboard."""

    entity_description: ThematronicBinaryDescription

    def __init__(
        self,
        coordinator: ThematronicCoordinator,
        description: ThematronicBinaryDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, description, description.section)

    @property
    def is_on(self) -> bool | None:
        """Current state."""
        return self.entity_description.value_fn(self.coordinator.data)
