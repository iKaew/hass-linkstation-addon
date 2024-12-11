"""Integration for Buffalo LinkStation NAS."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Dict

import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from linkstation import LinkStation

from .const import (
    ATTR_DISK_CAPACITY,
    ATTR_DISK_UNIT_NAME,
    ATTR_DISK_USED,
    CONF_MANUAL,
    DEFAULT_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LINKSTATION_DISK_STATUS_NORMAL,
    LINKSTATION_REFRESH_SERVICE,
    LINKSTATION_STATUS_ATTR_NAME,
    PLATFORMS,
    SENSOR_KEYS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        {
            DOMAIN: vol.Schema(
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
        },
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Import integration from config."""
    conf = config.get(DOMAIN)

    if conf is None:
        return True

    configured_hosts = [
        entry.options.get("host") for entry in hass.config_entries.async_entries(DOMAIN)
    ]

    host = conf.get(CONF_HOST)

    if host is None or host in configured_hosts:
        return True

    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=config[DOMAIN]
            )
        )

    return True  # await async_setup_entry(hass, config[DOMAIN])


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up the LinkStation component."""
    coordinator = LinkStationDataCoordinator(hass, config_entry)
    await coordinator.async_setup()

    async def _enable_scheduled_linkstation_dataretriever(*_):
        """Activate the data update coordinator."""
        coordinator.update_interval = timedelta(
            minutes=config_entry.options.get(
                CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )
        )
        await coordinator.async_refresh()

    if not config_entry.options.get(CONF_MANUAL, False):
        if hass.state == CoreState.running:
            await _enable_scheduled_linkstation_dataretriever()
        else:
            # Running a getting data during startup can prevent
            # integrations from being able to setup because it
            # can saturate the network interface.
            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _enable_scheduled_linkstation_dataretriever
            )

    hass.data[DOMAIN] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload LinkStation Entry from config_entry."""
    hass.services.async_remove(DOMAIN, LINKSTATION_REFRESH_SERVICE)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok


class LinkStationDataCoordinator(DataUpdateCoordinator):
    """Get the latest data from LinkStation."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the data object."""
        self.hass = hass
        super().__init__(
            self.hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self.async_update,
        )
        self.api: LinkStation | None = None
        self.config_entry: ConfigEntry = config_entry
        self.disks = None

    async def async_setup(self) -> None:
        """Set up LinkStation Coordinator."""

        await self.async_set_options()

        if self.config_entry.options.get(CONF_HOST):
            host = self.config_entry.options.get(CONF_HOST)
            username = self.config_entry.options.get(CONF_USERNAME)
            password = self.config_entry.options.get(CONF_PASSWORD)

            try:
                self.api = LinkStation(username, password, host)
                self.disks = await self.api.get_all_disks_async()
            except Exception:
                _LOGGER.error("Error initiate linkstation", exc_info=True)
                raise ConfigEntryNotReady

        else:
            raise ConfigEntryNotReady

        async def request_update(call):
            """Request update."""
            await self.async_request_refresh()

        self.hass.services.async_register(
            DOMAIN, LINKSTATION_REFRESH_SERVICE, request_update
        )

        self.config_entry.async_on_unload(
            self.config_entry.add_update_listener(options_updated_listener)
        )

    async def async_update(self) -> dict[str, Any]:
        """Update LinkStation data."""

        result = {}

        try:
            # name = await self.api.get_linkstation_name_async()
            await self.api.get_disks_info_with_cache_async()
            disks = await self.api.get_all_disks_async()
            await self.api.close()

            for disk in disks:
                diskStatus = self.api.get_disk_status(disk)

                if (
                    diskStatus.startswith(LINKSTATION_DISK_STATUS_NORMAL)
                    or diskStatus == ""
                ):
                    diskInfo = {
                        "status": self.api.get_disk_status(disk),
                        "disk_free": self.api.get_disk_free(disk),
                        "disk_used_pct": self.api.get_disk_pct_used(disk),
                        "disk_capacity": self.api.get_disk_capacity(disk),
                        "disk_used": self.api.get_disk_amount_used(disk),
                        "disk_unit_name": self.api.get_disk_unit_name(disk),
                    }
                else:
                    diskInfo = {
                        "status": diskStatus,
                    }

                result[disk] = diskInfo

        except Exception as err:
            raise UpdateFailed(err) from err

        return result

    async def async_set_options(self):
        """Set options for entry."""
        if not self.config_entry.options:
            data = {**self.config_entry.data}
            options = {
                CONF_SCAN_INTERVAL: data.pop(
                    CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
                CONF_MANUAL: data.pop(CONF_MANUAL, False),
                CONF_HOST: data.pop(CONF_HOST, ""),
                CONF_USERNAME: data.pop(CONF_USERNAME, ""),
                CONF_PASSWORD: data.pop(CONF_PASSWORD, ""),
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=data, options=options
            )


async def options_updated_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    hass.data[DOMAIN].update_interval = timedelta(
        minutes=entry.options[CONF_SCAN_INTERVAL]
    )
    await hass.data[DOMAIN].async_request_refresh()
