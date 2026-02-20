import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder
from telegram.constants import ParseMode
from telegram.error import Conflict, RetryAfter, NetworkError
from database import init_db, SessionLocal, VPNUser
from marzban_api import MarzbanAPI

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

init_db()
api = MarzbanAPI()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Код функции start остается таким же...
    pass

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Код функции handle_callback остается таким же...
    pass

# Глобальный обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        logger.error("⚠️ Обнаружен конфликт! Другой экземпляр бота запущен. Пытаюсь восстановиться...")
    elif isinstance(context.error, RetryAfter):
        logger.warning(f"⏳ Слишком много запросов. Ждем {context.error.retry_after} сек.")
    else:
        logger.error(f"❌ Ошибка: {context.error}")

async def run_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    
    # Настройка приложения с защитой
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Добавляем хендлеры
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(error_handler)

    print("🚀 Бот запускается...")
    
    # Настройка параметров запуска для минимизации конфликтов
    await app.initialize()
    await app.start()
    
    # Важно: drop_pending_updates=True удаляет старые сообщения, 
    # накопленные, пока бот был выключен, что предотвращает спам и конфликты.
    await app.updater.start_polling(drop_pending_updates=True)
    
    # Держим бота запущенным
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        await app.stop()

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except Exception as e:
        print(f"Критический сбой: {e}")
