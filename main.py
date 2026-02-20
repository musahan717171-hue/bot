import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import Conflict

from database import init_db, SessionLocal, VPNUser
from marzban_api import MarzbanAPI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

init_db()
api = MarzbanAPI()

# --- Обработчики команд ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(VPNUser).filter(VPNUser.tg_id == user_id).first()
    db.close()

    if user:
        text = f"💎 **Личный кабинет**\n\nАккаунт: `{user.marzban_username}`\n🆔 ID: `{user_id}`"
        buttons = [
            [InlineKeyboardButton("📊 Статус и Ссылка", callback_data="status")],
            [InlineKeyboardButton("⏳ Продлить (+30 дн.)", callback_data="renew")],
            [InlineKeyboardButton("🗑 Удалить ключ", callback_data="confirm_delete")]
        ]
    else:
        text = "👋 **Привет!**\nУ тебя нет VPN ключа. Создай его кнопкой ниже:"
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
                msg = f"✅ **Ключ создан!**\n\nСсылка:\n`{res['subscription_url']}`"
            else:
                msg = "❌ Ошибка панели. Проверьте настройки API."
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "status":
        if user:
            data = api.get_user(user.marzban_username)
            if data:
                used = round(data.get('used_traffic', 0) / (1024**3), 2)
                limit = round(data.get('data_limit', 0) / (1024**3), 2)
                msg = f"📈 **Статус:**\n📡 `{used} GB` / `{limit} GB`\n🔗 `{data.get('subscription_url')}`"
                await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))

    elif query.data == "renew":
        if user and api.renew_user(user.marzban_username):
            await query.edit_message_text("⚡️ **Продлено на 30 дней!**", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))

    elif query.data == "confirm_delete":
        await query.edit_message_text("⚠️ Удалить ключ?", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Да", callback_data="delete_final")], [InlineKeyboardButton("❌ Нет", callback_data="back")]]))

    elif query.data == "delete_final":
        if user:
            api.delete_user(user.marzban_username)
            db.delete(user)
            db.commit()
            await query.edit_message_text("🗑 Удалено. Напиши /start для нового заказа.")

    elif query.data == "back":
        db.close()
        await query.edit_message_text("Загрузка...")
        # Подмена сообщения для вызова start
        query.message.from_user = query.from_user
        await start(query, context)

    db.close()

# --- Логика запуска ---

async def run_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🚀 Подготовка к запуску...")

    try:
        await app.initialize()
        # ПРИНУДИТЕЛЬНО УДАЛЯЕМ ВЕБХУКИ И СТАРЫЕ СОЕДИНЕНИЯ
        await app.bot.delete_webhook(drop_pending_updates=True)
        await app.start()
        
        print("✅ Бот онлайн. Конфликты устранены.")
        await app.updater.start_polling(drop_pending_updates=True)
        
        while True:
            await asyncio.sleep(10)
            
    except Conflict:
        print("⚠️ Обнаружен конфликт токена. Railway перезапускает старую копию. Ожидайте...")
        await asyncio.sleep(5) # Даем время старой копии завершиться
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    asyncio.run(run_bot())
