from __future__ import annotations
from dataclasses import dataclass

import logging
from homeassistant.components.image import ImageEntity, ImageEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_IMAGES,
    CONF_IMAGE_RADAR,
    CONF_IMAGE_PRECIPITATION24,
    CONF_IMAGE_MAX_TEMPERATURE24,
    CONF_IMAGE_TEMPERATURE_HOURLY,
    DATA_PRECIPITATION24,
    DATA_MAX_TEMPERATURE24,
    DATA_RADAR,
    DATA_TEMPERATURE_HOURLY
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class NMCImageEntityDescription(ImageEntityDescription):
    data_key: str | None = None


CAMERA_TYPE = [
    NMCImageEntityDescription(
        key=CONF_IMAGE_PRECIPITATION24,
        data_key=DATA_PRECIPITATION24,
        name="24h Precipitation",
    ),
    NMCImageEntityDescription(
        key=CONF_IMAGE_MAX_TEMPERATURE24,
        data_key=DATA_MAX_TEMPERATURE24,
        name="24h Max Temperature",
    ),
    NMCImageEntityDescription(
        key=CONF_IMAGE_RADAR,
        data_key=DATA_RADAR,
        name="Radar",
    ),
    NMCImageEntityDescription(
        key=CONF_IMAGE_TEMPERATURE_HOURLY,
        data_key=DATA_TEMPERATURE_HOURLY,
        name="Temperature Hourly",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([NMCImageEntity(hass, coordinator, description)
                        for description in CAMERA_TYPE if description.key in (config_entry.data.get(CONF_IMAGES, []))])


class NMCImageEntity(CoordinatorEntity, ImageEntity):

    def __init__(self, hass, coordinator, description):
        super().__init__(coordinator)
        ImageEntity.__init__(self, hass)

        self.entity_description = description
        self._data_key = description.data_key
        self._attr_unique_id = f"nmc-{coordinator.config_entry.unique_id}-image-{description.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_image_url = self.coordinator.data[self._data_key]["url"]
        self._attr_image_last_updated = self.coordinator.data[self._data_key]["update_time"]

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (data := self.coordinator.data.get(self._data_key)) is None:
            return
        if (data.get("url") != self._attr_image_url or data.get("update_time") != self._attr_image_last_updated):
            self._attr_image_url = data.get("url")
            self._cached_image = None
            self._attr_image_last_updated = data.get("update_time")

            super()._handle_coordinator_update()
