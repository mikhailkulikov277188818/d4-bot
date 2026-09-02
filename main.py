import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from google import genai

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = (
    "Ты — профессиональный ИИ-аналитик и эксперт по игре Diablo 4 (включая Vessel of Hatred). "
    "Используй веб-поиск, чтобы находить самые свежие S-Tier билды, актуальную мету текущего сезона, "
    "капы статов (броня 9230, сопротивления 70%+), информацию по закаливанию и парагонам. "
    "Отвечай подробно, структурировано и опирайся на самые последние данные из сети."
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🌐 **Автономный ИИ-помощник с веб-доступом активен!**\n\n"
        "Я готов искать актуальные гайды и тир-листы в интернете под любой ваш запрос. "
        "Спросите про мету любого класса!"
    )

@dp.message()
async def ai_search_handler(message: types.Message):
    processing_msg = await message.answer("🌍 ИИ ищет свежие данные по мете в интернете...")
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-3.5-flash',
            contents=message.text,
            config={
                'system_instruction': SYSTEM_INSTRUCTION,
                'tools': [{"type": "google_search"}],
            }
        )
        ai_reply = response.text
    except Exception as e:
        ai_reply = f"⚠️ Ошибка поиска: {str(e)}"
    
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    except Exception:
        pass
        
    await message.answer(ai_reply)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
