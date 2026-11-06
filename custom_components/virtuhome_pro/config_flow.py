"""Config flow: nothing to ask. Once HACS has put VirtuHome Pro in and Home Assistant restarted,
VirtuHome starts a discovery flow for it, and it sets itself up there and then."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.typing import DiscoveryInfoType

from .const import CONF_LICENCE_SERVER, CORE_DOMAIN, DEFAULT_LICENCE_SERVER, DOMAIN, OLD_LICENCE_SERVER


class VirtuHomeProConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self._create()
        return self.async_show_form(step_id="user")

    async def async_step_integration_discovery(self, discovery_info: DiscoveryInfoType) -> ConfigFlowResult:
        """Started by VirtuHome once this integration is installed: the user asked for it by installing it."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self._create()

    def _create(self) -> ConfigFlowResult:
        # a licence server set in VirtuHome's options before 0.18 (for testing) stays in use
        options: dict[str, Any] = {}
        for core in self.hass.config_entries.async_entries(CORE_DOMAIN):
            if server := core.options.get(CONF_LICENCE_SERVER):
                options[CONF_LICENCE_SERVER] = server
        return self.async_create_entry(title="VirtuHome Pro", data={}, options=options)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return VirtuHomeProOptionsFlow()


class VirtuHomeProOptionsFlow(OptionsFlow):
    """Advanced: which licence server extensions come from (for testing a local one)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        current = self.config_entry.options.get(CONF_LICENCE_SERVER) or DEFAULT_LICENCE_SERVER
        # the first address, saved here before there was our own: both are tried anyway
        if current.rstrip("/") == OLD_LICENCE_SERVER:
            current = DEFAULT_LICENCE_SERVER
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({vol.Required(CONF_LICENCE_SERVER, default=current): str}),
        )
