import aiohttp
from bs4 import BeautifulSoup
import random
from aiogram.types import InputFile

url = "https://klike.net/2879-kartinki-milyh-zhivotnyh-35-foto.html"

'''
В функции реализован асинхронный запрос к сайту с различными фото милых животных. 
'''


async def get_photo():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                content = await resp.content.read()
                html = BeautifulSoup(content, 'html.parser')
                img_links = []
                # Парсим страницу и формируем список ссылок картинок
                for img in html.find_all('img', class_="fr-dib"):
                    img_links.append("https://klike.net" + img['data-src'])
                # Функция возвращает случайную ссылку из списка
                return random.choice(img_links)
    # В случае проблем с запросом функция возвращает имеющееся скачанное фото
    except Exception as error:
        print(error)
        photo = InputFile('img/animal_photo.jpeg')
        return photo
