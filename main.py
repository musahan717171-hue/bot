import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import Conflict

# Импортируем твои модули
from database import init_db, SessionLocal, VPNUser
from marzban_api import MarzbanAPI

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация
init_db()
api = MarzbanAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(VPNUser).filter(VPNUser.tg_id == user_id).first()
    db.close()

    if user:
        text = (f"💎 **Личный кабинет**\n\n"
                f"👤 Аккаунт: `{user.marzban_username}`\n"
                f"🆔 Твой ID: `{user_id}`\n\n"
                f"Выберите действие ниже:")
        buttons = [
            [InlineKeyboardButton("📊 Статус и Ссылка", callback_data="status")],
            [InlineKeyboardButton("⏳ Продлить (+30 дней)", callback_data="renew")],
            [InlineKeyboardButton("🗑 Удалить ключ", callback_data="confirm_delete")]
        ]
    else:
        text = "👋 **Привет!**\n\nУ тебя еще нет VPN. Нажми кнопку ниже, чтобы создать личный ключ доступа."
        buttons = [[InlineKeyboardButton("🚀 Создать VPN ключ", callback_data="create")]]

    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    db = SessionLocal()
    user = db.query(VPNUser).filter(VPNUser.tg_id == user_id).first()

    if query.data == "create":
        if not user:
            m_username = f"user_{user_id}"
            res = api.create_user(m_username)
            if res and 'subscription_url' in res:
                db.add(VPNUser(tg_id=user_id, marzban_username=m_username))
                db.commit()
                msg = f"✅ **Ключ создан!**\n\nТвоя ссылка:\n`{res['subscription_url']}`"
            else:
                msg = "❌ Ошибка панели. Проверьте `MARZBAN_URL` и логин/пароль."
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "status":
        if user:
            data = api.get_user(user.marzban_username)
            if data:
                used = round(data.get('used_traffic', 0) / (1024**3), 2)
                limit = round(data.get('data_limit', 0) / (1024**3), 2)
                msg = (f"📈 **Твой статус:**\n\n"
                       f"📡 Трафик: `{used} GB` / `{limit} GB`\n"
                       f"🔗 Ссылка: `{data.get('subscription_url')}`")
                await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, 
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))

    elif query.data == "renew":
        if user:
            if api.renew_user(user.marzban_username):
                await query.edit_message_text("⚡️ **Подписка продлена на 30 дней!**", 
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))
            else:
                await query.edit_message_text("❌ Ошибка продления.")

    elif query.data == "confirm_delete":
        await query.edit_message_text("⚠️ **Удалить ключ?**\nЭто действие нельзя отменить.", 
                                      reply_markup=InlineKeyboardMarkup([
                                          [InlineKeyboardButton("✅ Да, удалить", callback_data="delete_final")],
                                          [InlineKeyboardButton("⬅️ Отмена", callback_data="back")]
                                      ]))

    elif query.data == "delete_final":
        if user:
            api.delete_user(user.marzban_username)
            db.delete(user)
            db.commit()
            await query.edit_message_text("🗑 Ключ удален. Напишите /start для нового заказа.")

    elif query.data == "back":
        db.close()
        # Для возврата просто вызываем логику старта, но с редактированием сообщения
        await query.edit_message_text("Загрузка меню...")
        # Перенаправляем на начало (создаем эффект возврата)
        class FakeMessage:
            async def reply_text(self, text, parse_mode, reply_markup):
                await query.edit_message_text(text, parse_mode=parse_mode, reply_markup=reply_markup)
        update.message = FakeMessage()
        await start(update, context)

    db.close()

async def run_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Сборка приложения
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Хендлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 Бот запускается...")

    try:
        await app.initialize()
        await app.start()
        
        # drop_pending_updates=True лечит 90% проблем с конфликтами при запуске
        print("📥 Очистка очереди и запуск Polling...")
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Ожидание работы
        while True:
            await asyncio.sleep(1)
            
    except Conflict:
        logger.error("❌ КРИТИЧЕСКАЯ ОШИБКА: Конфликт токена! Бот запущен где-то еще.")
    except Exception as e:
        logger.error(f"❌ Произошла ошибка: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
