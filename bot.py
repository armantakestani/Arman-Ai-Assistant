import os
import logging
from datetime import datetime

from openai import AsyncOpenAI

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =====================================================
# خواندن تنظیمات از Environment Variables
# در Railway این‌ها را در بخش Variables تعریف می‌کنی
# =====================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))


# =====================================================
# تنظیمات GapGPT
# =====================================================

GAPGPT_BASE_URL = "https://api.gapgpt.app/v1"
GAPGPT_MODEL = os.environ.get("GAPGPT_MODEL", "gpt-4o")


# =====================================================
# ساخت کلاینت GapGPT
# =====================================================

client = AsyncOpenAI(
    base_url=GAPGPT_BASE_URL,
    api_key=GAPGPT_API_KEY,
)


# =====================================================
# لاگ
# =====================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =====================================================
# آماده‌سازی اطلاعات کاربر برای ارسال به ادمین
# =====================================================

def format_user_info(user, message_text=None):
    username = f"@{user.username}" if user.username else "ندارد"
    first_name = user.first_name or "ندارد"
    last_name = user.last_name or "ندارد"
    language_code = user.language_code or "نامشخص"

    text = f"""
👤 کاربر با بات کار کرد

🆔 Telegram ID: {user.id}
👤 Username: {username}
📛 First Name: {first_name}
📛 Last Name: {last_name}
🌐 Language: {language_code}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    if message_text:
        text += f"""

💬 پیام کاربر:
{message_text}
"""

    return text


# =====================================================
# ارسال مشخصات کاربر به ادمین
# =====================================================

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, user, message_text=None):
    if not ADMIN_TELEGRAM_ID:
        logger.warning("ADMIN_TELEGRAM_ID is not set.")
        return

    text = format_user_info(user, message_text)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=text,
        )
    except Exception:
        logger.exception("Could not notify admin")


# =====================================================
# ارسال پیام به GapGPT و گرفتن جواب
# =====================================================

async def ask_gapgpt(user_message: str) -> str:
    try:
        response = await client.chat.completions.create(
            model=GAPGPT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "تو یک دستیار فارسی‌زبان مفید، دقیق، صمیمی و محترم هستی. "
                        "پاسخ‌ها را واضح، کاربردی و قابل فهم بده."
                    ),
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.7,
        )

        return response.choices[0].message.content

    except Exception:
        logger.exception("GapGPT request failed")
        return (
            "متأسفانه الان نتونستم از سرویس هوش مصنوعی جواب بگیرم.\n"
            "لطفاً چند لحظه بعد دوباره امتحان کن."
        )


# =====================================================
# دستور /contact
# =====================================================

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact_text = """
📬 راه‌های ارتباطی با آرمان

📞 Phone:
09100379179

📸 Instagram:
https://instagram.com/armawni
"""

    await update.message.reply_text(contact_text)


# =====================================================
# تقسیم پیام‌های طولانی برای تلگرام
# =====================================================

async def send_long_message(update: Update, text: str):
    max_length = 4000

    if not text:
        await update.message.reply_text("پاسخی دریافت نشد.")
        return

    for i in range(0, len(text), max_length):
        await update.message.reply_text(text[i:i + max_length])


# =====================================================
# دستور /start
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await notify_admin(
        context=context,
        user=user,
        message_text="/start",
    )

    welcome_text = """
سلام 👋

من دستیار هوشمند آرمان هستم 🤠
هر سوالی، ایده‌ای یا کاری داشتی بفرست تا با هم جلو ببریم.

چطور می‌تونم کمکت کنم؟
"""

    await update.message.reply_text(welcome_text)


# =====================================================
# دستور /myid
# =====================================================

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await update.message.reply_text(
        f"آیدی عددی تلگرام شما:\n{user.id}"
    )


# =====================================================
# هندل کردن پیام‌های عادی
# =====================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text

    await notify_admin(
        context=context,
        user=user,
        message_text=message_text,
    )

    await update.message.chat.send_action(action=ChatAction.TYPING)

    answer = await ask_gapgpt(message_text)

    await send_long_message(update, answer)


# =====================================================
# هندل خطاهای کلی بات
# =====================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception(
        "Unhandled exception:",
        exc_info=context.error,
    )


# =====================================================
# اجرای بات
# =====================================================

def main():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

    if not GAPGPT_API_KEY:
        raise ValueError("GAPGPT_API_KEY is not set.")

    if not ADMIN_TELEGRAM_ID:
        raise ValueError("ADMIN_TELEGRAM_ID is not set.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("contact", contact))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    app.add_error_handler(error_handler)

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
