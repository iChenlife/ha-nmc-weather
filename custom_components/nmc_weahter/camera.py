"""Support for the Environment Canada radar imagery."""
from __future__ import annotations
from dataclasses import dataclass

import logging
from homeassistant.components.camera import Camera, CameraEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
class NMCCameraEntityDescription(CameraEntityDescription):
    data_key: str | None = None

CAMERA_TYPE = [
    NMCCameraEntityDescription(
        key=CONF_IMAGE_PRECIPITATION24,
        data_key=DATA_PRECIPITATION24,
        name="24h Precipitation",
    ),
    NMCCameraEntityDescription(
        key=CONF_IMAGE_MAX_TEMPERATURE24,
        data_key=DATA_MAX_TEMPERATURE24,
        name="24h Max Temperature",
    ),
    NMCCameraEntityDescription(
        key=CONF_IMAGE_RADAR,
        data_key=DATA_RADAR,
        name="Radar",
    ),
    NMCCameraEntityDescription(
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
    session = async_get_clientsession(hass)
    async_add_entities([NMCCamera(coordinator, session, description)
                        for description in CAMERA_TYPE if description.key in (config_entry.data[CONF_IMAGES] or [])])


class NMCCamera(CoordinatorEntity, Camera):

    def __init__(self, coordinator, session, description):
        """Initialize the camera."""
        super().__init__(coordinator)
        Camera.__init__(self)

        self.entity_description = description
        self._data_key = description.data_key
        self.session = session
        self._url = None
        self._image = None
        self._attr_unique_id = f"nmc-{coordinator.config_entry.unique_id}-camera-{description.key}"
        self._attr_device_info = coordinator.device_info

        self.content_type = "image/jpg"

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        url = self.coordinator.data[self._data_key]

        if url is not None and url != self._url:
            response = await self.session.get(url)
            self._image = await response.read()
            self._url = url

        return self._image
