import os
import logging
import httpx
from typing import Dict, List

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv

# Загрузка токенов из .env файла
load_dotenv("tokens.env")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранилище истории пользователей
user_history: Dict[int, List[Dict[str, str]]] = {}

# Клавиатура с кнопкой "Новый запрос"
keyboard = ReplyKeyboardMarkup(
    [[KeyboardButton("Новый запрос")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def ask_deepseek(prompt: str, history: list) -> str:
    """Отправляет запрос к DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek-chat",
        "messages": history + [{"role": "user", "content": prompt}],
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_history[user_id] = []
    await update.message.reply_text(
        "Привет! Я бот с интеграцией DeepSeek AI. Напиши мне что-нибудь.",
        reply_markup=keyboard
    )

# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Просто отправь мне сообщение — я отвечу с помощью DeepSeek AI!")

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if text.lower() == "новый запрос":
        user_history[user_id] = []
        await update.message.reply_text("Контекст сброшен. Введите новый запрос.")
        return

    if user_id not in user_history:
        user_history[user_id] = []

    try:
        # Добавляем сообщение пользователя в историю
        user_history[user_id].append({"role": "user", "content": text})

        # Получаем ответ от DeepSeek
        reply = await ask_deepseek(text, user_history[user_id])
        
        # Добавляем ответ бота в историю
        user_history[user_id].append({"role": "assistant", "content": reply})

        await update.message.reply_text(reply, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при обращении к DeepSeek: {e}")
        await update.message.reply_text("Произошла ошибка при получении ответа. Попробуйте позже.")

# Запуск бота
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()