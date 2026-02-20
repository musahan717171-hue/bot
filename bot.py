import asyncio
import os
import random
import string
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import *
from marzban_api import *

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ---------- Утилиты ----------

def is_admin(user_id):
    return user_id == ADMIN_ID


def generate_username():
    return "user_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))


# ---------- Команды ----------

@dp.message(Command("start"))
async def start(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("VPN Manager запущен 🚀")


@dp.message(Command("новый_клиент"))
async def new_client(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer("Используй: /новый_клиент дни лимит_гб")
        return

    days = int(args[1])
    limit = int(args[2])

    username = generate_username()

    result = await create_user(username, days, limit)

    if "username" in result:
        await add_client(username, days, limit)

        link = result["links"][0]

        await message.answer(
            f"✅ Клиент создан\n\n"
            f"👤 Username: {username}\n"
            f"📅 Срок: {days} дней\n"
            f"📦 Лимит: {limit} GB\n\n"
            f"🔗 Ссылка:\n{link}"
        )
    else:
        await message.answer(f"❌ Ошибка: {result}")


@dp.message(Command("удалить"))
async def delete(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer("Используй: /удалить username")
        return

    username = args[1]

    await delete_user(username)
    await delete_client(username)

    await message.answer("Клиент удален ❌")


@dp.message(Command("клиенты"))
async def list_clients(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    clients = await get_all_clients()

    if not clients:
        await message.answer("Клиентов нет")
        return

    text = "📋 Список клиентов:\n\n"

    for client in clients:
        username = client[1]
        expiry = client[3]
        limit = client[4]

        user_data = await get_user(username)
        used = user_data.get("used_traffic", 0) // (1024 ** 3)

        text += (
            f"👤 {username}\n"
            f"📅 До: {expiry}\n"
            f"📦 Лимит: {limit} GB\n"
            f"📊 Использовано: {used} GB\n\n"
        )

    await message.answer(text)


# ---------- Авто проверка ----------

async def check_clients():
    clients = await get_all_clients()
    today = datetime.now().date()

    for client in clients:
        username = client[1]
        expiry = datetime.strptime(client[3], "%Y-%m-%d").date()
        notified = client[5]

        if today > expiry:
            await delete_user(username)
            await delete_client(username)
            await bot.send_message(ADMIN_ID, f"❌ {username} удален (истек срок)")

        elif (expiry - today).days <= 3 and not notified:
            await bot.send_message(ADMIN_ID, f"⚠️ {username} истекает {expiry}")
            await mark_notified(username)


# ---------- Запуск ----------

async def main():
    await init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_clients, "interval", hours=6)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
