import logging
from datetime import timedelta, datetime
from urllib.parse import urljoin
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from lxml import html
from .const import (
    DOMAIN,
    MANUFACTURER,
    CONF_STATION_CODE,
    CONF_IMAGES,
    CONF_IMAGE_MAX_TEMPERATURE24,
    CONF_IMAGE_TEMPERATURE_HOURLY,
    CONF_IMAGE_PRECIPITATION24,
    CONF_IMAGE_RADAR,
    DATA_MAX_TEMPERATURE24,
    DATA_PRECIPITATION24,
    DATA_FORECAST,
    DATA_FORECAST_HOURLY,
    DATA_RADAR,
    DATA_TEMPERATURE_HOURLY
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)


class NMCDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, name, config):
        self.station_code = config.get(CONF_STATION_CODE)
        self._images = config.get(CONF_IMAGES, [])
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.session = async_get_clientsession(self.hass)
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_code)},
            name=name,
            manufacturer=MANUFACTURER,
            model=self.station_code
        )

    async def _get_image(self, html_url):
        request_data = await self.session.get(html_url)
        tree = html.fromstring(await request_data.text())
        image = tree.xpath('//img[@id="imgpath"]')[0]
        return {
            "url": image.attrib["src"],
            "update_time": datetime.strptime(f"{datetime.now().year}/{image.attrib['data-time']}", "%Y/%m/%d %H:%M")
        }

    async def _async_update_data(self):
        # 预报信息
        data = {}
        request_data = await self.session.get(f"http://www.nmc.cn/rest/weather?stationid={self.station_code}")
        forecast = await request_data.json()
        data[DATA_FORECAST] = forecast["data"]

        # 网页每小时预报
        url = forecast["data"]["predict"]["station"]["url"]
        request_data = await self.session.get(urljoin("http://www.nmc.cn", url))
        data[DATA_FORECAST_HOURLY] = await request_data.text()

        # 图片
        images = [
            (CONF_IMAGE_MAX_TEMPERATURE24, DATA_MAX_TEMPERATURE24,
             "http://www.nmc.cn/publish/temperature/hight/24hour.html"),
            (CONF_IMAGE_PRECIPITATION24, DATA_PRECIPITATION24,
             "http://www.nmc.cn/publish/precipitation/1-day.html"),
            (CONF_IMAGE_RADAR, DATA_RADAR,
             "http://nmc.cn/publish/radar/chinaall.html"),
            (CONF_IMAGE_TEMPERATURE_HOURLY, DATA_TEMPERATURE_HOURLY,
             "http://nmc.cn/publish/observations/hourly-temperature.html")
        ]
        for conf_key, data_key, url in images:
            if conf_key in self._images:
                data[data_key] = await self._get_image(url)
        return data
