from datetime import datetime, date, timezone, timedelta
import requests
import json
import re
import logging
from urllib.parse import urljoin
from lxml import html

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

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
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_NATIVE_PRESSURE,
    ATTR_FORECAST_HUMIDITY,
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
        data = json.loads(request_data.content)['data']
        url = data["predict"]["station"]["url"]
        request_data = await self.hass.async_add_executor_job(
            requests.get, urljoin("http://www.nmc.cn", url))
        data["html"] = request_data.content
        return data


def get_value(string):
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", string)
    if matches:
        return float(matches[0])
    return


class NMCWeather(SingleCoordinatorWeatherEntity):

    _attr_translation_key = "nmc"
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY
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
        if (c := CONDITION_MAP.get(condition)) is not None:
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
        for detail in self.coordinator.data['predict']['detail'][1:]:
            time = datetime.strptime(detail['date'], '%Y-%m-%d')
            for day_time in ("day", "night"):
                predict = detail[day_time]
                data_dict = {
                    ATTR_FORECAST_TIME: time,
                    ATTR_FORECAST_CONDITION: self._condition_map(predict['weather']['info']),
                    ATTR_FORECAST_NATIVE_TEMP: predict['weather']['temperature'],
                    ATTR_FORECAST_WIND_BEARING: predict['wind']['direct'],
                    ATTR_FORECAST_NATIVE_WIND_SPEED: predict['wind']['power'],
                    ATTR_FORECAST_IS_DAYTIME: day_time == "day"
                }
                forecast_data.append(data_dict)
        return forecast_data

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        forecast_data = []
        for detail in self.coordinator.data['predict']['detail'][1:]:
            time = datetime.strptime(detail['date'], '%Y-%m-%d')
            temp_day = detail["day"]['weather']['temperature']
            temp_night = detail["night"]['weather']['temperature']
            data_dict = {
                ATTR_FORECAST_TIME: time,
                ATTR_FORECAST_CONDITION: self._condition_map(detail["day"]['weather']['info']),
                ATTR_FORECAST_NATIVE_TEMP: max(temp_day, temp_night),
                ATTR_FORECAST_NATIVE_TEMP_LOW: min(temp_day, temp_night),
                ATTR_FORECAST_WIND_BEARING: detail["day"]['wind']['direct'],
                ATTR_FORECAST_NATIVE_WIND_SPEED: detail["day"]['wind']['power'],
            }
            forecast_data.append(data_dict)
        return forecast_data

    @callback
    def _async_forecast_hourly(self) -> list[Forecast] | None:
        forecast_data = []
        
        tree = html.fromstring(self.coordinator.data['html'])

        for i in range(0, 7):
            div_date = tree.xpath(
                f'//*[@id="day7"]//div[contains(@class,"weather")][{i+1}]//div[contains(@class, "date")]')
            if not len(div_date):
                break
            matches = re.findall(
                r'\d+/\d+', div_date[0].text_content().strip())
            if not matches:
                break
            month_day = datetime.strptime(matches[0], "%m/%d")
            now = dt_util.now(timezone(timedelta(hours=8)))
            if i == 0 and month_day.date().replace(year=now.year) != now.date():
                # 网页上的bug，过期日期的小时预报日期不正常，跳过
                continue
            predict_date = date(year=now.year if month_day.month >=
                                now.month else now.year + 1, month=month_day.month, day=month_day.day)

            div_day = tree.xpath(f'//*[@id="day{i}"]')
            if not len(div_day):
                break
            for div_hour in div_day[0].xpath("./div[contains(@class,'hour3')]"):
                time_str = div_hour.xpath("./div[1]")[0].text_content().strip()
                precipitation_str = div_hour.xpath(
                    "./div[3]")[0].text_content().strip()
                temp_str = div_hour.xpath("./div[4]")[0].text_content().strip()
                wind_speed_str = div_hour.xpath(
                    "./div[5]")[0].text_content().strip()
                wind_bearing_str = div_hour.xpath(
                    "./div[6]")[0].text_content().strip()
                pressure_str = div_hour.xpath(
                    "./div[7]")[0].text_content().strip()
                humidity_str = div_hour.xpath(
                    "./div[8]")[0].text_content().strip()

                predict = {}

                if "日" in time_str:
                    day_str, time_str = time_str.split("日")
                    predict_date = predict_date + timedelta(days=1)
                    if predict_date.day != int(day_str):
                        predict_date = predict_date.replace(day=int(day_str))
                time = dt_util.parse_time(time_str)
                predict[ATTR_FORECAST_TIME] = datetime.combine(
                    predict_date, time)

                if "mm" in precipitation_str and (precipitation := get_value(precipitation_str)) is not None:
                    predict[ATTR_FORECAST_PRECIPITATION] = precipitation
                if "℃" in temp_str and (temp := get_value(temp_str)) is not None:
                    predict[ATTR_FORECAST_NATIVE_TEMP] = temp
                if "m/s" in wind_speed_str and (wind_speed := get_value(wind_speed_str)) is not None:
                    predict[ATTR_FORECAST_NATIVE_WIND_SPEED] = wind_speed
                if (wind_bearing := get_value(wind_bearing_str)) is not None:
                    predict[ATTR_FORECAST_WIND_BEARING] = wind_bearing
                if "hPa" in pressure_str and (pressure := get_value(pressure_str)) is not None:
                    predict[ATTR_FORECAST_NATIVE_PRESSURE] = pressure
                if "%" in humidity_str and (humidity := get_value(humidity_str)) is not None:
                    predict[ATTR_FORECAST_HUMIDITY] = humidity

                forecast_data.append(predict)

        return forecast_data
