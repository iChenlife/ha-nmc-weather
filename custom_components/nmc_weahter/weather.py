from datetime import datetime
import requests
import json

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.components.weather import (
    WeatherEntity, ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_TEMP, ATTR_FORECAST_TEMP_LOW, ATTR_FORECAST_TIME, ATTR_FORECAST_WIND_BEARING, ATTR_FORECAST_WIND_SPEED)

from homeassistant.const import (TEMP_CELSIUS, CONF_NAME)

from .const import DOMAIN, MANUFACTURER, NAME, CONF_STATION_CODE

from homeassistant.components.weather import (
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_EXCEPTIONAL
)

CONDITION_MAP = {
    '晴': ATTR_CONDITION_SUNNY,
    '多云': ATTR_CONDITION_CLOUDY,
    '局部多云': ATTR_CONDITION_PARTLYCLOUDY,    
    '阴': ATTR_CONDITION_CLOUDY,
    '雾': ATTR_CONDITION_FOG,
    '中雾': ATTR_CONDITION_FOG,
    '大雾': ATTR_CONDITION_FOG,
    '小雨': ATTR_CONDITION_RAINY,
    '中雨': ATTR_CONDITION_RAINY,
    '大雨': ATTR_CONDITION_POURING,
    '暴雨': ATTR_CONDITION_POURING,
    '雾': ATTR_CONDITION_FOG,
    '小雪': ATTR_CONDITION_SNOWY,
    '中雪': ATTR_CONDITION_SNOWY,
    '大雪': ATTR_CONDITION_SNOWY,
    '暴雪': ATTR_CONDITION_SNOWY,
    '扬沙': ATTR_CONDITION_FOG,
    '沙尘': ATTR_CONDITION_FOG,
    '雷阵雨': ATTR_CONDITION_LIGHTNING_RAINY,
    '冰雹': ATTR_CONDITION_HAIL,
    '雨夹雪': ATTR_CONDITION_SNOWY_RAINY,
    '大风': ATTR_CONDITION_WINDY,
    '薄雾': ATTR_CONDITION_FOG,
    '雨': ATTR_CONDITION_RAINY,
    '雪': ATTR_CONDITION_SNOWY,
    '9999': ATTR_CONDITION_EXCEPTIONAL,
    
}

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    config = entry.data
    async_add_entities([NMCWeather(
        hass, name=config.get(CONF_NAME, NAME),  station_code=config.get(CONF_STATION_CODE), coordinator=coordinator
    )])

class NMCData():
    def __init__(self, hass, station_code):
        self.hass = hass
        self.station_code = station_code
    
    async def fetch_data(self):
        request_data = await self.hass.async_add_executor_job(
            requests.get, f"http://www.nmc.cn/rest/weather?stationid={self.station_code}")
        return json.loads(request_data.content)['data']

class NMCWeather(CoordinatorEntity, WeatherEntity):

    def __init__(self, hass, name, station_code, coordinator):
        self.hass = hass
        self._name = name
        self.station_code = station_code
        self.coordinator = coordinator

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_code)},
            manufacturer=MANUFACTURER,
            model=self.station_code
        )
    
    @property
    def unique_id(self):
        return str(self.station_code)


    @property
    def name(self):
        return self._name

    @property
    def state(self):
        skycon = self.coordinator.data['real']['weather']['info']
        return CONDITION_MAP.get(skycon)

    @property
    def temperature(self):
        return self.coordinator.data['real']['weather']['temperature']

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def humidity(self):
        return float(self.coordinator.data['real']['weather']['humidity']) 

    @property
    def wind_speed(self):
        return self.coordinator.data['real']['wind']['speed']

    @property
    def wind_bearing(self):
        return self.coordinator.data['real']['wind']['direct']

    @property
    def wind_speed(self):
        return self.coordinator.data['real']['wind']['power']


    @property
    def pressure(self):
        return round(float(self.coordinator.data['real']['weather']['airpressure']) / 100, 2)


    @property
    def attribution(self):
        return "Data provided by www.nmc.cn"

    @property
    def aqi(self):
        return self.coordinator.data['air']['aqi']

    @property
    def aqi_description(self):
        return self.coordinator.data['air']['aqi']
        
    @property
    def alert(self):
        return self.coordinator.data['real']['warn']['alert']

    @property
    def forecast(self):
        forecast_data = []
        for i in range(1, len(self.coordinator.data['predict']['detail'])):
            time_str = self.coordinator.data['predict']['detail'][i]['date']
            data_dict = {
                ATTR_FORECAST_TIME: datetime.strptime(time_str, '%Y-%m-%d'),
                ATTR_FORECAST_CONDITION: CONDITION_MAP[self.coordinator.data['predict']['detail'][i]['day']['weather']['info']],
                ATTR_FORECAST_TEMP: self.coordinator.data['tempchart'][i+7]['max_temp'],
                ATTR_FORECAST_TEMP_LOW: self.coordinator.data['tempchart'][i+7]['min_temp'],
                ATTR_FORECAST_WIND_BEARING: self.coordinator.data['predict']['detail'][i]['day']['wind']['direct'],
                ATTR_FORECAST_WIND_SPEED: self.coordinator.data['predict']['detail'][i]['day']['wind']['power']
            }
            forecast_data.append(data_dict)

        return forecast_data
