import os
import logging

import aiohttp
import re


from datetime import datetime

from openai import AsyncOpenAI

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)


# =====================================================
# خواندن تنظیمات از Environment Variables
# در Railway این‌ها را در بخش Variables تعریف می‌کنی
# =====================================================

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GAPGPT_API_KEY = os.environ.get("GAPGPT_API_KEY")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))
# =====================================================
# BRS API
# =====================================================

BRS_API_KEY = "BGvKeQy8FNfxRAYnafpDzNzLMxdEBeCs"

BRS_API_URL = (
    f"https://Api.BrsApi.ir/Market/Gold_Currency_Pro.php"
    f"?key={BRS_API_KEY}"
)

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


BANNED_USER_TITLES = {
    1148440368: "ثنای عزیز",
    7031977248: "آرمان عزیز",
}

async def handle_restricted_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user.id not in BANNED_USER_TITLES:
        return False

    first_message_name = BANNED_USER_TITLES[user.id]

    attempts = context.user_data.get("banned_attempts", 0) + 1
    context.user_data["banned_attempts"] = attempts

    if attempts == 1:
        msg = f"""
خطای سیستم: ۴۰۳ ❌

{first_message_name} متاسفانه این ربات برای استفاده افراد «باهوش و باشخصیت» طراحی شده و سیستم ما علائم شدیدی از بی‌شعوری و رفتارهای شبیه به گاو سانان رو در اکانت شما شناسایی کرده! 🐮💤

لطفاً جهت حفظ سلامت سرور، دکمه Stop Bot را زده و به چراگاه خود بازگردید. با تشکر! 🌾🚶‍♂️
"""
    elif attempts == 2:
        msg = """
ببین انگار اصلاً متوجه نیستی! 🤦‍♂️

مگه نگفتم این ربات مال تو نیست؟ چرا دوباره داری پیام می‌فرستی؟
سواد خواندن و نوشتن نداری یا شاخات جلوی چشمت رو گرفته؟ 🐄🚫
یک‌بار دیگه دست به این ربات بزنی با یه لحن دیگه باهات صحبت می‌کنم!
"""
    else:
        msg = f"""
🚨 تلاش شماره {attempts} شما ثبت شد!

واقعاً سطح سماجت و بی‌شعوریت قله‌های جدیدی رو فتح کرده! 🐑🔥
چند بار باید بهت بگم ول کن این ربات رو؟ مگه علف هرز بهت دادن که انقدر پیگیری؟اسکلی چیزی هستی؟
برو یه جا دیگه ماع‌ماع کن، دست از سر ما بردار! 🛑🌾
"""

    if update.callback_query:
        await update.callback_query.answer("دسترسی مسدود است! ❌", show_alert=True)
        await update.callback_query.message.reply_text(msg)
    elif update.message:
        await update.message.reply_text(msg)

    return True



# =====================================================
# آماده‌سازی اطلاعات کاربر برای ارسال به ادمین
# =====================================================

def format_user_info(user, message_text=None, action_text="کاربر با بات کار کرد"):
    username = f"@{user.username}" if user.username else "ندارد"
    first_name = user.first_name or "ندارد"
    last_name = user.last_name or "ندارد"
    language_code = user.language_code or "نامشخص"

    text = f"""
👤 {action_text}

🆔 Telegram ID: {user.id}
👤 Username: {username}
📛 First Name: {first_name}
📛 Last Name: {last_name}
🌐 Language: {language_code}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    if message_text:
        text += f"""

💬 پیام / عملیات کاربر:
{message_text}
"""

    return text



# =====================================================
# ارسال مشخصات کاربر به ادمین
# =====================================================

async def notify_admin(
    context: ContextTypes.DEFAULT_TYPE,
    user,
    message_text=None,
    action_text="کاربر با بات کار کرد",
):
    if not ADMIN_TELEGRAM_ID:
        logger.warning("ADMIN_TELEGRAM_ID is not set.")
        return

    text = format_user_info(
        user=user,
        message_text=message_text,
        action_text=action_text,
    )

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



async def get_market_data():

    async with aiohttp.ClientSession() as session:
        async with session.get(BRS_API_URL) as response:

            if response.status != 200:
                return None

            return await response.json()
        
        
def find_symbol(data, keyword):

    keyword = keyword.lower()

    all_items = []

    all_items.extend(data.get("gold", []))
    all_items.extend(data.get("currency", []))
    all_items.extend(data.get("cryptocurrency", []))

    mapping = {
        "دلار": "USD",
        "تتر": "USDT_IRT",
        "بیت": "BTC",
        "بیت کوین": "BTC",
        "بیتکوین": "BTC",
        "اتریوم": "ETH",
        "یورو": "EUR",
        "پوند": "GBP",
        "درهم": "AED",
        "طلا": "IR_GOLD_18K",
        "طلای 18": "IR_GOLD_18K",
        "طلای 24": "IR_GOLD_24K",
        "انس": "XAUUSD",
        "سکه": "IR_COIN_EMAMI",
        "ربع": "IR_COIN_QUARTER",
        "نیم": "IR_COIN_HALF",
        "بهار": "IR_COIN_BAHAR",
    }

    target_symbol = None

    for k, v in mapping.items():
        if k in keyword:
            target_symbol = v
            break

    if not target_symbol:
        return None

    for item in all_items:
        if item["symbol"] == target_symbol:
            return item

    return None




def build_market_message(item):

    change = item.get("change_percent", 0)

    if change > 0:
        emoji = "🟢"
    elif change < 0:
        emoji = "🔴"
    else:
        emoji = "⚪"

    text = (
        f"{emoji} {item['name']}\n\n"
        f"💰 قیمت: {item['price']:,} {item['unit']}\n"
        f"📈 تغییر: {item.get('change_percent',0)}%\n"
        f"📊 مقدار تغییر: {item.get('change_value','-')}\n"
        f"🕒 {item['date']} - {item['time']}"
    )

    return text



def is_market_question(text):

    keywords = [
        "قیمت",
        "نرخ",
        "چنده",
        "چند",
        "طلا",
        "سکه",
        "دلار",
        "یورو",
        "تتر",
        "بیت",
        "بیت کوین",
        "اتریوم",
        "رمزارز",
        "ارز"
    ]

    text = text.lower()

    return any(k in text for k in keywords)



# =====================================================
# دستور /contact
# =====================================================

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    await notify_admin(
        context=context,
        user=user,
        message_text="/contact",
        action_text="کاربر دستور /contact را زد",
    )

    if await handle_restricted_user(update, context):
        return

    keyboard = [
        [
            InlineKeyboardButton(
                "📨 درخواست ارتباط با آرمان",
                callback_data="contact_request",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 پیام مستقیم در تلگرام",
                url="https://t.me/ArmanTakestani",
            )
        ],
        [
            InlineKeyboardButton(
                "📧 ارسال ایمیل با Gmail",
                url="https://mail.google.com/mail/?view=cm&fs=1&to=armantakestani6440@gmail.com",
            )
        ],
        [
            InlineKeyboardButton(
                "📸 اینستاگرام آرمان",
                url="https://instagram.com/armawni",
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    contact_text = """
📬 راه‌های ارتباطی با آرمان

📞 Phone:
09100379179

📧 Gmail:
armantakestani6440@gmail.com

💬 Telegram:
@ArmanTakestani

📸 Instagram:
@armawni


"""

    await update.message.reply_text(
        contact_text,
        reply_markup=reply_markup,
    )





async def contact_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user

    if await handle_restricted_user(update, context):
        return

    # جواب کوتاه به کلیک کاربر، تا حالت loading دکمه از بین برود
    await query.answer("درخواست ارتباط ثبت شد ✅")

    # پیام به خود کاربر
    user_text = """
✅ درخواست ارتباط شما ثبت شد.
"""

    await query.message.reply_text(user_text)

    # پیام به ادمین
    await notify_admin(
        context=context,
        user=user,
        message_text="کاربر روی دکمه درخواست ارتباط کلیک کرد.",
        action_text="درخواست ارتباط با آرمان",
    )


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

    if await handle_restricted_user(update, context):
        return

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

    if await handle_restricted_user(update, context):
        return

    await update.message.chat.send_action(
        action=ChatAction.TYPING
    )

    if is_market_question(message_text):

        try:

            data = await get_market_data()

            if data:

                item = find_symbol(data, message_text)

                if item:

                    await update.message.reply_text(
                        build_market_message(item)
                    )

                    return

        except Exception:
            logger.exception("Market API Error")

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
        CallbackQueryHandler(
            contact_button_handler,
            pattern="^contact_request$",
        )
    )

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
