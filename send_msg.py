import asyncio
import os
from telegram import Bot

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or "8987382222:AAEGXQMCdEomgqrobJ25XN7lsVTg-8Ao1K4"
TARGET_USER_ID = 1148440368

async def main():
    bot = Bot(token=BOT_TOKEN)
    
    text = """
از طرفی به من سپرده شده است روزی فقط ۲ هزارتومان از حساب پول برداشت کنم برای مبلغ بیشتر با آرمان هماهنگی انجام بده.
"""
    
    try:
        msg = await bot.send_message(
            chat_id=TARGET_USER_ID,
            text=text
        )
        print(f"✅ پیام با موفقیت ارسال شد! شناسه پیام: {msg.message_id}")
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")

if __name__ == "__main__":
    asyncio.run(main())
