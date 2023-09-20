from datetime import datetime
import requests
import json
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_NATIVE_WIND_SPEED
)

from homeassistant.const import (
    CONF_NAME,
    UnitOfSpeed,
    UnitOfPressure,
    UnitOfTemperature
)

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
    ATTR_CONDITION_EXCEPTIONAL,
    ATTR_FORECAST_IS_DAYTIME,
    WeatherEntityFeature,
    Forecast,
    SingleCoordinatorWeatherEntity
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
    '小到中雨': ATTR_CONDITION_RAINY,
    '阵雨': ATTR_CONDITION_RAINY,
    '大雨': ATTR_CONDITION_POURING,
    '暴雨': ATTR_CONDITION_POURING,
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

_LOGGER = logging.getLogger(__name__)

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

class NMCWeather(SingleCoordinatorWeatherEntity):

    _attr_translation_key = "nmc"
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_TWICE_DAILY
    )

    def __init__(self, hass, name, station_code, coordinator):
        super().__init__(coordinator)
        self.hass = hass
        self._name = name
        self.station_code = station_code

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.station_code)},
            manufacturer=MANUFACTURER,
            model=self.station_code
        )

    def _condition_map(self, condition):
        if (c:=CONDITION_MAP.get(condition)) is not None:
            return c
        if '中雨' in condition:
            return ATTR_CONDITION_RAINY
        if '暴雨' in condition:
            return ATTR_CONDITION_POURING
        if '雨' in condition:
            return ATTR_CONDITION_RAINY
        if '雪' in condition:
            return ATTR_CONDITION_SNOWY
        if '沙' in condition:
            return ATTR_CONDITION_FOG
        if '云' in condition:
            return ATTR_CONDITION_CLOUDY
        if '雾' in condition:
            return ATTR_CONDITION_FOG

        _LOGGER.error(f'unkown condition: {condition}')
        return ATTR_CONDITION_EXCEPTIONAL
        
    
    @property
    def unique_id(self):
        return str(self.station_code)


    @property
    def name(self):
        return self._name

    @property
    def condition(self):
        skycon = self.coordinator.data['real']['weather']['info']
        return self._condition_map(skycon)

    @property
    def native_temperature(self):
        return self.coordinator.data['real']['weather']['temperature']

    @property
    def native_temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def humidity(self):
        return float(self.coordinator.data['real']['weather']['humidity']) 

    @property
    def native_wind_speed(self):
        return self.coordinator.data['real']['wind']['speed']

    @property
    def native_wind_speed_unit(self):
        """Return the current windspeed."""
        return UnitOfSpeed.METERS_PER_SECOND

    @property
    def wind_bearing(self):
        return self.coordinator.data['real']['wind']['direct']

    @property
    def native_pressure(self):
        pressure = self.coordinator.data['real']['weather']['airpressure']
        if pressure != 9999:
            return pressure
            
        return self.coordinator.data['passedchart'][0]['pressure']

    @property
    def native_pressure_unit(self):
        """Return the current pressure unit."""
        return UnitOfPressure.HPA

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

    @callback
    def _async_forecast_twice_daily(self) -> list[Forecast] | None:
        forecast_data = []
        for i in range(1, len(self.coordinator.data['predict']['detail'])):
            time_str = self.coordinator.data['predict']['detail'][i]['date']
            for time in ("day", "night"):
                predict = self.coordinator.data['predict']['detail'][i][time]
                data_dict = {
                    ATTR_FORECAST_TIME: datetime.strptime(time_str, '%Y-%m-%d'),
                    ATTR_FORECAST_CONDITION: self._condition_map(predict['weather']['info']),
                    ATTR_FORECAST_NATIVE_TEMP: predict['weather']['temperature'],
                    ATTR_FORECAST_WIND_BEARING: predict['wind']['direct'],
                    ATTR_FORECAST_NATIVE_WIND_SPEED: predict['wind']['power'],
                    ATTR_FORECAST_IS_DAYTIME: time == "day"
                }
                forecast_data.append(data_dict)
        return forecast_data
    
