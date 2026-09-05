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
            model='gemini-3.6-flash', # Актуальная модель по требованию API Google
            contents=f"Найди в интернете и составь подробный актуальный гайд/данные по запросу: {query}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                tools=[{"google_search": {}}],
            )
        )
        return response.text
    except Exception as e:
        return f"⚠️ Ошибка обновления данных: {str(e)}"

async def initial_data_gathering():
    global knowledge_base
    print("🚀 [АГЕНТ] Запуск первичного сбора базы данных...")
    
    initial_queries = [
        "Diablo 4 лучшие S-Tier билды текущего сезона",
        "Диабло 4 капы брони и сопротивлений эндгейм",
        "Diablo 4 мета классы волшебник разбойник некромант варвар друид спиритборн"
    ]
    
    for query in initial_queries:
        if query not in knowledge_base:
            print(f"🔍 [АГЕНТ] Исследую тему: {query}")
            data = await fetch_meta_from_web(query)
            knowledge_base[query] = data
            save_db(knowledge_base)
            await asyncio.sleep(5)
            
    print("✅ [АГЕНТ] Первичная база данных успешно сформирована и сохранена в /data!")

async def background_meta_updater():
    global knowledge_base
    while True:
        await asyncio.sleep(1200) # 20 минут
        print("🔄 [АГЕНТ] Плановый фоновый опрос сети на предмет изменений в мете...")
        
        for query in list(knowledge_base.keys()):
            fresh_data = await fetch_meta_from_web(query)
            knowledge_base[query] = fresh_data
            save_db(knowledge_base)
            await asyncio.sleep(5)
            
        print("✨ [АГЕНТ] База данных успешно актуализирована фоновым процессом.")

@dp.message(Command("start"))
async def cmd_start(message: tg_types.Message):
    await message.answer(
        "🤖 **Автономный ИИ-архитектор Diablo 4 активен!**\n\n"
        "Моя база знаний сохраняется в постоянное хранилище, наполняется автоматически и обновляется каждые 20 минут. "
        "Спрашивай про любые билды и капы!"
    )

@dp.message()
async def ai_handler(message: tg_types.Message):
    global knowledge_base
    user_query = message.text.strip()
    query_lower = user_query.lower()
    
    for stored_query, content in knowledge_base.items():
        if query_lower in stored_query.lower() or stored_query.lower() in query_lower:
            await message.answer(f"📖 **Из автономной базы знаний:**\n\n{content}")
            return

    processing_msg = await message.answer("🌍 Новая тема! Агент исследует сеть и добавляет данные в библиотеку...")
    
    ai_reply = await fetch_meta_from_web(user_query)
    
    knowledge_base[user_query] = ai_reply
    save_db(knowledge_base)
    
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
    except Exception:
        pass
        
    await message.answer(ai_reply)

async def main():
    asyncio.create_task(initial_data_gathering())
    asyncio.create_task(background_meta_updater())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
