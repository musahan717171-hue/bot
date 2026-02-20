import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from database import init_db, SessionLocal, VPNUser
from marzban_api import MarzbanAPI

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
init_db()
api = MarzbanAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    user = db.query(VPNUser).filter(VPNUser.tg_id == user_id).first()
    db.close()

    if user:
        text = f"💎 **Личный кабинет**\n\nВаш ID: `{user_id}`\nАккаунт: `{user.marzban_username}`\n\nВыберите действие:"
        buttons = [
            [InlineKeyboardButton("📊 Статистика и Ссылка", callback_data="status")],
            [InlineKeyboardButton("⏳ Продлить на 30 дней", callback_data="renew")],
            [InlineKeyboardButton("🗑 Удалить ключ", callback_data="confirm_delete")]
        ]
    else:
        text = "👋 **Привет!**\n\nУ тебя еще нет VPN подписки. Нажми кнопку ниже, чтобы создать её мгновенно!"
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
            if 'subscription_url' in res:
                db.add(VPNUser(tg_id=user_id, marzban_username=m_username))
                db.commit()
                msg = f"✅ **Ключ создан!**\n\nТвоя ссылка (нажми, чтобы скопировать):\n`{res['subscription_url']}`"
            else:
                msg = "❌ Ошибка панели. Проверьте настройки API."
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)

    elif query.data == "status":
        if user:
            data = api.get_user(user.marzban_username)
            used = round(data['used_traffic'] / (1024**3), 2)
            limit = round(data['data_limit'] / (1024**3), 2)
            msg = (f"📈 **Твой статус:**\n\n"
                   f"📡 Использовано: `{used} GB` / `{limit} GB`\n"
                   f"🔗 Ссылка: `{data['subscription_url']}`")
            await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, 
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back")]]))

    elif query.data == "renew":
        if user and api.renew_user(user.marzban_username):
            await query.edit_message_text("⚡️ **Подписка продлена на 30 дней!**", parse_mode=ParseMode.MARKDOWN)
        
    elif query.data == "confirm_delete":
        await query.edit_message_text("⚠️ Вы уверены? Ключ будет удален навсегда.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Да, удалить", callback_data="delete_final")]]))

    elif query.data == "delete_final":
        if user:
            api.delete_user(user.marzban_username)
            db.delete(user)
            db.commit()
            await query.edit_message_text("🗑 Ключ успешно удален. Ждем вас снова!")

    elif query.data == "back":
        db.close()
        await start(update, context)
        return

    db.close()

if __name__ == '__main__':
    TOKEN = os.getenv("BOT_TOKEN")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
