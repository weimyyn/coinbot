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

seen_coins = set()

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

# ====================== АВТОМАТИЧЕСКИЕ НОВЫЕ МОНЕТЫ ======================
async def monitor_new_coins():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.dexscreener.com/token-profiles/latest/v1", timeout=12) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(45)
                        continue
                    data = await resp.json()

            for item in data:
                if item.get("chainId") != "solana":
                    continue

                base = item.get("baseToken", {})
                address = base.get("address")
                if not address or address in seen_coins:
                    continue

                seen_coins.add(address)

                name = base.get("name", "Unknown")
                symbol = base.get("symbol", "???")
                
                # Пытаемся достать цену и изменение
                price = item.get("priceUsd") or item.get("price") or "N/A"
                change = item.get("priceChange", {}).get("h24") or item.get("priceChange24h") or "N/A"

                text = (
                    f"🚀 <b>Новая монета!</b>\n\n"
                    f"<b>{name}</b> (${symbol})\n"
                    f"CA: <code>{address}</code>\n"
                    f"Цена: <b>{price}</b>\n"
                    f"Изменение 24ч: <b>{change}%</b>\n\n"
                    f"<a href='https://dexscreener.com/solana/{address}'>📊 График DexScreener</a>\n"
                    f"<a href='https://www.tradingview.com/chart/?symbol={symbol}'>📈 TradingView</a>"
                )

                for user_id in ALLOWED_USERS:
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=text,
                            parse_mode="HTML",
                            disable_web_page_preview=False
                        )
                    except:
                        pass

                print(f"Новая монета отправлена: {symbol}")

        except Exception as e:
            print("Ошибка мониторинга:", e)

        await asyncio.sleep(40)

# ====================== МЕНЮ ======================
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

@dp.callback_query(F.data == "buy")
async def process_buy(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()

    text = "📈 <b>Что покупать:</b>\n\n"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.coingecko.com/api/v3/search/trending", timeout=8) as r:
                data = await r.json()
                text += "<b>🔥 В тренде:</b>\n"
                for item in data.get("coins", [])[:4]:
                    text += f"• {item['item']['name']} (${item['item']['symbol'].upper()})\n"
                text += "\n"

            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=price_change_percentage_24h_desc&per_page=10&page=1"
            async with session.get(url, timeout=8) as r:
                data = await r.json()
                text += "<b>📊 Сильный рост:</b>\n"
                count = 0
                for coin in data:
                    change = coin.get('price_change_percentage_24h') or 0
                    if change > 3:
                        text += f"• {coin['symbol'].upper()} +{change:.1f}%\n"
                        count += 1
                        if count >= 5:
                            break

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await callback.message.edit_text("Не удалось получить данные.", reply_markup=back_button())

@dp.callback_query(F.data == "sell")
async def process_sell(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()

    text = "📉 <b>Что лучше продать:</b>\n\n"
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=price_change_percentage_24h_asc&per_page=15&page=1"
            async with session.get(url, timeout=8) as r:
                data = await r.json()
                count = 0
                for coin in data:
                    change = coin.get('price_change_percentage_24h') or 0
                    if change < -3:
                        text += f"• {coin['symbol'].upper()} {change:.1f}%\n"
                        count += 1
                        if count >= 6:
                            break
                if count == 0:
                    text += "Сильных падений сейчас нет."

        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await callback.message.edit_text("Не удалось получить данные.", reply_markup=back_button())

@dp.callback_query(F.data == "new")
async def process_new(callback: CallbackQuery):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()

    text = "🪙 <b>Новые монеты :</b>\n\n"
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
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_button())
    except:
        await callback.message.edit_text("Не удалось найти новые монеты.", reply_markup=back_button())

@dp.callback_query(F.data == "news")
async def process_news(callback: CallbackQuery, state: FSMContext):
    if not await is_allowed(callback.from_user.id):
        return
    await callback.answer()
    await callback.message.edit_text(
        "Напиши тикер монеты (BTC, SOL, PEPE, WIF...):",
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
        f"📰 <b>Твиты по ${coin}</b>\n\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}&f=live'>🔴 Живые твиты</a>\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}%20(owner%20OR%20founder%20OR%20dev)&f=live'>👤 От владельцев/dev</a>\n"
        f"• <a href='https://twitter.com/search?q=%24{coin}%20min_faves%3A30&f=live'>🔥 Популярные</a>"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_button())

@dp.message()
async def fallback(message: Message):
    if not await is_allowed(message.from_user.id):
        return
    await message.answer("Напиши /menu")

async def main():
    print("Бот запущен (меню + авто-уведомления)...")
    asyncio.create_task(monitor_new_coins())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
