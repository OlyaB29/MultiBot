from aiogram import Bot, types, executor
from aiogram.dispatcher import Dispatcher, FSMContext, filters
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import deep_linking
import logging
import re
from config import BOT_TOKEN
from weather import get_weather
from conversion import convert
from images import get_photo

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=storage)


# Создаем машину состояний
class ParamsDefine(StatesGroup):
    city = State()
    from_currency = State()
    to_currency = State()
    amount = State()


polls = {}  # здесь будут храниться списки опросов по ключам, являющимся id пользователей-создателей соответствующих
           # опросов

'''
Функция создает основную клавиатуру с четырьмя кнопками в два ряда, соответствующими четырем направлениям функционала бота.
Клавиатура всегда доступна пользователям
'''

async def get_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(types.KeyboardButton(text="Текущая погода"), types.KeyboardButton(text="Конвертация валют"))
    keyboard.row(types.KeyboardButton(text="Картинка милого животного"),
                 types.KeyboardButton(text="Создание опроса",
                                      request_poll=types.KeyboardButtonPollType(type=types.PollType.REGULAR)))
    return keyboard


# Обработчик команды /start
@dp.message_handler(commands=["start"], state='*')
async def start_bot(message: types.Message, state: FSMContext):
    # В случае получения указанной команды в личном чате бот приветствует пользователя и предлагает свои услуги
    if message.chat.type == types.ChatType.PRIVATE:
        await state.finish()
        await message.answer(
            "Приветствую Вас! Я могу быть многим полезен. Выберите ниже, что интересует Вас в данный момент",
            reply_markup=await get_keyboard())

    # В противном случае, когда бот получает команду в группе, в которую был добавлен с помощью глубокой ссылки, при
    # этом в команду был передан аргумент - id созданного опроса, который требуется в данную группу отправить,
    # определяем id запрашиваемого опроса, далее пытаемся найти этот опрос среди опросов пользователя
    else:
        required_poll_id = message.get_args()
        found_poll = None
        try:
            user_polls = polls[str(message.from_user.id)]
            for poll in user_polls:
                if required_poll_id == poll.id:
                    found_poll = poll

            # если требуемый опрос найден, бот отправляет его в группу, в противном случае пишет пользователю в личные
            # сообщения о том, что  опрос не найден
            if found_poll:
                await bot.send_poll(chat_id=message.chat.id, question=found_poll.question,
                                    is_anonymous=False, options=[o.text for o in found_poll.options], type="regular")
            else:
                await bot.send_message(message.from_user.id, 'Опрос не найден', reply_markup=await get_keyboard())
        except:
            await bot.send_message(message.from_user.id, 'Опрос не найден', reply_markup=await get_keyboard())


# Обработчик текстовых сообщений с указанным фильтром текста (срабатывает всегда при выборе одного из трех функций бота)
@dp.message_handler(filters.Text(equals=["Текущая погода", "Конвертация валют", "Картинка милого животного"]),
                    state='*')
async def answer_to_choice(message: types.Message, state: FSMContext):
    await state.finish()
    if message.text == "Текущая погода":
        # устанавливается соответствующее состояние дл определения интересующего города
        await ParamsDefine.city.set()
        await message.answer("Погода в каком городе Вас интересует?")
    elif message.text == "Конвертация валют":
        # устанавливается соответствующее состояние для определения исходной валюты
        await ParamsDefine.from_currency.set()
        await message.answer("Введите латинскими буквами трехзначный код валюты, которую хотите конвертировать")
    elif message.text == "Картинка милого животного":
        # получаем фото и отправляем пользователю
        photo = await get_photo()
        await bot.send_photo(message.chat.id, photo)


# Обработчик текстовых сообщений, срабатывающий при текущем состоянии city
@dp.message_handler(state=ParamsDefine.city)
async def city_define(message: types.Message, state: FSMContext):
    # Если написанное пользователем название города содержит только буквы и пробелы, получаем информацию о погоде в этом
    # городе и отправляем пользователю, останавливая машину состояний
    if re.match('[A-Za-zА-Яа-яёЁ ]*$', message.text):
        weather = await get_weather(message.text)
        if weather == "error":
            msg = "Что-то пошло не так, попробуйте еще"
            await state.finish()
        elif "message" in weather:
            # Если запрос для такого города информацию о погоде не выдал, пользователю предлагаается еще раз ввести
            # название города, состояние остается прежним
            msg = "Информация о погоде в таком городе не найдена.\nПопробуйте еще" if weather[
                                                                                          "message"] == 'city not found' else \
                weather["message"]
        else:
            msg = "<b>Погода в городе {}:</b>\n\n<i>Температура: </i>{}°C\n<i>По ощущениям: </i>{}°C\n<i>Влажность: </i>{} %\n<i>Ветер: </i>{} м/с\n<i>Ясность: </i>{}\n<a href='http://openweathermap.org/img/w/{}.png'>.</a>".format(
                message.text.title(), weather['main']['temp'], weather['main']['feels_like'],
                weather['main']['humidity'], weather['wind']['speed'], weather['weather'][0]['description'],
                weather['weather'][0]['icon'])
            await state.finish()
    else:
        # Если введенное название заведомо некорректное, пользователю предлагаается ввести правильное название,
        # состояние остается прежним
        msg = "Название города может содержать только буквы и пробелы. Введите корректное название"

    await message.answer(msg, reply_markup=await get_keyboard())


# Обработчик текстовых сообщений, срабатывающий при текущем состоянии from_currency
@dp.message_handler(state=ParamsDefine.from_currency)
async def from_currency_define(message: types.Message, state: FSMContext):
    # В случае если введенный код состоит из 3 латинских букв, сохраняем данные и переходим к следующему состоянию
    if re.match('[A-Za-z]{3}$', message.text):
        await state.update_data(from_currency=message.text)
        await ParamsDefine.next()
        msg = "Введите код валюты, в которую хотите конвертировать"
    else:
        # В противном случае состояние остается прежним и пользователю предлагается ввести корректные данные
        msg = "Введите корректный код валюты"
    await message.answer(msg, reply_markup=await get_keyboard())


# Обработчик текстовых сообщений, срабатывающий при текущем состоянии to_currency (определение целевой валюты)
@dp.message_handler(state=ParamsDefine.to_currency)
async def to_currency_define(message: types.Message, state: FSMContext):
    # В случае если введенный код состоит из 3 латинских букв, сохраняем данные и переходим к следующему состоянию
    if re.match('[A-Za-z]{3}$', message.text):
        await state.update_data(to_currency=message.text)
        await ParamsDefine.next()
        msg = "Введите сумму конверсии"
    else:
        # В противном случае состояние остается прежним и пользователю предлагается ввести корректные данные
        msg = "Введите корректный код валюты"
    await message.answer(msg, reply_markup=await get_keyboard())


# Обработчик текстовых сообщений, срабатывающий при текущем состоянии amount (определение суммы конверсии)
@dp.message_handler(state=ParamsDefine.amount)
async def amount_define(message: types.Message, state: FSMContext):
    # В случае если введенный текст состоит только из цифр, получаем сообщение о результате конвертации (в том числе об
    # ошибке при некорректных данных), передаем его пользователю и останавливаем машину состояний
    if message.text.isdigit():
        data = await state.get_data()
        await state.finish()
        msg = await convert(data['from_currency'], data['to_currency'], message.text)
    else:
        # В противном случае состояние остается прежним и пользователю предлагается ввести корректную сумму
        msg = "Сумма должна состоять из цифр"
    await message.answer(msg, reply_markup=await get_keyboard())


# Обработчик, срабатывающий при получении объекта опроса (когда он создан пользователем)
@dp.message_handler(content_types=["poll"], state="*")
async def msg_with_poll(message: types.Message, state: FSMContext):
    await state.finish()
    # Добавляем полученный опрос в список опросов пользователя
    global polls
    if not str(message.from_user.id) in polls:
        polls[str(message.from_user.id)] = []
    polls[str(message.from_user.id)].append(message.poll)

    # Кнопка с глубокой ссылкой для отправки опроса в группу (передается id опроса, по которому затем добавленный
    # в группу бот определяет, какой опрос нужно отправить)
    keyboard = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton(
        text="Отправить в группу",
        url=await deep_linking.get_startgroup_link(message.poll.id)
    ))

    await message.answer("Опрос создан", reply_markup=keyboard)


# Обработчик текстовых сообщений, срабатывающий, если пользователь отправил что-то незапланированное и не сработал
# ни один обработчик до этого
@dp.message_handler(state="*")
async def other_answer(message: types.Message):
    await message.answer("Я Вас не понял. Выберите, что Вы хотите", reply_markup=await get_keyboard())


if __name__ == "__main__":
    executor.start_polling(dp)
