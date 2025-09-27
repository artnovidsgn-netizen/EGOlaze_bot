import os, asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import aiohttp

# Загружаем токены из .env (если файл есть локально)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Берём токен из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TG_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN:
    raise ValueError("❌ Нет токена! Укажи BOT_TOKEN (или TG_BOT_TOKEN) в Render → Environment")


dp = Dispatcher()
bot = Bot(BOT_TOKEN)

# Меню
menu = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="Подбор процедуры"), KeyboardButton(text="Подготовка / Уход")],
    [KeyboardButton(text="Противопоказания"), KeyboardButton(text="Записаться")]
])


# Системный промпт для ИИ (если подключите OpenAI)
SYSTEM_PROMPT = """Ты ассистент клиники лазерной эпиляции.
Отвечай кратко и понятно на русском. Даёшь образовательную инфо, не персональные мед-советы.
Если у пользователя есть противопоказания — рекомендуй очную консультацию.
Всегда используй чек-листы подготовки и ухода, будь эмпатичным и аккуратным."""

# Функция для запроса к OpenAI
async def ask_llm(user_text: str) -> str:
    if not OPENAI_API_KEY:
        return "ИИ-ответы отключены. Но я могу рассказать FAQ!"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "gpt-5-thinking",
        "messages": [
            {"role":"system","content": SYSTEM_PROMPT},
            {"role":"user","content": user_text}
        ],
        "temperature": 0.2
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, headers=headers, json=payload, timeout=60) as r:
            data = await r.json()
            return data["choices"][0]["message"]["content"].strip()

# Команда /start
@dp.message(F.text == "/start")
async def start_cmd(m: types.Message):
    await m.answer(
        "Привет! Я помогу с лазерной эпиляцией: подбор, подготовка, запись и уход.",
        reply_markup=menu
    )

# Подбор процедуры
@dp.message(F.text.contains("Подбор процедуры"))
async def select_flow(m: types.Message):
    q = (
        "Давай подберём курс. Ответь, пожалуйста:\n"
        "1) Фототип кожи (I–VI)?\n"
        "2) Был ли загар последние 2–4 недели?\n"
        "3) Принимаешь ли лекарства (например, изотретиноин)?\n"
        "4) Какая зона интересует?"
    )
    await m.answer(q)

# Подготовка / уход
@dp.message(F.text.contains("Подготовка") | F.text.contains("Уход"))
async def prep_after(m: types.Message):
    await m.answer(
        "Подготовка: за 24ч — побрить зону; 2–4 недели — без загара/солярия; SPF 50; "
        "за 3–7 дней — без пилингов/скрабов.\n"
        "После: SPF 50, без сауны/спорт 24–48ч, без горячих ванн, без пилингов 7 дней, увлажнение."
    )

# Противопоказания
@dp.message(F.text.contains("Противопоказ"))
async def contraindications(m: types.Message):
    await m.answer(
        "Противопоказания: беременность/ГВ, онкология, эпилепсия, кожные инфекции, свежий загар, "
        "приём изотретиноина ≤6–12 мес. Перед процедурой нужна консультация."
    )

# Запись
@dp.message(F.text.contains("Записаться"))
async def book(m: types.Message):
    await m.answer("Укажите зону и удобное время — я передам администратору.")

# Все остальные вопросы — к ИИ
@dp.message()
async def fallback(m: types.Message):
    reply = await ask_llm(m.text)
    await m.answer(reply)

# Запуск бота
def main():
    asyncio.run(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))

if __name__ == "__main__":
    main()
