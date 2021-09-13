"""Support for monitoring the LinkStation client."""
from __future__ import annotations

from datetime import timedelta
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
    LINKSTATION_DISK_STATUS_NORMAL,
    LINKSTATION_STATUS_ATTR_NAME,
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

_LOGGER = logging.getLogger(__name__)
_THROTTLED_REFRESH = None

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=LINKSTATION_STATUS_ATTR_NAME,
        name="status",
    ),
    SensorEntityDescription(
        key="disk_free",
        name="available",
        native_unit_of_measurement=DATA_GIGABYTES,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
    SensorEntityDescription(
        key="disk_used_pct",
        name="used (%)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=STATE_CLASS_MEASUREMENT,
    ),
)

SENSOR_KEYS: list[str] = [desc.key for desc in SENSOR_TYPES]

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


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Linkstation sensors."""
    name = config[CONF_NAME]
    host = config[CONF_HOST]
    username = config[CONF_USERNAME]
    password = config[CONF_PASSWORD]
    disks = config[CONF_DISKS]

    linkstation_api = LinkStation(username, password, host)

    if not disks:
        _LOGGER.debug("No disks configuration, getting all disks from server.")
        try:
            disks = await linkstation_api.get_all_disks_async()
        except Exception:
            _LOGGER.error("Connection to LinkStation failed", exc_info=True)
            raise PlatformNotReady

    if name == DEFAULT_NAME:
        _LOGGER.debug("No LinkStation Name configuration, gettine name from server.")
        try:
            name = await linkstation_api.get_linkstation_name_async()
        except Exception:
            _LOGGER.error("Connection to LinkStation failed", exc_info=True)
            raise PlatformNotReady

    monitored_variables = config[CONF_MONITORED_VARIABLES]
    entities = []

    for disk in disks:
        for description in SENSOR_TYPES:
            if description.key in monitored_variables:
                entities.append(
                    LinkStationSensor(linkstation_api, name, description, disk)
                )

    async_add_entities(entities)


class LinkStationSensor(SensorEntity):
    """Representation of a LinkStation sensor."""

    def __init__(
        self,
        linkstation_client: LinkStation,
        linkstation_name,
        description: SensorEntityDescription,
        disk_name: str,
    ):
        """Initialize the sensor."""
        self.entity_description = description
        self.client = linkstation_client
        self.disk_status = None
        self.disk = disk_name
        self.disk_data = None
        self._attr_name = f"{linkstation_name} {disk_name} {description.name}"
        self._attrs: dict[str, Any] = {}

    async def async_update(self):
        """Get the latest data from LinkStation and updates the state."""
        _LOGGER.debug("Update data for %s", self._attr_name)

        try:
            self.disk_data = await self.client.get_disks_info_with_cache_async()
            self.disk_status = await self.client.get_disk_status_async(self.disk)
            self._attr_available = True
            await self.client.close()
        except Exception:
            _LOGGER.error("Connection to LinkStation Failed", exc_info=True)
            return

        sensor_type = self.entity_description.key
        if sensor_type == LINKSTATION_STATUS_ATTR_NAME:

            if self.is_disk_ready():
                self._attr_native_value = LINKSTATION_DISK_STATUS_NORMAL
            else:
                self._attr_native_value = self.disk_status
            self._attr_icon = "mdi:harddisk"
            return

        if self.is_disk_ready():
            if sensor_type == "disk_used_pct":
                self._attr_native_value = self.client.get_disk_pct_used(self.disk)
                self._attr_icon = "mdi:gauge"

            elif sensor_type == "disk_free":

                self._attr_native_value = self.client.get_disk_free(self.disk)
                self._attr_icon = "mdi:folder-outline"
        else:
            self._attr_available = False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.is_disk_ready():

            disk_capacity =  self.client.get_disk_capacity(self.disk)
            if (disk_capacity is not None):
                self._attrs.update(
                {
                    ATTR_DISK_CAPACITY: self.client.get_disk_capacity(self.disk),
                }
            )

            disk_used = self.client.get_disk_amount_used(self.disk)
            if (disk_used is not None):
                self._attrs.update(
                    {
                        ATTR_DISK_USED: self.client.get_disk_amount_used(self.disk),
                    }
                )
            disk_unit_name = self.client.get_disk_unit_name(self.disk)
            if (disk_unit_name is not None):
                self._attrs.update(
                    {
                        ATTR_DISK_UNIT_NAME: self.client.get_disk_unit_name(self.disk),
                    }
                )

        return self._attrs

    def is_disk_ready(self) -> bool:
        """Check if disk status is normal."""
        if self.disk_status is not None and (
            self.disk_status.startswith(LINKSTATION_DISK_STATUS_NORMAL)
            or self.disk_status == ""
        ):
            return True
        else:
            return False
