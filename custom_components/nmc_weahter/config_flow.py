from __future__ import annotations
import logging
import requests
import json
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    CONF_PROVINCE,
    CONF_STATION_CODE,
    CONF_IMAGES,
    CONF_IMAGE_RADAR,
    CONF_IMAGE_PRECIPITATION24,
    CONF_IMAGE_MAX_TEMPERATURE24,
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)

IMAGES = {
    CONF_IMAGE_RADAR: "雷达图",
    CONF_IMAGE_PRECIPITATION24: "24小时降雨量预报图",
    CONF_IMAGE_MAX_TEMPERATURE24: "24小时最高气温预报图"
}


class NMCWeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Met Eireann component."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            self._province = user_input[CONF_PROVINCE]
            return await self.async_step_city()

        try:
            request_provinces = await self.hass.async_add_executor_job(
                requests.get, "http://www.nmc.cn/rest/province/all"
            )
            self._provinces = {p['code']: p['name']
                               for p in json.loads(request_provinces.content)}
        except Exception:
            _LOGGER.exception("fetch provinces failed")
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_PROVINCE): vol.In(self._provinces)
                    }
            ),
            errors=errors,
        )

    async def async_step_city(self, user_input=None):
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_NAME) is None:
                user_input[CONF_NAME] = f"{user_input[CONF_STATION_CODE]}"
                for city in self._cities:
                    if city['code'] == user_input[CONF_STATION_CODE]:
                        user_input[CONF_NAME] = f"{city['province']}{city['city']}"
                        break
            self.config = user_input
            return await self.async_setup_station()

        try:
            request_city = await self.hass.async_add_executor_job(
                requests.get, f"http://www.nmc.cn/rest/province/{self._province}"
            )
            self._cities = json.loads(request_city.content)
            stations = {city['code']: city['city'] for city in self._cities}
        except Exception:
            _LOGGER.exception("fetch cities failed")
            return await self.async_step_manual()

        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_STATION_CODE): vol.In(stations),
                        vol.Optional(CONF_NAME): str,
                        vol.Optional(CONF_IMAGES): cv.multi_select(IMAGES)
                    }
            ),
            errors=errors,
        )

    async def async_step_manual(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            if user_input.get(CONF_NAME) is None:
                user_input[CONF_NAME] = f"{user_input[CONF_STATION_CODE]}"
            self.config = user_input
            return await self.async_setup_station()

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_STATION_CODE,
                        ): str,
                        vol.Optional(CONF_NAME): str,
                        vol.Optional(CONF_IMAGES): cv.multi_select(IMAGES)
                    }
            ),
            errors=errors,
        )

    async def async_setup_station(self):
        name = self.config.get(CONF_NAME)
        await self.async_set_unique_id(
            f"{self.config.get(CONF_STATION_CODE)}"
        )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=name, data=self.config)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.config = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            self.config.update(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=self.config
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=self.config)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_IMAGES, default=self.config.get(CONF_IMAGES, [])): cv.multi_select(IMAGES)
                    }
            ),
        )
