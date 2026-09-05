import os
import logging
import asyncio
import json
from aiogram import Bot, Dispatcher, types as tg_types
from aiogram.filters import Command
from google import genai
from google.genai import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Настраиваем путь с учетом постоянного хранилища Amvera (/data)
DATA_DIR = "/data"
if os.path.exists(DATA_DIR) and os.access(DATA_DIR, os.W_OK):
    DB_FILE = os.path.join(DATA_DIR, "knowledge_base.json")
else:
    DB_FILE = "knowledge_base.json"

SYSTEM_INSTRUCTION = (
    "Ты — автономный ИИ-архитектор и главный эксперт по игре Diablo 4 (Vessel of Hatred). "
    "Твоя задача — собирать и поддерживать в актуальном состоянии базу данных по S-Tier билдам, "
    "капам статов (броня 9230, сопротивления 70%+), парагонам и механикам. "
    "Отдавай структурированные, глубокие и точные данные."
)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Ошибка сохранения базы: {e}")

knowledge_base = load_db()

async def fetch_meta_from_web(query: str) -> str:
    try:
        response = ai_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=f"Найди в интернете и составь подробный актуальный гайд/данные по запросу: {query}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[{"google_search": {}}],
            )
        )
        return response.text
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            return "⏳ Превышен лимит запросов к нейросети (квота API). Подожди 1–2 минуты и повтори запрос."
        return f"⚠️ Ошибка обновления данных: {err_str}"

# Фоновый апдейтер с редкими запросами, чтобы не ловить лимиты
async def background_meta_updater():
    global knowledge_base
    while True:
        await asyncio.sleep(3600) # Проверка раз в час, чтобы не тратить квоту
        if not knowledge_base:
            continue
            
        print("🔄 [АГЕНТ] Плановый фоновый опрос сети...")
        for query in list(knowledge_base.keys()):
            fresh_data = await fetch_meta_from_web(query)
            if "превышен лимит" not in fresh_data.lower():
                knowledge_base[query] = fresh_data
                save_db(knowledge_base)
            await asyncio.sleep(20) # Большая пауза между запросами для безопасности лимитов

@dp.message(Command("start"))
async def cmd_start(message: tg_types.Message):
    await message.answer(
        "🤖 **Автономный ИИ-агент Diablo 4 активен!**\n\n"
        "База знаний работает в режиме умного кеширования. Задавай любой вопрос по билдам — если данных нет, я сам найду их в сети!"
    )

@dp.message()
async def ai_handler(message: tg_types.Message):
    global knowledge_base
    user_query = message.text.strip()
    query_lower = user_query.lower()
    
    # Проверяем локальную базу
    for stored_query, content in knowledge_base.items():
        if query_lower in stored_query.lower() or stored_query.lower() in query_lower:
            await message.answer(f"📖 **Из автономной базы знаний:**\n\n{content}")
            return

    processing_msg = await message.answer("🌍 Ищу свежие данные в сети через поисковый агент...")
    
    ai_reply = await fetch_meta_from_web(user_query)
    
    # Сохраняем в базу только успешные ответы
    if "превышен лимит" not in ai_reply.lower() and "ошибка" not in ai_reply.lower():
        knowledge_base[user_query] = ai_reply
        save_db(knowledge_base)
    
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    except Exception:
        pass
        
    await message.answer(ai_reply)

async def main():
    # Запускаем только фоновый апдейтер (без спама при старте)
    asyncio.create_task(background_meta_updater())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
