"""Config flow for LinkStation Client."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_DISKS,
    CONF_HOST,
    CONF_MONITORED_VARIABLES,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from linkstation import LinkStation

from .const import DEFAULT_NAME, DEFAULT_UPDATE_INTERVAL, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def verify_api(hass, entry):
    """Verify LinkStation client."""
    host = entry[CONF_HOST]
    username = entry.get(CONF_USERNAME)
    password = entry.get(CONF_PASSWORD)

    api = LinkStation(username, password, host)
    await api.connect_async()
    await api.close()


class LinkStationFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle LinkStation config flow."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return LinkStationOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            for entry in self._async_current_entries():
                if entry.data["name"] == user_input["name"]:
                    return self.async_abort(reason="already_configured")
            try:
                await verify_api(self.hass, user_input)

            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(self, import_config):
        """Import from LinkStation client config."""
        import_config[CONF_SCAN_INTERVAL] = import_config[
            CONF_SCAN_INTERVAL
        ].total_seconds()
        return await self.async_step_user(user_input=import_config)


class LinkStationOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle LinkStation client options."""

    def __init__(self, config_entry):
        """Initialize LinkStation options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the LinkStation options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Required(
                CONF_HOST, default=self.config_entry.options.get(CONF_HOST, "")
            ): str,
            vol.Required(
                CONF_USERNAME, default=self.config_entry.options.get(CONF_USERNAME, "")
            ): str,
            vol.Required(
                CONF_PASSWORD, default=self.config_entry.options.get(CONF_PASSWORD, "")
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_UPDATE_INTERVAL
                ),
            ): int,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
