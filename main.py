import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai

# Получаем секреты из окружения Amvera
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Инициализируем бота и клиента Gemini
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Ты — профессиональный ИИ-аналитик и эксперт по игре Diablo 4 (включая контент Vessel of Hatred). "
    "Ты знаешь всё про актуальную мету, S-Tier билды, капы статов (броня 9230, сопротивления 70%+), "
    "закаливание (Tempering), парагоны и эндгейм-боссов. Отвечай подробно, структурировано и по делу."
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🧠 **ИИ-ассистент Diablo 4 на базе Gemini активирован!**\n\n"
        "Теперь я не использую заготовки — я анализирую каждый твой вопрос в реальном времени. "
        "Спроси меня про любой билд, механику или класс!"
    )

@dp.message()
async def ai_handler(message: types.Message):
    # Уведомляем пользователя, что ИИ думает
    processing_msg = await message.answer("🔍 ИИ анализирует мету и готовит гайд...")
    
    try:
        # Отправляем запрос в модель Gemini с системной инструкцией
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=message.text,
            config={
                'system_instruction': SYSTEM_INSTRUCTION,
            }
        )
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"⚠️ Ошибка обращения к ИИ: {str(e)}"
    
    # Удаляем статус загрузки и отправляем ответ игроку
    await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    await message.answer(ai_reply)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
