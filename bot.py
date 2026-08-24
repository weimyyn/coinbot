import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import time

# ================== ТВОИ ДАННЫЕ ==================
BOT_TOKEN = "8965399377:AAFbqLoemmLeEqGhVu0fBYVDli6BpMa2wJk"

# Два человека, которым будут приходить сообщения
USERS = [
    6186773442,
    1122173232
]
# ================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

seen = set()

async def check_tradingview_exists(symbol: str) -> bool:
    url = f"https://symbol-search.tradingview.com/symbol_search/?text={symbol}&hl=1&exchange=&lang=en&search_type=undefined&domain=production&sort_by_country=false"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                for item in data:
                    item_symbol = item.get("symbol", "").upper()
                    if item_symbol == symbol.upper() or item_symbol.startswith(symbol.upper()):
                        return True
                return False
    except:
        return False

async def get_new_solana_pairs():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=12) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [p for p in data if p.get("chainId") == "solana"]
    except:
        return []

async def monitor():
    while True:
        try:
            pairs = await get_new_solana_pairs()
            
            for pair in pairs:
                base = pair.get("baseToken", {})
                symbol = base.get("symbol", "").upper().strip()
                name = base.get("name", "Unknown")
                address = base.get("address", "")
                
                if not symbol or len(symbol) < 2 or symbol in seen:
                    continue
                
                exists = await check_tradingview_exists(symbol)
                if not exists:
                    continue
                
                seen.add(symbol)
                
                tv_link = f"https://www.tradingview.com/chart/?symbol={symbol}"
                tv_link_alt = f"https://www.tradingview.com/symbols/{symbol}/"
                
                text = (
                    f"🚀 <b>Монета появилась на TradingView!</b>\n\n"
                    f"<b>{name}</b> (${symbol})\n"
                    f"CA: <code>{address}</code>\n\n"
                    f"<a href='{tv_link}'>📈 Открыть график на TradingView</a>\n"
                    f"<a href='{tv_link_alt}'>🔗 Страница символа</a>"
                )
                
                # Отправляем обоим
                for user_id in USERS:
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=text,
                            parse_mode="HTML",
                            disable_web_page_preview=False
                        )
                    except Exception as e:
                        print(f"Ошибка отправки {user_id}: {e}")
                
                print(f"Отправил: {symbol}")
                
        except Exception as e:
            print("Ошибка:", e)
        
        await asyncio.sleep(40)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Бот работает. Уведомления приходят автоматически.")

async def main():
    print("Бот запущен для двух пользователей...")
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())