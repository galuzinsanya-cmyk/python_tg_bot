import logging
import os
import json
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Загружаем данные из .env
load_dotenv()
TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
PRICE = os.getenv("PRICE")
STOCK = os.getenv("STOCK")
WALLET = os.getenv("WALLET")
INSTRUCTIONS = os.getenv("INSTRUCTIONS", "Файл и инструкция будут высланы после оплаты.")

# Ссылка на закрытый чат
CHAT_LINK = "https://t.me/+k_TPDmjN1xdhNDky"

# Включаем логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- Клавиатура пользователя ---
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(
    KeyboardButton("Цена 💰"),
    KeyboardButton("Наличие 📦")
)
keyboard.add(
    KeyboardButton("Купить 🛒"),
    KeyboardButton("Я оплатил ✅")
)
keyboard.add(KeyboardButton("TG ЧАТ ПЕРЕЛИВА 💬"))

# --- Работа с пользователями ---
def load_users():
    if os.path.exists("users.json"):
        with open("users.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(users, f)

users = load_users()
user_context = {}  # сохраняем, куда пользователь оплатил (товар или чат)


# --- Команда /start ---
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        save_users(users)

    await message.answer(
        "👋 Привет!\nЯ бот для продажи товаров и доступа в приватный чат.\nВыбери опцию ниже 👇",
        reply_markup=keyboard
    )


# --- Цена ---
@dp.message_handler(lambda message: message.text == "Цена 💰")
async def price(message: types.Message):
    await message.answer(f"💰 Цена товара: {PRICE} долларов.")


# --- Наличие ---
@dp.message_handler(lambda message: message.text == "Наличие 📦")
async def stock(message: types.Message):
    await message.answer(f"📦 В наличии: {STOCK} шт.")


# --- Купить ---
@dp.message_handler(lambda message: message.text == "Купить 🛒")
async def buy(message: types.Message):
    user_context[message.from_user.id] = "product"
    await message.answer(
        f"💵 Для покупки отправьте оплату на следующий кошелек:\n\n{WALLET}\n\n"
        f"После оплаты нажмите кнопку 'Я оплатил ✅', и вы получите файл."
    )


# --- TG ЧАТ ПЕРЕЛИВА ---
@dp.message_handler(lambda message: message.text == "TG ЧАТ ПЕРЕЛИВА 💬")
async def tg_chat(message: types.Message):
    user_context[message.from_user.id] = "chat"
    chat_price = 19
    await message.answer(
        f"💬 Приватный TG ЧАТ ПЕРЕЛИВА стоит {chat_price}$ в месяц.\n\n"
        f"Для оплаты переведите {chat_price}$ на этот кошелёк:\n\n{WALLET}\n\n"
        "После оплаты нажмите 'Я оплатил ✅' — заявка на вступление будет отправлена владельцу."
    )


# --- Я оплатил ✅ ---
@dp.message_handler(lambda message: message.text == "Я оплатил ✅")
async def paid(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без ника"
    choice = user_context.get(user_id, "product")

    if choice == "chat":
        # Отправляем владельцу заявку с кнопкой "Одобрить"
        approve_button = InlineKeyboardMarkup().add(
            InlineKeyboardButton("✅ Одобрить доступ", callback_data=f"approve_{user_id}")
        )

        await bot.send_message(
            OWNER_ID,
            f"💬 Заявка на вступление в TG ЧАТ ПЕРЕЛИВА:\n"
            f"Пользователь: @{username}\nID: {user_id}\n\nПосле проверки оплаты — нажми 'Одобрить доступ'.",
            reply_markup=approve_button
        )

        await message.answer("✅ Ваша заявка отправлена владельцу. Ожидайте подтверждения 🔒")

    else:
        # Обычная покупка товара
        await bot.send_message(
            OWNER_ID,
            f"💰 Пользователь @{username} ({user_id}) отметил оплату *товара*.\n"
            f"Цена: {PRICE}$.\nОтправьте ему файл вручную."
        )
        await message.answer(f"Спасибо за оплату! {INSTRUCTIONS}")


# --- Одобрение заявки владельцем ---
@dp.callback_query_handler(lambda call: call.data.startswith("approve_"))
async def approve_user(call: types.CallbackQuery):
    if call.from_user.id != OWNER_ID:
        return await call.answer("❌ Только владелец может одобрять заявки.", show_alert=True)

    user_id = int(call.data.split("_")[1])

    try:
        await bot.send_message(
            user_id,
            f"🎉 Ваша заявка одобрена!\n\nВот ссылка на приватный чат:\n{CHAT_LINK}\n\nДобро пожаловать 💬"
        )
        await call.message.edit_text(f"✅ Пользователь {user_id} одобрен и получил ссылку на чат.")
    except Exception as e:
        await call.message.answer(f"⚠️ Не удалось отправить ссылку пользователю ({user_id}): {e}")


# --- Команда рассылки ---
@dp.message_handler(commands=['send'])
async def send_message_to_all(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("❌ У вас нет прав для этой команды.")

    text = message.text.replace("/send", "").strip()
    if not text:
        return await message.answer("Введите сообщение после команды, например:\n/send 🔥 Новая акция только сегодня!")

    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
        except Exception:
            pass

    await message.answer(f"✅ Сообщение отправлено {count} пользователям.")


# --- Запуск бота ---
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)





