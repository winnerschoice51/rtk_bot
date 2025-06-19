import aiohttp


async def get_weather_full():
    url = (f"http://api.openweathermap.org/data/2.5/forecast?q={LOCATION}"
           f"&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "⚠️ Не удалось получить погоду."

            data = await resp.json()

            if "list" not in data or len(data["list"]) == 0:
                return "⚠️ Не удалось получить прогноз погоды."

            first_forecast = data["list"][0]

            temp = first_forecast["main"]["temp"]
            feels_like = first_forecast["main"]["feels_like"]
            description = first_forecast["weather"][0]["description"]
            wind_speed = first_forecast["wind"]["speed"]
            humidity = first_forecast["main"]["humidity"]
            dt_txt = first_forecast["dt_txt"]

            message = (
                f"Погода в {data['city']['name']} на {dt_txt}:\n"
                f"Температура: {temp}°C, ощущается как {feels_like}°C\n"
                f"Состояние: {description}\n"
                f"Ветер: {wind_speed} м/с\n"
                f"Влажность: {humidity}%"
            )

            return message
