"""Support for monitoring the LinkStation client."""
from __future__ import annotations
from . import LinkStationDataCoordinator

from datetime import timedelta
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
import logging
import sys
from typing import Any

from linkstation import LinkStation
import voluptuous as vol

from .const import (
    ATTR_DISK_CAPACITY,
    ATTR_DISK_UNIT_NAME,
    ATTR_DISK_USED,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LINKSTATION_DISK_STATUS_NORMAL,
    LINKSTATION_STATUS_ATTR_NAME,
    SENSOR_KEYS,
    SENSOR_TYPES,
)
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DATA_GIGABYTES,
    PERCENTAGE,
)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL,
            default=timedelta(minutes=DEFAULT_UPDATE_INTERVAL),
        ): cv.positive_time_period,
        vol.Optional(CONF_DISKS, default=[]): vol.All(),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_MONITORED_VARIABLES, default=[]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_KEYS)]
        ),
    }
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add LinkStation entities from a config_entry."""
    name: str = entry.data[CONF_NAME]

    coordinator: LinkStationDataCoordinator = hass.data[DOMAIN]

    sensors: list[LinkStationSensorEntity] = []
    if coordinator.disks:
        for disk in coordinator.disks:
            for description in SENSOR_TYPES:
                sensors.append(
                    LinkStationSensorEntity(coordinator, description, name, disk)
                )

    async_add_entities(sensors)

class LinkStationSensorEntity(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Representation of a LinkStation sensor."""

    coordinator: LinkStationDataCoordinator

    def __init__(
        self,
        coordinator: LinkStationDataCoordinator,
        description: SensorEntityDescription,
        linkstation_name: str,
        disk_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.disk_name = disk_name
        self.linkstation_name = linkstation_name

        self._attr_name = f"{linkstation_name} {disk_name} {description.name}"
        self._attrs: dict[str, Any] = {}

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._attr_native_value = state.state

        @callback
        def update() -> None:
            """Update state."""
            self._update_state()
            self.async_write_ha_state()

        self.async_on_remove(self.coordinator.async_add_listener(update))
        self._update_state()

    def _update_state(self):
        """Update sensors state."""
        if self.coordinator.data:

            if self.entity_description.key == LINKSTATION_STATUS_ATTR_NAME:
                if self.is_disk_ready_status(
                    self.coordinator.data[self.disk_name]["status"]
                ):
                    self._attr_native_value = LINKSTATION_DISK_STATUS_NORMAL
                else:
                    self._attr_native_value = self.coordinator.data[self.disk_name][
                        "status"
                    ]
                self._attr_icon = "mdi:harddisk"
            elif (
                self.entity_description.key == "disk_used_pct"
                and self.is_disk_ready_status(
                    self.coordinator.data[self.disk_name]["status"]
                )
            ):
                self._attr_native_value = self.coordinator.data[self.disk_name][
                    "disk_used_pct"
                ]
                self._attr_icon = "mdi:gauge"
            elif (
                self.entity_description.key == "disk_free"
                and self.is_disk_ready_status(
                    self.coordinator.data[self.disk_name]["status"]
                )
            ):
                self._attr_native_value = self.coordinator.data[self.disk_name][
                    "disk_free"
                ]
                self._attr_icon = "mdi:folder-outline"
            else:
                self._attr_available = False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if (
            self.coordinator.data
            and self.coordinator.data[self.disk_name]
            and self.is_disk_ready_status(
                self.coordinator.data[self.disk_name]["status"]
            )
        ):
            self._attrs.update(
                {
                    ATTR_DISK_CAPACITY: self.coordinator.data[self.disk_name][
                        "disk_capacity"
                    ],
                    ATTR_DISK_USED: self.coordinator.data[self.disk_name]["disk_used"],
                    ATTR_DISK_UNIT_NAME: self.coordinator.data[self.disk_name][
                        "disk_unit_name"
                    ],
                }
            )

        return self._attrs

    def is_disk_ready_status(self, status: str) -> bool:
        """Check if disk status is normal."""
        if status is not None and (
            status.startswith(LINKSTATION_DISK_STATUS_NORMAL) or status == ""
        ):
            return True
        else:
            return False
