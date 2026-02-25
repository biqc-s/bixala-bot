import logging
import os
import base64
import requests
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ============================================================
#  بوت بِكسلة — Bixala Bot
#  يجمع صور المقتنيات من ٦ زوايا ويرفعها ويولّد روابط
# ============================================================

# إعدادات — تُضاف كـ Variables في Railway
BOT_TOKEN = os.environ["BOT_TOKEN"]
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]
AIRTABLE_FORM_URL = os.environ.get("AIRTABLE_FORM_URL", "")

# مراحل المحادثة
NAME, ITEM_NAME, PHOTO_1, PHOTO_2, PHOTO_3, PHOTO_4, PHOTO_5, PHOTO_6 = range(8)

# إعدادات الزوايا الست
PHOTO_STEPS = [
    {
        "num": "١/٦",
        "angle": "من الأمام 🔲",
        "instruction": "صوّر القطعة من الأمام مباشرة.\n💡 خلّ الإضاءة واضحة والخلفية بسيطة."
    },
    {
        "num": "٢/٦",
        "angle": "من الخلف 🔳",
        "instruction": "أدر القطعة وصوّرها من الخلف."
    },
    {
        "num": "٣/٦",
        "angle": "من الجانب الأيمن ➡️",
        "instruction": "صوّرها من الجانب الأيمن."
    },
    {
        "num": "٤/٦",
        "angle": "من الجانب الأيسر ⬅️",
        "instruction": "صوّرها من الجانب الأيسر."
    },
    {
        "num": "٥/٦",
        "angle": "من الأعلى ⬆️",
        "instruction": "صوّرها من فوق (منظر علوي)."
    },
    {
        "num": "٦/٦",
        "angle": "تفاصيل مميزة ✨",
        "instruction": "صوّر أي نقش أو علامة أو تفصيلة مميزة على القطعة.\nإذا ما فيه، صوّرها من أي زاوية إضافية تحبها."
    },
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── رفع الصورة إلى imgBB ─────────────────────────────────
def upload_to_imgbb(file_bytes: bytes) -> str | None:
    """يرفع صورة على imgBB ويرجع الرابط المباشر."""
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": IMGBB_API_KEY,
                "image": b64,
            },
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data["data"]["url"]
    except Exception as e:
        logger.error(f"imgBB upload error: {e}")
    return None


# ─── أوامر المحادثة ──────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """رسالة الترحيب."""
    context.user_data.clear()
    context.user_data["photos"] = []

    await update.message.reply_text(
        "✨ *أهلاً بك في بِكسلة!*\n\n"
        "نحن نحفظ الإرث العائلي رقميًا 🏺\n\n"
        "سأساعدك ترفع صور قطعتك التراثية من ٦ زوايا مختلفة، "
        "وبعدها أعطيك رابط تلصقه في نموذج المشاركة.\n\n"
        "📝 *أرسل لي اسمك الكامل:*",
        parse_mode="Markdown",
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال الاسم."""
    context.user_data["name"] = update.message.text.strip()
    name = context.user_data["name"]

    await update.message.reply_text(
        f"أهلاً *{name}!* 👋\n\n"
        "📝 *أرسل لي اسم القطعة التراثية:*\n"
        "مثال: دلة قهوة، سجادة، خنجر، مبخرة...",
        parse_mode="Markdown",
    )
    return ITEM_NAME


async def get_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """استقبال اسم القطعة ثم طلب الصورة الأولى."""
    context.user_data["item_name"] = update.message.text.strip()
    item = context.user_data["item_name"]

    step = PHOTO_STEPS[0]
    await update.message.reply_text(
        f"ممتاز! بنصوّر *{item}* من ٦ زوايا 📷\n\n"
        "─────────────────\n"
        "💡 *نصائح سريعة للتصوير:*\n"
        "• استخدم إضاءة طبيعية أو واضحة\n"
        "• خلّ الخلفية بسيطة (أبيض أو لون واحد)\n"
        "• لا تستخدم فلاش\n"
        "• تأكد القطعة واضحة وكاملة في الصورة\n"
        "─────────────────\n\n"
        f"📸 *الصورة {step['num']} — {step['angle']}*\n"
        f"{step['instruction']}",
        parse_mode="Markdown",
    )
    return PHOTO_1


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالجة كل صورة مرفوعة."""
    current_step = len(context.user_data["photos"])

    # تحميل الصورة من تيليقرام
    photo = update.message.photo[-1]  # أعلى جودة
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    # رفعها على imgBB
    await update.message.reply_text("⏳ جاري رفع الصورة...")
    link = upload_to_imgbb(bytes(file_bytes))

    if not link:
        await update.message.reply_text(
            "❌ حصل خطأ في الرفع. أرسل الصورة مرة ثانية."
        )
        return PHOTO_1 + current_step

    # حفظ الرابط
    context.user_data["photos"].append(
        {"angle": PHOTO_STEPS[current_step]["angle"], "url": link}
    )

    await update.message.reply_text(f"✅ تم رفع الصورة {current_step + 1}/٦")

    # إذا كملنا ٦ صور
    if current_step + 1 >= 6:
        return await finish(update, context)

    # طلب الصورة التالية
    next_step = PHOTO_STEPS[current_step + 1]
    await update.message.reply_text(
        f"📸 *الصورة {next_step['num']} — {next_step['angle']}*\n"
        f"{next_step['instruction']}",
        parse_mode="Markdown",
    )
    return PHOTO_1 + current_step + 1


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إنهاء المحادثة وإرسال الروابط."""
    name = context.user_data["name"]
    item = context.user_data["item_name"]
    photos = context.user_data["photos"]

    # بناء رسالة الروابط
    links_text = ""
    for i, p in enumerate(photos, 1):
        links_text += f"{i}. {p['angle']}\n🔗 {p['url']}\n\n"

    # كل الروابط بسطر واحد لكل رابط (سهل النسخ)
    all_urls = "\n".join([p["url"] for p in photos])

    await update.message.reply_text(
        f"🎉 *ممتاز {name}!*\n\n"
        f"تم رفع ٦ صور لـ *{item}* بنجاح!\n\n"
        "─────────────────\n"
        f"📋 *روابط الصور:*\n\n"
        f"{links_text}"
        "─────────────────\n\n"
        "📋 *انسخ جميع الروابط:*",
        parse_mode="Markdown",
    )

    # رسالة منفصلة بالروابط فقط (سهل النسخ)
    await update.message.reply_text(
        f"📎 روابط صور: {item}\n\n{all_urls}",
    )

    # رابط الفورم
    if AIRTABLE_FORM_URL:
        await update.message.reply_text(
            "📝 *الخطوة الأخيرة:*\n\n"
            "الصق الروابط في نموذج المشاركة 👇\n"
            f"🔗 {AIRTABLE_FORM_URL}\n\n"
            "شكرًا لمشاركتك في بِكسلة! 🙏✨\n\n"
            "لتصوير قطعة أخرى أرسل /start",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "شكرًا لمشاركتك في بِكسلة! 🙏✨\n\n"
            "لتصوير قطعة أخرى أرسل /start",
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """إلغاء المحادثة."""
    await update.message.reply_text(
        "تم الإلغاء ❌\nتقدر تبدأ من جديد بأمر /start",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تخطي صورة اختيارية."""
    current_step = len(context.user_data["photos"])

    # فقط الصورة الأخيرة (التفاصيل) قابلة للتخطي
    if current_step == 5:
        context.user_data["photos"].append(
            {"angle": PHOTO_STEPS[5]["angle"], "url": "—"}
        )
        return await finish(update, context)

    await update.message.reply_text("⚠️ هذي الصورة مطلوبة. أرسل الصورة لو سمحت.")
    return PHOTO_1 + current_step


# ─── التشغيل ─────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_name)],
            PHOTO_1: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
            PHOTO_2: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
            PHOTO_3: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
            PHOTO_4: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
            PHOTO_5: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
            PHOTO_6: [
                MessageHandler(filters.PHOTO, handle_photo),
                CommandHandler("skip", skip_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("🚀 بوت بِكسلة شغّال!")
    app.run_polling()


if __name__ == "__main__":
    main()
