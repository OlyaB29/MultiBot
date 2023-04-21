import aiohttp
from config import EXCHANGE_API_Key

url = "https://api.apilayer.com/exchangerates_data/convert?to={}&from={}&amount={}"


'''
В функции реализован асинхронный запрос к API Exchange Rates. 
Функция возвращает сообщение о результате конвертации либо сообщение об ошибке 
'''


async def convert(from_, to_, amount):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url.format(to_, from_, amount), headers={"apikey": EXCHANGE_API_Key}) as resp:
                content = await resp.json()
                if "error" in content:
                    result = "Введен неизвестный код валюты.\nПопробуйте сначала" if content["error"][
                        "code"].startswith('invalid') else "Ошибка '{}'.\nПопробуйте сначала".format(
                        content["error"]["code"])
                else:
                    result = "Результат конвертации:\n" + str(content["result"]) + " " + to_
                return result
    except Exception as error:
        print(error)
        return "Что-то пошло не так, попробуйте сначала"
