import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import init_db, SessionLocal, VPNUser
from marzban_api import MarzbanAPI

# Инициализация
init_db()
marzban = MarzbanAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🚀 Создать VPN", callback_data="create_vpn")],
        [InlineKeyboardButton("❌ Удалить мой VPN", callback_data="delete_vpn")]
    ]
    await update.message.reply_text("Управление VPN Marzban:", reply_markup=InlineKeyboardMarkup(kb))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()
    tg_id = query.from_user.id
    
    if query.data == "create_vpn":
        # Проверка, есть ли уже ключ
        user = db.query(VPNUser).filter(VPNUser.tg_id == tg_id).first()
        if user:
            await query.edit_message_text(f"У вас уже есть ключ: `{user.marzban_username}`")
        else:
            m_username = f"user_{tg_id}"
            res = marzban.create_user(m_username)
            new_user = VPNUser(tg_id=tg_id, username=query.from_user.username, marzban_username=m_username)
            db.add(new_user)
            db.commit()
            link = res.get('subscription_url', 'Ошибка получения ссылки')
            await query.edit_message_text(f"✅ Ключ создан!\nТвоя ссылка: `{link}`")
            
    db.close()

if __name__ == '__main__':
    token = "8127712860:AAH8SbCbbDBNbmpDldBsALUiKYK1FjFN5pI"
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен...")
    app.run_polling()
