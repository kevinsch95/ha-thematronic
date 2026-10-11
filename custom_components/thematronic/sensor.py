"""Sensors mirroring the tiles on the Thematronic web dashboard."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_RAW_SIGNALS,
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
)
from .coordinator import ThematronicConfigEntry, ThematronicCoordinator
from .entity import ThematronicEntity
from .parser import (
    DHW_TARGET_OPTIONS,
    ROOM_TARGET_OPTIONS,
    Signal,
    blocking_difference,
    dhw_target,
    dhw_target_temperature,
    iso_duration_to_hours,
    number,
    room_target_mode,
    room_target_temperature,
    schema_code,
    season,
)

PARALLEL_UPDATES = 0

Signals = dict[str, Signal]


@dataclass(frozen=True, kw_only=True)
class ThematronicSensorDescription(SensorEntityDescription):
    """Describes one dashboard value."""

    section: str
    value_fn: Callable[[Signals], Any]


def _temp(
    key: str, signal: str, section: str, **kwargs: Any
) -> ThematronicSensorDescription:
    return ThematronicSensorDescription(
        key=key,
        translation_key=key,
        section=section,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda s, _k=signal: number(s, _k),
        **kwargs,
    )


def _blocking(key: str, signal: str, section: str) -> ThematronicSensorDescription:
    return ThematronicSensorDescription(
        key=key,
        translation_key=key,
        section=section,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda s, _k=signal: blocking_difference(s, _k),
    )


def _duration(signal: str) -> Callable[[Signals], float | None]:
    def value(s: Signals) -> float | None:
        sig = s.get(signal)
        return None if sig is None else iso_duration_to_hours(sig.value)

    return value


SENSORS: tuple[ThematronicSensorDescription, ...] = (
    # --- Kessel 1 -------------------------------------------------------
    _temp("flue_gas_temperature", "s_t_spal", SECTION_BOILER_1),
    _temp("boiler_flow_temperature", "s_t_ko_vy", SECTION_BOILER_1),
    _temp("boiler_return_temperature", "s_t_ko_vr", SECTION_BOILER_1),
    ThematronicSensorDescription(
        key="total_burn_time",
        translation_key="total_burn_time",
        section=SECTION_BOILER_1,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=2,
        value_fn=_duration("dev_horeni"),
    ),
    ThematronicSensorDescription(
        key="current_burn_time",
        translation_key="current_burn_time",
        section=SECTION_BOILER_1,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_unit_of_measurement=UnitOfTime.MINUTES,
        suggested_display_precision=0,
        value_fn=_duration("dev_prilozeni"),
    ),
    # --- Kessel 2 -------------------------------------------------------
    _temp("boiler_2_flow_temperature", "s_t_nezamrz", SECTION_BOILER_2),
    # --- Aussen temp / Modus -------------------------------------------
    _temp("outdoor_temperature", "s_t_venku", SECTION_OUTDOOR),
    ThematronicSensorDescription(
        key="season_mode",
        translation_key="season_mode",
        section=SECTION_MODE,
        device_class=SensorDeviceClass.ENUM,
        options=["summer", "winter"],
        value_fn=season,
    ),
    # --- HK 1 ------------------------------------------------------------
    _temp("hc1_room_temperature", "s_t_zona1", SECTION_HC_1),
    ThematronicSensorDescription(
        key="hc1_room_target_mode",
        translation_key="hc1_room_target_mode",
        section=SECTION_HC_1,
        device_class=SensorDeviceClass.ENUM,
        options=ROOM_TARGET_OPTIONS,
        value_fn=lambda s: room_target_mode(s, 1),
    ),
    ThematronicSensorDescription(
        key="hc1_room_target_temperature",
        translation_key="hc1_room_target_temperature",
        section=SECTION_HC_1,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda s: room_target_temperature(s, 1),
    ),
    _temp("hc1_flow_temperature", "s_t_zo1_vy", SECTION_HC_1),
    ThematronicSensorDescription(
        key="hc1_humidity",
        translation_key="hc1_humidity",
        section=SECTION_HC_1,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda s: number(s, "s_o_zo1_vlhkost"),
    ),
    _blocking("hc1_blocking_difference", "s_o_blok_zbyva_z1", SECTION_HC_1),
    # --- HK 2 ------------------------------------------------------------
    _temp("hc2_room_temperature", "s_t_zona2", SECTION_HC_2),
    ThematronicSensorDescription(
        key="hc2_room_target_mode",
        translation_key="hc2_room_target_mode",
        section=SECTION_HC_2,
        device_class=SensorDeviceClass.ENUM,
        options=ROOM_TARGET_OPTIONS,
        value_fn=lambda s: room_target_mode(s, 2),
    ),
    ThematronicSensorDescription(
        key="hc2_room_target_temperature",
        translation_key="hc2_room_target_temperature",
        section=SECTION_HC_2,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda s: room_target_temperature(s, 2),
    ),
    _temp("hc2_flow_temperature", "s_t_zo2_vy", SECTION_HC_2),
    ThematronicSensorDescription(
        key="hc2_humidity",
        translation_key="hc2_humidity",
        section=SECTION_HC_2,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda s: number(s, "s_o_zo2_vlhkost"),
    ),
    _blocking("hc2_blocking_difference", "s_o_blok_zbyva_z2", SECTION_HC_2),
    # --- Puffer 1 / 2 ----------------------------------------------------
    _temp("buffer1_top_temperature", "s_t_akuh", SECTION_BUFFER_1),
    _temp("buffer1_middle_temperature", "s_t_akus", SECTION_BUFFER_1),
    _temp("buffer1_bottom_temperature", "s_t_akud", SECTION_BUFFER_1),
    _temp("buffer2_top_temperature", "s_t_aku2h", SECTION_BUFFER_2),
    _temp("buffer2_middle_temperature", "s_t_aku2s", SECTION_BUFFER_2),
    _temp("buffer2_bottom_temperature", "s_t_aku2d", SECTION_BUFFER_2),
    # --- WW ----------------------------------------------------------------
    _temp("dhw_temperature", "s_t_tuv", SECTION_DHW),
    ThematronicSensorDescription(
        key="dhw_target_mode",
        translation_key="dhw_target_mode",
        section=SECTION_DHW,
        device_class=SensorDeviceClass.ENUM,
        options=DHW_TARGET_OPTIONS,
        value_fn=dhw_target,
    ),
    ThematronicSensorDescription(
        key="dhw_target_temperature",
        translation_key="dhw_target_temperature",
        section=SECTION_DHW,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        value_fn=dhw_target_temperature,
    ),
    _blocking("dhw_blocking_difference", "s_o_blok_zbyva_tuv", SECTION_DHW),
    # --- Solar ---------------------------------------------------------
    _temp("solar_collector_temperature", "s_t_solar", SECTION_SOLAR),
)

SCHEMA_SENSOR = ThematronicSensorDescription(
    key="hydraulic_schema",
    translation_key="hydraulic_schema",
    section=SECTION_BOILER_1,
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=lambda s: schema_code(s) or None,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ThematronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        ThematronicSensor(coordinator, description)
        for description in (*SENSORS, SCHEMA_SENSOR)
    ]
    if entry.options.get(CONF_RAW_SIGNALS, False):
        entities.extend(
            ThematronicRawSignalSensor(coordinator, name)
            for name in sorted(coordinator.data)
        )
    async_add_entities(entities)


class ThematronicSensor(ThematronicEntity, SensorEntity):
    """A value from the dashboard."""

    entity_description: ThematronicSensorDescription

    def __init__(
        self,
        coordinator: ThematronicCoordinator,
        description: ThematronicSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description, description.section)

    @property
    def native_value(self) -> Any:
        """Current value."""
        return self.entity_description.value_fn(self.coordinator.data)


class ThematronicRawSignalSensor(ThematronicEntity, SensorEntity):
    """Any portal signal, unprocessed (opt-in, for advanced users)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ThematronicCoordinator, signal: str) -> None:
        """Initialise the raw sensor."""
        super().__init__(
            coordinator,
            SensorEntityDescription(key=f"raw_{signal}", name=f"Signal {signal}"),
        )
        self._signal = signal

    @property
    def native_value(self) -> str | None:
        """What the web page would print for this signal."""
        sig = self.coordinator.data.get(self._signal)
        if sig is None:
            return None
        return sig.formatted or str(sig.value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Raw value and the portal's status code."""
        sig = self.coordinator.data.get(self._signal)
        if sig is None:
            return {}
        return {"raw_value": sig.value, "status": sig.state}
