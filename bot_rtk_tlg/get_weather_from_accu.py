import asyncio
import aiohttp
from dateutil.parser import parse  # нужно установить python-dateutil: pip install python-dateutil
from datetime import datetime


ACCUWEATHER_API_KEY = "FFFvelgKB64FGNAxS4lWj83T9N6lq3UO"
LOCATION_NAME = "Полярный"  # Можно подставить любой город


async def get_location_key(location_name):
    url = f"http://dataservice.accuweather.com/locations/v1/cities/search?apikey={ACCUWEATHER_API_KEY}&q={location_name}&language=ru-ru"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if not data:
                return None
            return data[0]['Key'], data[0]['LocalizedName']

def time_of_day(hour):
    if 6 <= hour < 12:
        return 'утро'
    elif 12 <= hour < 18:
        return 'день'
    elif 18 <= hour < 22:
        return 'вечер'
    else:
        return 'ночь'


def summarize_period(period_hours):
    if not period_hours:
        return "нет данных"
    temps = [h['Temperature']['Value'] for h in period_hours]
    descs = [h['IconPhrase'] for h in period_hours]
    desc = max(set(descs), key=descs.count)

    # Добавляем вероятность осадков
    precip_probs = [h.get('PrecipitationProbability', 0) for h in period_hours]
    max_precip = max(precip_probs) if precip_probs else 0

    min_temp = round(min(temps))
    max_temp = round(max(temps))

    if min_temp == max_temp:
        temp_str = f"{min_temp}°C"
    else:
        temp_str = f"{min_temp}–{max_temp}°C"

    precip_str = f", вероятность осадков: {max_precip}%" if max_precip > 0 else ""

    return f"{temp_str}, {desc}{precip_str}"


async def get_weather_full():
    location_info = await get_location_key(LOCATION_NAME)
    if location_info is None:
        return "⚠️ Не удалось найти город."

    location_key, localized_name = location_info

    async with aiohttp.ClientSession() as session:
        # Текущая погода
        url_current = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}?apikey={ACCUWEATHER_API_KEY}&language=ru-ru&details=true"
        async with session.get(url_current) as resp:
            if resp.status != 200:
                return "⚠️ Не удалось получить текущую погоду."
            current_data = await resp.json()
            if not current_data:
                return "⚠️ Пустой ответ по текущей погоде."

            current = current_data[0]
            temp = current["Temperature"]["Metric"]["Value"]
            feels_like = current["RealFeelTemperature"]["Metric"]["Value"]
            description = current["WeatherText"]
            wind_speed = current["Wind"]["Speed"]["Metric"]["Value"]
            humidity = current["RelativeHumidity"]
            observation_time = current["LocalObservationDateTime"][:19].replace("T", " ")

            emoji = weather_emoji(description)

        # Почасовой прогноз на 12 часов
        url_hourly = f"http://dataservice.accuweather.com/forecasts/v1/hourly/12hour/{location_key}?apikey={ACCUWEATHER_API_KEY}&language=ru-ru&metric=true"
        async with session.get(url_hourly) as resp:
            if resp.status != 200:
                return "⚠️ Не удалось получить почасовой прогноз."
            hourly_data = await resp.json()
            if not hourly_data:
                return "⚠️ Нет данных почасового прогноза."

            parts = {'утро': [], 'день': [], 'вечер': [], 'ночь': []}
            for hour_info in hourly_data:
                # datetime.fromisoformat не работает с +03:00 в Python <3.11, можно заменить на срез
                dt_obj = datetime.fromisoformat(hour_info['DateTime'][:-6])
                tod = time_of_day(dt_obj.hour)
                parts[tod].append(hour_info)

            morning = summarize_period(parts['утро'])
            day = summarize_period(parts['день'])
            evening = summarize_period(parts['вечер'])
            night = summarize_period(parts['ночь'])

    message = (
        f"🌤 Погода {observation_time}\n\n"
        f" Сейчас:\n"
        f"  {emoji} Температура: {round(temp)}°C (ощущается как {round(feels_like)}°C)\n"
        f"  Состояние: {description}\n"
        f"  Ветер: {round(wind_speed, 1)} м/с\n"
        f"  Влажность: {humidity}%\n\n"
        f"📅 Сегодня:\n"
        f"  🌅 Утро: {morning.replace('…', '–')}\n"
        f"  ☀️ День: {day.replace('…', '–')}\n"
        f"  🌇 Вечер: {evening.replace('…', '–')}\n"
        f"  🌙 Ночь: {night.replace('…', '–')}"
    )

    return message


def weather_emoji(description: str) -> str:
    desc = description.lower()
    if any(x in desc for x in ['дождь', 'ливень', 'морось']):
        return "🌧️"
    elif any(x in desc for x in ['гроза', 'шторм', 'гроза']):
        return "⛈️"
    elif any(x in desc for x in ['снег', 'метель', 'снежный']):
        return "❄️"
    elif any(x in desc for x in ['туман', 'дым', 'дымка', 'туманно', 'пыль']):
        return "🌫️"
    elif any(x in desc for x in ['пасмурно', 'облачно', 'облака']):
        return "☁️"
    elif any(x in desc for x in ['ясно', 'солнечно', 'солнце']):
        return "☀️"
    elif any(x in desc for x in ['переменная облачность', 'переменно']):
        return "⛅"
    else:
        return "🌈"

if __name__ == '__main__':
    result = asyncio.run(get_weather_full())
    print(result)