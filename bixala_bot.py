# ============================================================
#  بوت بِكسلة — Bixala Bot
#  الوظيفة: بوت تراثي متكامل مع وكيل ذكي (GPT)
#  ويجمع صور المقتنيات ويحفظها في قاعدة بيانات
# ============================================================

# ──────────────────────────────────────────────────────────
# 📦 استيراد المكتبات
# ──────────────────────────────────────────────────────────
import logging
import os
import csv
import io
import requests
from collections import Counter
from datetime import datetime
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)


BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "")
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
CLOUDINARY_CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
CLOUDINARY_API_KEY = os.environ["CLOUDINARY_API_KEY"]
CLOUDINARY_API_SECRET = os.environ["CLOUDINARY_API_SECRET"]

# ── عميل Supabase ──
db: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── إعداد Cloudinary ──
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True,
)      

# ── قائمة الأدمنز ──
ADMIN_IDS = [int(x.strip()) for x in ADMIN_ID.split(",") if x.strip().isdigit()]

# ──────────────────────────────────────────────────────────
# 🔢 مراحل المحادثة
# ──────────────────────────────────────────────────────────
(
    PASSWORD,       # 0 — كلمة السر
    MAIN_MENU,      # 1 — القائمة الرئيسية
    ITEM_TYPE,      # 2 — اختيار نوع القطعة
    ITEM_NAME,      # 3 — كتابة اسم القطعة
    NAME,           # 4 — كتابة اسم المشارك
    PHOTO_1,        # 5
    PHOTO_2,        # 6
    PHOTO_3,        # 7
    PHOTO_4,        # 8
    PHOTO_5,        # 9
    PHOTO_6,        # 10
    PHONE,          # 11 — رقم الجوال
    STORY,          # 12 — قصة القطعة
    AI_STORY_INPUT, # 13 — كتابة المعلومات للذكاء الاصطناعي
    AI_STORY_CONFIRM,#14 — التأكيد على القصة المولّدة
) = range(15)

# ──────────────────────────────────────────────────────────
# 🏺 أنواع القطع
# ──────────────────────────────────────────────────────────
ITEM_TYPES = [
    ["دلة قهوة ☕", "مبخرة 🪔"],
    ["سجادة 🧶", "خنجر 🗡️"],
    ["أواني فخارية 🏺", "ملابس تراثية 👘"],
    ["حُلي ومجوهرات 💍", "أدوات حرفية 🔨"],
    ["أخرى ✏️"],
]

# ──────────────────────────────────────────────────────────
# 📸 الزوايا الست
# ──────────────────────────────────────────────────────────
PHOTO_STEPS = [
    {"num": "١/٦", "angle": "من الأمام 🔲", "instruction": "صوّر القطعة من الأمام مباشرة.\nخلّ الإضاءة واضحة والخلفية بسيطة 💡"},
    {"num": "٢/٦", "angle": "من الخلف 🔳", "instruction": "أدر القطعة وصوّرها من الخلف."},
    {"num": "٣/٦", "angle": "من الجانب الأيمن ➡️", "instruction": "صوّرها من الجانب الأيمن."},
    {"num": "٤/٦", "angle": "من الجانب الأيسر ⬅️", "instruction": "صوّرها من الجانب الأيسر."},
    {"num": "٥/٦", "angle": "من الأعلى ⬆️", "instruction": "صوّرها من فوق (منظر علوي)."},
    {"num": "٦/٦", "angle": "تفاصيل مميزة ✨", "instruction": "صوّر أي نقش أو علامة مميزة على القطعة.\nإذا ما فيه، صوّرها من أي زاوية إضافية."},
]

# ──────────────────────────────────────────────────────────
# 🤖 رسالة النظام للوكيل الذكي — شخصيته وتعليماته
# 💡 تستخدم المقتطفات فقط لكتابة القصص ولا يتاح المحادثة العامة معه
# ──────────────────────────────────────────────────────────
AI_SYSTEM_PROMPT = """أنت "بِكسل" الوكيل الذكي لمشروع بِكسلة 🤖

مهمتك الوحيدة:
تأليف قصة قصيرة أو وصف دافئ وعاطفي يناسب تراث المملكة وثقافتها، بناءً على المعلومات التي يقدمها المشارك عن قطعته التراثية مثل عمرها ومصدرها وأصحابها.

الشروط:
١. القصة تُكتب بأسلوب الراوي بحيث تصلح للتعليق الصوتي في معرض فني أو تجربة واقع افتراضي.
٢. النبرة دافئة وقريبة من القلب، تعكس مشاعر الحنين وقيم الكرم والأصالة.
٣. لا تتجاوز ٣ إلى ٤ أسطر كحد أقصى. اختصر وأثّر.
٤. اكتب بالعربية الفصحى الواضحة مع لمسة من روح اللهجة السعودية دون تعقيد."""

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# 🗄️ قاعدة البيانات — Supabase
# ══════════════════════════════════════════════════════════
def log_activity(telegram_id, action, details=""):
    try:
        db.table("activity_log").insert({
            "telegram_id": telegram_id, "action": action, "details": details
        }).execute()
    except Exception as e:
        logger.error(f"log_activity error: {e}")


def save_participant(telegram_id, username, name, phone="", city=""):
    try:
        res = db.table("participants").insert({
            "telegram_id": telegram_id, "telegram_username": username or "",
            "name": name, "phone": phone, "city": city
        }).execute()
        return res.data[0]["id"]
    except Exception as e:
        logger.error(f"save_participant error: {e}")
        return None


def save_item(participant_id, item_type, item_name, story=""):
    try:
        res = db.table("items").insert({
            "participant_id": participant_id, "item_type": item_type,
            "item_name": item_name, "status": "مكتمل", "story": story
        }).execute()
        return res.data[0]["id"]
    except Exception as e:
        logger.error(f"save_item error: {e}")
        return None


def save_photo(item_id, angle, url):
    try:
        db.table("photos").insert({
            "item_id": item_id, "angle": angle, "url": url
        }).execute()
    except Exception as e:
        logger.error(f"save_photo error: {e}")


def get_stats():
    try:
        tp = len(db.table("participants").select("id").execute().data)
        ti = len(db.table("items").select("id").execute().data)
        tph = len(db.table("photos").select("id").execute().data)
        items_data = db.table("items").select("item_type").execute().data
        counts = Counter(r["item_type"] for r in items_data)
        tt = counts.most_common(1)[0][0] if counts else "—"
        fa = len(db.table("activity_log").select("id").eq("action", "كلمة_سر_خاطئة").execute().data)
        ra_data = db.table("activity_log").select("action,details,timestamp").order("id", desc=True).limit(5).execute().data
        ra = [(r["action"], r.get("details") or "", r.get("timestamp") or "") for r in ra_data]
        return {"total_participants": tp, "total_items": ti, "total_photos": tph,
                "top_type": tt, "failed_attempts": fa, "recent_activity": ra}
    except Exception as e:
        logger.error(f"get_stats error: {e}")
        return {"total_participants": 0, "total_items": 0, "total_photos": 0,
                "top_type": "—", "failed_attempts": 0, "recent_activity": []}


def is_admin(user_id):
    return user_id in ADMIN_IDS


def photo_progress(done: int) -> str:
    """يرجع شريط التقدم البصري: ✅✅✅⬜⬜⬜"""
    return "".join(["✅" if i < done else "⬜" for i in range(6)])


# ══════════════════════════════════════════════════════════
# 🖼️ رفع الصور على Cloudinary
# ══════════════════════════════════════════════════════════
def upload_to_cloudinary(file_bytes):
    try:
        result = cloudinary.uploader.upload(
            file_bytes,
            folder="bixala",
            resource_type="image",
        )
        return result.get("secure_url")
    except Exception as e:
        logger.error(f"Cloudinary error: {e}")
    return None


# ══════════════════════════════════════════════════════════
# 🤖 دالة الوكيل الذكي — إرسال رسالة إلى OpenAI GPT
# ══════════════════════════════════════════════════════════
def ask_gpt(user_message: str, chat_history: list) -> str:
    """
    ترسل رسالة المستخدم + سجل المحادثة إلى GPT وترجع الرد.
    chat_history: قائمة بالرسائل السابقة [{role, content}, ...]
    """
    try:
        # بناء الرسائل: رسالة النظام + سجل المحادثة + الرسالة الجديدة
        messages = [{"role": "system", "content": AI_SYSTEM_PROMPT}]
        messages.extend(chat_history)
        messages.append({"role": "user", "content": user_message})

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": messages,
                "max_tokens": 500,         # الحد الأقصى للرد
                "temperature": 0.7,        # درجة الإبداعية
            },
            timeout=30,
        )

        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            logger.error(f"OpenAI error {resp.status_code}: {resp.text}")
            return "عذرًا، حصل خطأ تقني.. حاول مرة ثانية 🙏"

    except Exception as e:
        logger.error(f"OpenAI exception: {e}")
        return "عذرًا، حصل خطأ في الاتصال.. حاول مرة ثانية 🙏"


# ══════════════════════════════════════════════════════════
# 🔧 دالة عرض القائمة الرئيسية
# ══════════════════════════════════════════════════════════
def main_menu_keyboard():
    """ترجع أزرار القائمة الرئيسية (Inline Keyboard)."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("تسجيل قطعة تراثية 📸", callback_data="register_item")],
        [InlineKeyboardButton("التواصل مع الدعم الفني 📞", callback_data="support")],
        [InlineKeyboardButton("إلغاء ✖️", callback_data="cancel")],
    ])


async def show_main_menu(message, name=""):
    """ترسل القائمة الرئيسية."""
    greeting = f"أهلاً *{name}* " if name else ""
    await message.reply_text(
        f"{greeting}مرحباً بك في *بِكسلة* ✨\n\n"
        "نجمع الماضي لنحفظه للمستقبل 🏺\n"
        "نحوّل القطع التراثية العائلية إلى تجارب تفاعلية وواقع معزز.\n\n"
        "كيف نقدر نساعدك اليوم؟ 👇",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


# ══════════════════════════════════════════════════════════
# 🟢 البداية — ترحيب + القائمة مباشرة بدون كلمة سر
# ══════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["photos"] = []
    context.user_data["ai_history"] = []

    user = update.effective_user
    log_activity(user.id, "بداية_محادثة", f"@{user.username or 'بدون_يوزر'}")

    await show_main_menu(update.message)
    return MAIN_MENU


# ══════════════════════════════════════════════════════════
# 🔐 التحقق من كلمة السر
# ══════════════════════════════════════════════════════════
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    entered = update.message.text.strip()

    if entered == BOT_PASSWORD:
        log_activity(user.id, "كلمة_سر_صحيحة")
        await update.message.reply_text(
            "تم التحقق بنجاح ✅\n\nأرسل لي اسمك الكامل 📝",
            parse_mode="Markdown",
        )
        return NAME

    log_activity(user.id, "كلمة_سر_خاطئة", "محاولة فاشلة")
    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1

    if context.user_data["attempts"] >= 3:
        log_activity(user.id, "تم_الحظر", "٣ محاولات فاشلة")
        await update.message.reply_text("تم تجاوز عدد المحاولات 🚫\nتواصل مع فريق بِكسلة للحصول على كلمة السر.")
        await show_main_menu(update.message)
        return MAIN_MENU

    remaining = 3 - context.user_data["attempts"]
    await update.message.reply_text(
        f"كلمة السر غير صحيحة ✖️\nمتبقي *{remaining}* محاولات.\n\nأدخل كلمة السر 🔐",
        parse_mode="Markdown",
    )
    return PASSWORD


# ══════════════════════════════════════════════════════════
# 📋 معالجة أزرار القائمة الرئيسية
# ══════════════════════════════════════════════════════════
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()  # إزالة علامة التحميل من الزر
    user = update.effective_user
    choice = query.data

    # ─── 📸 تسجيل قطعة — يطلب كلمة السر أولاً ───
    if choice == "register_item":
        log_activity(user.id, "بدء_تسجيل_قطعة")
        context.user_data["attempts"] = 0
        await query.message.reply_text(
            "أدخل كلمة السر للمتابعة 🔐",
            parse_mode="Markdown",
        )
        return PASSWORD

    # ─── 📞 الدعم الفني ───
    elif choice == "support":
        log_activity(user.id, "طلب_دعم_فني")
        if SUPPORT_USERNAME:
            support_text = f"تواصل مع فريق الدعم مباشرة: {SUPPORT_USERNAME}"
        else:
            support_text = "أرسل استفسارك هنا وسيتواصل معك فريقنا في أقرب وقت."
        await query.message.reply_text(
            f"الدعم الفني 📞\n\n{support_text}\n\nللرجوع للقائمة أرسل: /menu",
            parse_mode="Markdown",
        )
        return MAIN_MENU

    # ─── ❌ إلغاء ───
    elif choice == "cancel":
        log_activity(user.id, "إلغاء_من_القائمة")
        await query.message.reply_text(
            "شكرًا لزيارتك بِكسلة 🙏✨\nتقدر ترجع بإرسال أي رسالة.",
        )
        return ConversationHandler.END

    return MAIN_MENU


# ══════════════════════════════════════════════════════════
# /menu — الرجوع للقائمة الرئيسية من أي مكان
# ══════════════════════════════════════════════════════════
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await show_main_menu(update.message)
    return MAIN_MENU


# ══════════════════════════════════════════════════════════
# 👤 استقبال الاسم
# ══════════════════════════════════════════════════════════
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.user_data["name"] = update.message.text.strip()
    name = context.user_data["name"]
    log_activity(user.id, "تسجيل_اسم", name)

    await update.message.reply_text(
        f"تشرفنا فيك يا *{name}* 👋\n\n"
        "عشان نبقى على تواصل بعد رفع القطعة\nالرجاء إدخال رقم جوالك 📱\n"
        "_(مثال: 0512345678)_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    phone = update.message.text.strip()
    digits = phone.replace(" ", "").replace("-", "").replace("+", "")

    if not (digits.isdigit() and 8 <= len(digits) <= 15):
        await update.message.reply_text(
            "رقم الجوال غير صحيح ⚠️\n\n"
            "أدخل رقم جوالك 📱\nمثال: 0512345678",
            parse_mode="Markdown",
        )
        return PHONE

    context.user_data["phone"] = phone
    name = context.user_data["name"]
    log_activity(user.id, "تسجيل_جوال", digits[:4] + "***")

    await update.message.reply_text(
        f"ممتاز\n\nوالآن يا *{name}*، حدد نوع القطعة التراثية اللي تبي توثّقها اليوم 🏺",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(ITEM_TYPES, one_time_keyboard=True,
                                         resize_keyboard=True, input_field_placeholder="اختر نوع القطعة..."),
    )
    return ITEM_TYPE


# ══════════════════════════════════════════════════════════
# 🏺 اختيار نوع القطعة
# ══════════════════════════════════════════════════════════
async def get_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chosen = update.message.text.strip()
    user = update.effective_user

    if "أخرى" in chosen:
        await update.message.reply_text(
            "اكتب اسم القطعة التراثية 📝\nمثال: مفتاح قديم، صندوق خشبي...",
            parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
        )
        return ITEM_NAME

    parts = chosen.rsplit(" ", 1)
    item_name = parts[0] if len(parts) > 1 else chosen
    context.user_data["item_type"] = item_name
    context.user_data["item_name"] = item_name
    log_activity(user.id, "اختيار_قطعة", item_name)
    return await ask_first_photo(update, context)


async def get_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    item_name = update.message.text.strip()
    context.user_data["item_type"] = "أخرى"
    context.user_data["item_name"] = item_name
    log_activity(user.id, "اختيار_قطعة_يدوي", item_name)
    return await ask_first_photo(update, context)


# ══════════════════════════════════════════════════════════
# 📷 التصوير
# ══════════════════════════════════════════════════════════
async def ask_first_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    # حفظ المشارك في Supabase عند أول صورة (لدينا الاسم والجوال الآن)
    if "participant_id" not in context.user_data:
        pid = save_participant(
            user.id, user.username,
            context.user_data.get("name", ""),
            context.user_data.get("phone", ""),
        )
        context.user_data["participant_id"] = pid

    name = context.user_data.get("name", "")
    item = context.user_data["item_name"]
    item_type = context.user_data.get("item_type", item)
    step = PHOTO_STEPS[0]

    # ملخص المعلومات قبل البدء بالتصوير
    await update.message.reply_text(
        f"معلومات ممتازة ✅\n\n"
        f"المشارك: *{name}* 👤\n"
        f"القطعة: *{item}* 🏺\n"
        f"النوع: *{item_type}* 📂\n\n"
        "─────────────────\n"
        "وصلنا لأهم وأمتع جزء، التصوير 📸\n"
        "أهم نصيحة: الإضاءة الطبيعية هي الأفضل، ولا تستخدم الفلاش 💡\n"
        "─────────────────\n\n"
        f"الصورة *{step['num']}* — {step['angle']} 📸\n"
        f"{photo_progress(0)}\n\n"
        f"{step['instruction']}",
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove(),
    )
    return PHOTO_1


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    current_step = len(context.user_data["photos"])
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    await update.message.reply_text("جاري رفع الصورة.. ⏳")
    link = upload_to_cloudinary(bytes(file_bytes))

    if not link:
        log_activity(user.id, "خطأ_رفع", PHOTO_STEPS[current_step]["angle"])
        await update.message.reply_text(
            "حصل خطأ أثناء رفع الصورة ✖️\nأرسلها مرة ثانية."
        )
        return PHOTO_1 + current_step

    done = current_step + 1
    context.user_data["photos"].append({"angle": PHOTO_STEPS[current_step]["angle"], "url": link})
    log_activity(user.id, "رفع_صورة", f"{done}/٦")

    if done >= 6:
        await update.message.reply_text(
            f"اكتملت الصور ✅\n{photo_progress(6)}  ٦/٦\n\n"
            "ممتاز، تم رفع جميع الصور الست بنجاح 🎉",
            parse_mode="Markdown",
        )
        return await ask_story(update, context)

    ns = PHOTO_STEPS[current_step + 1]
    await update.message.reply_text(
        f"تم رفع الصورة {done}/٦ ✅\n{photo_progress(done)}\n\n"
        f"الصورة *{ns['num']}* — {ns['angle']} 📸\n{ns['instruction']}",
        parse_mode="Markdown",
    )
    return PHOTO_1 + current_step + 1


# ══════════════════════════════════════════════════════════
# 📖 خطوة القصة
# ══════════════════════════════════════════════════════════
async def ask_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    item = context.user_data["item_name"]
    name = context.user_data.get("name", "")
    await update.message.reply_text(
        f"نوّرتنا يا *{name}* 📖\n\n"
        f"الحين جاء وقت القصة.. خلّنا نعرف أكثر عن *{item}*:\n"
        "• كم عمرها تقريبًا؟ ومن وين جاتكم؟\n"
        "• هل لها ذكرى خاصة مع العائلة؟\n\n"
        "اكتب قصتها بأسلوبك، أو استخدم الذكاء الاصطناعي ليساعدك في صياغتها ✍️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("دع الذكاء الاصطناعي يساعدك (ينصح به للملف الصوتي) 🤖", callback_data="ai_help_story")]
        ]),
    )
    return STORY


async def get_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    story = update.message.text.strip()
    context.user_data["story"] = story
    log_activity(user.id, "تسجيل_قصة", story[:60])
    return await finish(update, context)




async def wrong_input_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "أحتاج *نص مكتوب* لقصة القطعة ⚠️\n\n"
        "اكتب القصة، أو اختر أحد الخيارات ✍️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("دع الذكاء الاصطناعي يساعدك 🤖", callback_data="ai_help_story")]
        ]),
    )
    return STORY


# ══════════════════════════════════════════════════════════
# ✨ الذكاء الاصطناعي للقصة
# ══════════════════════════════════════════════════════════
async def ai_story_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "أهلاً بك في مساعد القصة الذكي 🤖\n\n"
        "لا تقلق بشأن التعبير، فقط أعطني بعض الكلمات أو التفاصيل اللي تعرفها عن القطعة، وأنا بصيغها كقصة دافئة تصلح للتعليق الصوتي.\n\n"
        "اكتب كل ما تعرفه الآن 📝\n_(مثال: من ٧٠ سنة، كان يستخدمها جدي في مزرعته في أبها، غالية علينا)_",
        parse_mode="Markdown"
    )
    return AI_STORY_INPUT

async def get_ai_story_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    # نحصل على كائن الرسالة سواء جاء من نص أو من callback
    msg = update.message or update.callback_query.message
    user_details = ""

    if update.message:
        user_details = update.message.text.strip()
        context.user_data["ai_story_details"] = user_details  # نحفظها للإعادة
    else:
        user_details = context.user_data.get("ai_story_details", "")

    item_name = context.user_data["item_name"]
    item_type = context.user_data.get("item_type", item_name)
    
    log_activity(user.id, "معلومات_قصة_الذكاء", user_details[:50])
    await msg.chat.send_action("typing")
    
    # رسالة مخصصة لطلب القصة من OpenAI
    prompt = (
        f"لدي قطعة تراثية نوعها '{item_type}' واسمها '{item_name}'.\n"
        f"هذه المعلومات التي أعرفها عنها: '{user_details}'.\n\n"
        "اكتب قصة هذه القطعة بناءً على الشروط المحددة في النظام: دافئة، بأسلوب الراوي، تصلح للتعليق الصوتي، من ٣ إلى ٤ أسطر."
    )
    
    story_result = ask_gpt(prompt, [])  # نمرر تاريخ فارغ لأنها تعليمة مباشرة
    context.user_data["ai_generated_story"] = story_result
    
    await msg.reply_text(
        f"هذي القصة اللي صغتها لك ✨\n\n"
        f"_{story_result}_\n\n"
        "كيف تشوفها؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("اعتماد القصة ✅", callback_data="ai_story_accept")],
            [InlineKeyboardButton("إعادة صياغة بأسلوب مختلف 🔄", callback_data="ai_story_retry")],
            [InlineKeyboardButton("سأكتبها بنفسي ✏️", callback_data="ai_story_manual")]
        ]),
    )
    return AI_STORY_CONFIRM

async def ai_story_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data
    user = update.effective_user
    
    if choice == "ai_story_accept":
        context.user_data["story"] = context.user_data.get("ai_generated_story", "")
        log_activity(user.id, "اعتماد_قصة_ذكاء")
        return await finish(update, context)
        
    elif choice == "ai_story_retry":
        log_activity(user.id, "إعادة_صياغة_قصة")
        await query.message.reply_text("جاري كتابة صياغة جديدة، لحظات.. ⏳")
        return await get_ai_story_input(update, context)  # يستخدم التفاصيل المحفوظة
        
    elif choice == "ai_story_manual":
        log_activity(user.id, "تراجع_عن_الذكاء")
        await query.message.reply_text(
            "حسنًا، خذ وقتك واكتب القصة بأسلوبك الآن ✍️"
        )
        return STORY

    return AI_STORY_CONFIRM


# ══════════════════════════════════════════════════════════
# 🎉 الإنهاء
# ══════════════════════════════════════════════════════════
async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    # نحصل على كائن الرسالة سواء جاء من نص أو من callback
    msg = update.message or update.callback_query.message

    name = context.user_data["name"]
    item_name = context.user_data["item_name"]
    item_type = context.user_data.get("item_type", item_name)
    story = context.user_data.get("story", "")
    photos = context.user_data["photos"]
    participant_id = context.user_data["participant_id"]

    item_id = save_item(participant_id, item_type, item_name, story)
    for p in photos:
        if p["url"] != "—":
            save_photo(item_id, p["angle"], p["url"])

    log_activity(user.id, "اكتمال_قطعة", f"{item_name} — {len(photos)} صور")

    await msg.reply_text(
        f"شكرًا لك يا *{name}*، عظيم جدًا 🎉\n\n"
        f"ساهمت للتو في حفظ قطعة غالية ({item_name}) من الاندثار.\n"
        f"رفعنا {len([p for p in photos if p['url'] != '—'])} صور واضحة 📸\n"
        f"حفظنا بياناتك وقصتها بأمان ✅\n\n"
        f"*ما التالي؟*\n"
        f"فريقنا التقني سيبدأ الآن بتحويل صورك إلى مجسم ثلاثي الأبعاد (3D) لتكون جاهزة قريبًا لعدسات الواقع المعزز، تشوفها تتجسد أمامك وتسمع قصتها اللي صغناها معًا 🪄",
        parse_mode="Markdown",
    )

    await show_main_menu(msg, name)
    return MAIN_MENU


# ══════════════════════════════════════════════════════════
# ⚠️ معالجة الإدخال الخاطئ
# ══════════════════════════════════════════════════════════
async def wrong_input_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cs = len(context.user_data.get("photos", []))
    step = PHOTO_STEPS[cs] if cs < 6 else PHOTO_STEPS[5]
    await update.message.reply_text(
        f"أحتاج *صورة* مو نص ⚠️\n\nالصورة *{step['num']}* — {step['angle']} 📸\n{step['instruction']}",
        parse_mode="Markdown",
    )
    return PHOTO_1 + cs

async def wrong_input_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("أحتاج *اسمك* مو صورة ⚠️\n\nأرسل لي اسمك الكامل 📝", parse_mode="Markdown")
    return NAME

async def wrong_input_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("أحتاج *رقم الجوال* مو صورة ⚠️\n\nأدخل رقم جوالك 📱\nمثال: 0512345678", parse_mode="Markdown")
    return PHONE

async def wrong_input_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("أحتاج *اسم القطعة* مو صورة ⚠️\n\nاكتب اسم القطعة 📝", parse_mode="Markdown")
    return ITEM_NAME

async def wrong_input_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("أحتاج *كلمة السر* مو صورة ⚠️\n\nأدخل كلمة السر 🔐", parse_mode="Markdown")
    return PASSWORD


# ══════════════════════════════════════════════════════════
# 📊 أوامر الأدمن
# ══════════════════════════════════════════════════════════
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()
    activity_text = ""
    for action, details, ts in stats["recent_activity"]:
        t = ts[11:16] if len(ts) > 16 else ts
        d = ts[:10] if len(ts) > 10 else ""
        activity_text += f"• {action}: {details} ({d} {t})\n"
    if not activity_text:
        activity_text = "لا توجد أحداث بعد"

    await update.message.reply_text(
        f"📊 *إحصائيات بِكسلة*\n\n─────────────────\n"
        f"👥 المشاركين: *{stats['total_participants']}*\n"
        f"🏺 القطع: *{stats['total_items']}*\n"
        f"📸 الصور: *{stats['total_photos']}*\n"
        f"🏆 الأكثر شيوعًا: *{stats['top_type']}*\n"
        f"🚫 محاولات فاشلة: *{stats['failed_attempts']}*\n"
        f"─────────────────\n\n📋 *آخر ٥ أحداث:*\n{activity_text}",
        parse_mode="Markdown",
    )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🆔 رقم حسابك:\n\n`{update.effective_user.id}`\n\nأضفه كـ ADMIN\\_ID في Railway.",
        parse_mode="Markdown",
    )


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 هذا الأمر للأدمن فقط.")
        return

    await update.message.reply_text("⏳ جاري تجهيز الملفات...")

    exports = [
        {
            "name": "المشاركين", "emoji": "👥", "caption": "جدول المشاركين",
            "headers": ["الرقم", "تيليقرام_ID", "اليوزرنيم", "الاسم", "الجوال", "المدينة", "التاريخ"],
            "data": db.table("participants").select("id,telegram_id,telegram_username,name,phone,city,created_at").order("id").execute().data,
            "fields": ["id", "telegram_id", "telegram_username", "name", "phone", "city", "created_at"],
        },
        {
            "name": "القطع", "emoji": "🏺", "caption": "جدول القطع",
            "headers": ["الرقم", "participant_id", "النوع", "الاسم", "القصة", "الحالة", "التاريخ"],
            "data": db.table("items").select("id,participant_id,item_type,item_name,story,status,created_at").order("id").execute().data,
            "fields": ["id", "participant_id", "item_type", "item_name", "story", "status", "created_at"],
        },
        {
            "name": "الصور", "emoji": "📸", "caption": "جدول الصور",
            "headers": ["الرقم", "item_id", "الزاوية", "الرابط", "التاريخ"],
            "data": db.table("photos").select("id,item_id,angle,url,uploaded_at").order("id").execute().data,
            "fields": ["id", "item_id", "angle", "url", "uploaded_at"],
        },
        {
            "name": "السجل", "emoji": "📋", "caption": "سجل الأحداث",
            "headers": ["الرقم", "تيليقرام_ID", "الحدث", "التفاصيل", "التوقيت"],
            "data": db.table("activity_log").select("id,telegram_id,action,details,timestamp").order("id", desc=True).limit(100).execute().data,
            "fields": ["id", "telegram_id", "action", "details", "timestamp"],
        },
    ]

    for exp in exports:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(exp["headers"])
        for row in exp["data"]:
            w.writerow([row.get(f, "") for f in exp["fields"]])
        buf.seek(0)
        await update.message.reply_document(
            document=buf.getvalue().encode("utf-8-sig"),
            filename=f"بكسلة_{exp['name']}_{datetime.now().strftime('%Y%m%d')}.csv",
            caption=f"{exp['emoji']} {exp['caption']}",
        )

    await update.message.reply_text("تم التصدير ✅")


async def participants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 للأدمن فقط.")
        return
    rows = db.table("participants").select("name,telegram_username,phone,created_at").order("id", desc=True).limit(20).execute().data
    if not rows:
        await update.message.reply_text("لا يوجد مشاركين بعد.")
        return
    text = "👥 *آخر ٢٠ مشارك:*\n\n"
    for i, r in enumerate(rows, 1):
        name = r.get("name", "—")
        un = r.get("telegram_username") or "—"
        phone = r.get("phone") or "—"
        ca = (r.get("created_at") or "")[:10]
        text += f"{i}. *{name}* (@{un})\n   📱 {phone} — 📅 {ca}\n\n"
    await update.message.reply_text(text, parse_mode="Markdown")


async def item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 للأدمن فقط.")
        return
    if not context.args:
        await update.message.reply_text("استخدم: /item [رقم]")
        return
    try:
        iid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("أرسل رقم صحيح ✖️")
        return

    item_data = db.table("items").select("item_name,item_type,status,story,created_at,participant_id").eq("id", iid).execute().data
    if not item_data:
        await update.message.reply_text(f"ما لقيت قطعة برقم {iid} ✖️")
        return
    item = item_data[0]
    part_data = db.table("participants").select("name,telegram_username,phone").eq("id", item["participant_id"]).execute().data
    part = part_data[0] if part_data else {}
    photos = db.table("photos").select("angle,url").eq("item_id", iid).order("id").execute().data
    pt = "\n".join([f"• {p['angle']}: {p['url']}" for p in photos]) or "لا توجد صور"
    story_text = f"\n📖 *القصة:*\n{item.get('story')}\n" if item.get("story") else ""
    await update.message.reply_text(
        f"🔍 *القطعة #{iid}*\n\n🏺 *{item['item_name']}*\n📂 {item['item_type']}\n📊 {item['status']}\n"
        f"📅 {(item.get('created_at') or '')[:10]}\n"
        f"👤 *{part.get('name','—')}* (@{part.get('telegram_username') or '—'})\n"
        f"📱 {part.get('phone') or '—'}\n"
        f"{story_text}\n📸 *الصور:*\n{pt}",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════
# ❌ الإلغاء
# ══════════════════════════════════════════════════════════
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    log_activity(update.effective_user.id, "إلغاء")
    await update.message.reply_text("تم الإلغاء ✖️\nأرسل أي رسالة للبدء من جديد.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    cs = len(context.user_data["photos"])
    if cs == 5:
        context.user_data["photos"].append({"angle": PHOTO_STEPS[5]["angle"], "url": "—"})
        return await ask_story(update, context)
    await update.message.reply_text("⚠️ هذي الصورة مطلوبة، أرسلها.")
    return PHOTO_1 + cs


# ══════════════════════════════════════════════════════════
# 🚀 التشغيل
# ══════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start),
            MessageHandler(filters.PHOTO, start),
        ],
        states={
            PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, check_password),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_password),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(menu_callback),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.TEXT & ~filters.COMMAND, menu_command),
            ],
            NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_name),
            ],
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_phone),
            ],
            ITEM_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_type),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_item),
            ],
            ITEM_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_name),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_item),
            ],
            PHOTO_1: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            PHOTO_2: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            PHOTO_3: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            PHOTO_4: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            PHOTO_5: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            PHOTO_6: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo), CommandHandler("menu", menu_command), MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_photo)],
            STORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_story),
                CallbackQueryHandler(ai_story_start_callback, pattern="^ai_help_story$"),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_story),
            ],
            AI_STORY_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_ai_story_input),
                CommandHandler("menu", menu_command),
                MessageHandler(filters.ALL & ~filters.COMMAND, wrong_input_story),
            ],
            AI_STORY_CONFIRM: [
                CallbackQueryHandler(ai_story_confirm_callback),
                CommandHandler("menu", menu_command),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("myid", myid_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("participants", participants_command))
    app.add_handler(CommandHandler("item", item_command))
    app.add_handler(MessageHandler(filters.ALL, start))

    logger.info("🚀 بوت بِكسلة شغّال!")
    app.run_polling()


if __name__ == "__main__":
    main()
