import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================== ТВОИ ДАННЫЕ ==================
BOT_TOKEN = "8965399377:AAFy0_rgg8vNtm-Ta-HEPwhC9oy3MQYbPqM"

ALLOWED_USERS = {
    6186773442,
    1122173232
}
# ================================================

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class NewsState(StatesGroup):
    waiting_for_coin = State()

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈что покупать?", callback_data="buy")],
        [InlineKeyboardButton(text="📉что продавать?", callback_data="sell")],
        [InlineKeyboardButton(text="🪙Новые монеты", callback_data="new")],
        [InlineKeyboardButton(text="📰Новости", callback_data="news")]
    ])

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back")]
    ])

async def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USERS

@dp.message(Command("start", "menu"))
async def cmd_menu(message: Message):
    if not await is_allowed(message.from_user.id):
        return await message.answer("Доступ закрыт.")
    await message.answer("Выбери раздел:", reply_markup=main_menu())

@dp.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery, state: FSMContext):
    if not await is_allowed(callback.from_user.id):
        return
    await state.clear()
    await callback.message.edit_text("Выбери раздел:", reply_markup=main_menu())
    await callback.answer()

# ====================== ЧТО ПОКУПАТЬ ======================
@dp.callback_query(F.data == "buy")
async def process_buy(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()
    msg = await callback.message.answer("🔍 Собираю данные...")

    text = "📈 <b>Что покупать:</b>\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            # CoinGecko Trending (самое важное)
            async with session.get("https://api.coingecko.com/api/v3/search/trending", timeout=8) as r:
                data = await r.json()
                text += "<b>🔥 В тренде:</b>\n"
                for item in data.get("coins", [])[:4]:
                    name = item["item"]["name"]
                    symbol = item["item"]["symbol"].upper()
                    text += f"• {name} (${symbol})\n"
                text += "\n"

            # Топ роста
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=price_change_percentage_24h_desc&per_page=5&page=1"
            async with session.get(url, timeout=8) as r:
                data = await r.json()
                text += "<b>📊 Сильный рост 24ч:</b>\n"
                for coin in data[:4]:
                    change = coin.get('price_change_percentage_24h') or 0
                    text += f"• {coin['symbol'].upper()} +{change:.1f}%\n"

        await msg.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await msg.edit_text("Не удалось получить данные. Попробуй позже.", reply_markup=back_button())

# ====================== ЧТО ПРОДАВАТЬ ======================
@dp.callback_query(F.data == "sell")
async def process_sell(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()
    msg = await callback.message.answer("🔍 Собираю данные...")

    text = "📉 <b>Что лучше продать:</b>\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=price_change_percentage_24h_asc&per_page=6&page=1"
            async with session.get(url, timeout=8) as r:
                data = await r.json()
                for coin in data[:5]:
                    change = coin.get('price_change_percentage_24h') or 0
                    text += f"• {coin['symbol'].upper()} {change:.1f}%\n"

        await msg.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await msg.edit_text("Не удалось получить данные.", reply_markup=back_button())

# ====================== НОВЫЕ МОНЕТЫ ======================
@dp.callback_query(F.data == "new")
async def process_new(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()
    msg = await callback.message.answer("🔍 Ищу новые монеты...")

    text = "🪙 <b>Новые монеты (Solana):</b>\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=10) as r:
                data = await r.json()
                count = 0
                for item in data:
                    if item.get("chainId") == "solana":
                        base = item.get("baseToken", {})
                        symbol = base.get("symbol", "???")
                        addr = base.get("address", "")
                        text += f"• <b>${symbol}</b>\n<code>{addr}</code>\n\n"
                        count += 1
                        if count >= 5:
                            break

        await msg.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await msg.edit_text("Не удалось найти новые монеты.", reply_markup=back_button())

# ====================== НОВОСТИ ======================
@dp.callback_query(F.data == "news")
async def process_news(callback: CallbackQuery, state: FSMContext):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()
    await callback.message.answer(
        "Напиши тикер монеты (например: BTC, SOL, PEPE, WIF, BONK):",
        reply_markup=back_button()
    )
    await state.set_state(NewsState.waiting_for_coin)

@dp.message(NewsState.waiting_for_coin)
async def get_news(message: Message, state: FSMContext):
    if not await is_allowed(message.from_user.id):
        return

    coin = message.text.strip().upper().replace("$", "")
    await state.clear()

    text = (
        f"📰 <b>Новости и твиты по ${coin}</b>\n\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}&src=typed_query&f=live'>🔴 Живые твиты по ${coin}</a>\n\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}%20(from%3Aofficial%20OR%20owner%20OR%20founder%20OR%20dev)&f=live'>👤 От владельцев / dev / founders</a>\n\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}%20min_faves%3A50&f=live'>🔥 Популярные твиты</a>\n\n"
        f"• <a href='https://twitter.com/search?q=%22{coin}%22%20crypto&f=live'>📢 Общий поиск</a>"
    )

    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_button())
