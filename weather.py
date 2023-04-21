import aiohttp
from config import WEATHER_APPID

appid = WEATHER_APPID
url = "https://api.openweathermap.org/data/2.5/weather?q={}&units=metric&lang=ru&appid=" + appid

'''
В функции реализован асинхронный запрос к API OpenWeather. 
Функция возвращает информацию о погоде для заданного города либо сообщение об ошибке 
'''


async def get_weather(city):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url.format(city)) as resp:
                content = await resp.json()
                return content
    except Exception as error:
        print(error)
        return "error"
