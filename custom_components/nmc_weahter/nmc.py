import logging
from datetime import timedelta
from urllib.parse import urljoin
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from lxml import html
from .const import (
    DOMAIN,
    MANUFACTURER,
    DATA_MAX_TEMPERATURE24,
    DATA_PRECIPITATION24,
    DATA_FORECAST,
    DATA_FORECAST_HOURLY,
    DATA_RADAR
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=10)


class NMCDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, name, station_code):
        self.station_code = station_code
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

    async def _get_image_url(self, html_url):
        request_data = await self.session.get(html_url)
        tree = html.fromstring(await request_data.text())
        return tree.xpath('//img[@id="imgpath"]')[0].attrib["src"]

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
            (DATA_MAX_TEMPERATURE24,
             "http://www.nmc.cn/publish/temperature/hight/24hour.html"),
            (DATA_PRECIPITATION24, "http://www.nmc.cn/publish/precipitation/1-day.html"),
            (DATA_RADAR, "http://nmc.cn/publish/radar/chinaall.html")
        ]
        for image_type, url in images:
            data[image_type] = await self._get_image_url(url)
        return data
