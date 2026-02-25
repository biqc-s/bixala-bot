# ============================================================
#  بوت بِكسلة — Bixala Bot
#  الوظيفة: يجمع صور المقتنيات التراثية من ٦ زوايا
#  ويرفعها ويحفظ كل العمليات في قاعدة بيانات داخلية
#  مع حماية بكلمة سر للمشاركين المصرّح لهم فقط
# ============================================================

# ──────────────────────────────────────────────────────────
# 📦 استيراد المكتبات المطلوبة
# ──────────────────────────────────────────────────────────
import logging
import os
import base64
import sqlite3           # قاعدة البيانات الداخلية — ما تحتاج تثبيت شيء
import requests
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# ──────────────────────────────────────────────────────────
# ⚙️ الإعدادات — تُضاف كـ Variables في Railway
# ──────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["BOT_TOKEN"]                          # توكن البوت
IMGBB_API_KEY = os.environ["IMGBB_API_KEY"]                  # مفتاح imgBB
BOT_PASSWORD = os.environ.get("BOT_PASSWORD", "bixala2026")  # كلمة السر الموحدة — غيّرها من Railway
AIRTABLE_FORM_URL = os.environ.get("AIRTABLE_FORM_URL", "")  # رابط الفورم (اختياري)
DB_PATH = os.environ.get("DB_PATH", "bixala_data.db")        # مسار قاعدة البيانات

# ──────────────────────────────────────────────────────────
# 🔢 تعريف مراحل المحادثة
# ──────────────────────────────────────────────────────────
(
    PASSWORD,       # 0 — إدخال كلمة السر
    NAME,           # 1 — كتابة الاسم
    ITEM_TYPE,      # 2 — اختيار نوع القطعة
    ITEM_NAME,      # 3 — كتابة اسم القطعة (إذا اختار "أخرى")
    PHOTO_1,        # 4 — صورة من الأمام
    PHOTO_2,        # 5 — صورة من الخلف
    PHOTO_3,        # 6 — صورة من الجانب الأيمن
    PHOTO_4,        # 7 — صورة من الجانب الأيسر
    PHOTO_5,        # 8 — صورة من الأعلى
    PHOTO_6,        # 9 — صورة تفاصيل مميزة
) = range(10)

# ──────────────────────────────────────────────────────────
# 🏺 أنواع القطع — تظهر كأزرار
# 💡 عدّل هنا إذا تبي تضيف أو تحذف أنواع
# ──────────────────────────────────────────────────────────
ITEM_TYPES = [
    ["دلة قهوة ☕", "مبخرة 🪔"],
    ["سجادة 🧶", "خنجر 🗡️"],
    ["أواني فخارية 🏺", "ملابس تراثية 👘"],
    ["حُلي ومجوهرات 💍", "أدوات حرفية 🔨"],
    ["أخرى ✏️"],
]

# ──────────────────────────────────────────────────────────
# 📸 إعدادات الزوايا الست
# ──────────────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────────────
# 📋 نظام تسجيل الأحداث
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════
# 🗄️ قاعدة البيانات الداخلية (SQLite)
# تحفظ كل العمليات: المشاركين، القطع، الصور، سجل الأحداث
# ══════════════════════════════════════════════════════════

def init_database():
    """
    تُنشئ جداول قاعدة البيانات إذا ما كانت موجودة.
    تُستدعى مرة وحدة عند تشغيل البوت.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ─── جدول المشاركين ───
    # يحفظ بيانات كل مشارك استخدم البوت
    c.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- رقم تسلسلي تلقائي
            telegram_id INTEGER,                     -- رقم حساب التيليقرام
            telegram_username TEXT,                   -- يوزرنيم التيليقرام
            name TEXT,                                -- الاسم اللي كتبه المشارك
            created_at TEXT                           -- تاريخ ووقت التسجيل
        )
    """)

    # ─── جدول القطع ───
    # يحفظ بيانات كل قطعة تم تصويرها
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- رقم تسلسلي تلقائي
            participant_id INTEGER,                  -- رقم المشارك (يربطها بجدول المشاركين)
            item_type TEXT,                          -- نوع القطعة (دلة، سجادة، إلخ)
            item_name TEXT,                          -- اسم القطعة
            status TEXT DEFAULT 'مكتمل',             -- حالة القطعة
            created_at TEXT,                         -- تاريخ ووقت الإضافة
            FOREIGN KEY (participant_id) REFERENCES participants(id)
        )
    """)

    # ─── جدول الصور ───
    # يحفظ رابط كل صورة والزاوية حقتها
    c.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,   -- رقم تسلسلي
            item_id INTEGER,                         -- رقم القطعة (يربطها بجدول القطع)
            angle TEXT,                              -- الزاوية (أمام، خلف، إلخ)
            url TEXT,                                -- رابط الصورة على imgBB
            uploaded_at TEXT,                         -- تاريخ ووقت الرفع
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)

    # ─── جدول سجل الأحداث ───
    # يحفظ كل حدث يصير في البوت (دخول، خروج، أخطاء، إلخ)
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,                     -- مين سوّى الحدث
            action TEXT,                             -- نوع الحدث
            details TEXT,                            -- تفاصيل إضافية
            timestamp TEXT                           -- التوقيت
        )
    """)

    conn.commit()
    conn.close()
    logger.info("🗄️ قاعدة البيانات جاهزة")


def log_activity(telegram_id: int, action: str, details: str = ""):
    """
    تسجّل أي حدث في سجل الأحداث.
    أمثلة: "دخول البوت"، "إدخال كلمة سر خاطئة"، "رفع صورة"، إلخ
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO activity_log (telegram_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
        (telegram_id, action, details, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def save_participant(telegram_id: int, username: str, name: str) -> int:
    """
    تحفظ بيانات المشارك وترجع رقمه في قاعدة البيانات.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO participants (telegram_id, telegram_username, name, created_at) VALUES (?, ?, ?, ?)",
        (telegram_id, username or "", name, datetime.now().isoformat())
    )
    participant_id = c.lastrowid  # رقم المشارك اللي انحفظ
    conn.commit()
    conn.close()
    return participant_id


def save_item(participant_id: int, item_type: str, item_name: str) -> int:
    """
    تحفظ بيانات القطعة وترجع رقمها.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO items (participant_id, item_type, item_name, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (participant_id, item_type, item_name, "مكتمل", datetime.now().isoformat())
    )
    item_id = c.lastrowid
    conn.commit()
    conn.close()
    return item_id


def save_photo(item_id: int, angle: str, url: str):
    """
    تحفظ رابط صورة مع الزاوية حقتها.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO photos (item_id, angle, url, uploaded_at) VALUES (?, ?, ?, ?)",
        (item_id, angle, url, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    """
    تجيب إحصائيات سريعة من قاعدة البيانات.
    تُستخدم في أمر /stats
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # عدد المشاركين
    c.execute("SELECT COUNT(*) FROM participants")
    total_participants = c.fetchone()[0]

    # عدد القطع
    c.execute("SELECT COUNT(*) FROM items")
    total_items = c.fetchone()[0]

    # عدد الصور
    c.execute("SELECT COUNT(*) FROM photos")
    total_photos = c.fetchone()[0]

    # أكثر نوع قطعة شيوعًا
    c.execute("SELECT item_type, COUNT(*) as cnt FROM items GROUP BY item_type ORDER BY cnt DESC LIMIT 1")
    top_type_row = c.fetchone()
    top_type = top_type_row[0] if top_type_row else "—"

    # عدد محاولات الدخول الفاشلة
    c.execute("SELECT COUNT(*) FROM activity_log WHERE action = 'كلمة_سر_خاطئة'")
    failed_attempts = c.fetchone()[0]

    # آخر ٥ أحداث
    c.execute("SELECT action, details, timestamp FROM activity_log ORDER BY id DESC LIMIT 5")
    recent_activity = c.fetchall()

    conn.close()

    return {
        "total_participants": total_participants,
        "total_items": total_items,
        "total_photos": total_photos,
        "top_type": top_type,
        "failed_attempts": failed_attempts,
        "recent_activity": recent_activity,
    }


# ══════════════════════════════════════════════════════════
# 🖼️ دالة رفع الصور على imgBB
# ══════════════════════════════════════════════════════════
def upload_to_imgbb(file_bytes: bytes) -> str | None:
    """يرفع صورة على imgBB ويرجع الرابط المباشر."""
    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                return data["data"]["url"]
    except Exception as e:
        logger.error(f"imgBB upload error: {e}")
    return None


# ══════════════════════════════════════════════════════════
# 🔧 دالة مساعدة — تطلب الصورة الأولى
# ══════════════════════════════════════════════════════════
async def ask_first_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        reply_markup=ReplyKeyboardRemove(),
    )
    return PHOTO_1


# ══════════════════════════════════════════════════════════
# 🟢 دالة البداية — ترحيب + طلب كلمة السر
# ══════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    context.user_data["photos"] = []

    # تسجيل الدخول في سجل الأحداث
    user = update.effective_user
    log_activity(user.id, "بداية_محادثة", f"@{user.username or 'بدون_يوزر'}")

    await update.message.reply_text(
        "✨ *أهلاً بك في بِكسلة!*\n\n"
        "نحن نحفظ الإرث العائلي رقميًا 🏺\n\n"
        "🔐 *أدخل كلمة السر للمتابعة:*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    # الانتقال لمرحلة كلمة السر
    return PASSWORD


# ══════════════════════════════════════════════════════════
# 🔐 دالة التحقق من كلمة السر
# إذا صحيحة ← يكمل، إذا خاطئة ← يطلب مرة ثانية
# ══════════════════════════════════════════════════════════
async def check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    entered = update.message.text.strip()

    # ─── كلمة السر صحيحة ───
    if entered == BOT_PASSWORD:
        log_activity(user.id, "كلمة_سر_صحيحة")

        await update.message.reply_text(
            "✅ تم التحقق بنجاح!\n\n"
            "📝 *أرسل لي اسمك الكامل:*",
            parse_mode="Markdown",
        )
        return NAME

    # ─── كلمة السر خاطئة ───
    log_activity(user.id, "كلمة_سر_خاطئة", f"أدخل: {entered}")

    # نحسب عدد المحاولات
    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1

    # إذا حاول ٣ مرات — أنهِ المحادثة
    if context.user_data["attempts"] >= 3:
        log_activity(user.id, "تم_الحظر", "٣ محاولات فاشلة")
        await update.message.reply_text(
            "🚫 تم تجاوز عدد المحاولات المسموحة.\n"
            "تواصل مع فريق بِكسلة للحصول على كلمة السر."
        )
        return ConversationHandler.END

    remaining = 3 - context.user_data["attempts"]
    await update.message.reply_text(
        f"❌ كلمة السر غير صحيحة.\n"
        f"متبقي لك *{remaining}* محاولات.\n\n"
        "🔐 *أدخل كلمة السر:*",
        parse_mode="Markdown",
    )
    return PASSWORD


# ══════════════════════════════════════════════════════════
# 👤 دالة استقبال الاسم
# ══════════════════════════════════════════════════════════
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    context.user_data["name"] = update.message.text.strip()
    name = context.user_data["name"]

    # حفظ المشارك في قاعدة البيانات
    participant_id = save_participant(user.id, user.username, name)
    context.user_data["participant_id"] = participant_id

    log_activity(user.id, "تسجيل_اسم", name)

    # عرض أزرار أنواع القطع
    await update.message.reply_text(
        f"أهلاً *{name}!* 👋\n\n"
        "🏺 *اختر نوع القطعة التراثية:*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            ITEM_TYPES,
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder="اختر نوع القطعة..."
        ),
    )
    return ITEM_TYPE


# ══════════════════════════════════════════════════════════
# 🏺 دالة استقبال نوع القطعة — من الأزرار
# ══════════════════════════════════════════════════════════
async def get_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chosen = update.message.text.strip()
    user = update.effective_user

    # إذا اختار "أخرى"
    if "أخرى" in chosen:
        await update.message.reply_text(
            "📝 *اكتب اسم القطعة التراثية:*\n"
            "مثال: مفتاح قديم، صندوق خشبي، مرآة نحاسية...",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ITEM_NAME

    # حفظ نوع القطعة (بدون الإيموجي)
    parts = chosen.rsplit(" ", 1)
    item_name = parts[0] if len(parts) > 1 else chosen
    context.user_data["item_type"] = item_name
    context.user_data["item_name"] = item_name

    log_activity(user.id, "اختيار_قطعة", item_name)

    return await ask_first_photo(update, context)


# ══════════════════════════════════════════════════════════
# ✏️ دالة استقبال اسم القطعة يدويًا (إذا اختار "أخرى")
# ══════════════════════════════════════════════════════════
async def get_item_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    item_name = update.message.text.strip()
    context.user_data["item_type"] = "أخرى"
    context.user_data["item_name"] = item_name

    log_activity(user.id, "اختيار_قطعة_يدوي", item_name)

    return await ask_first_photo(update, context)


# ══════════════════════════════════════════════════════════
# 📷 دالة معالجة الصور
# ══════════════════════════════════════════════════════════
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    current_step = len(context.user_data["photos"])

    # تحميل الصورة من تيليقرام
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    # رفعها على imgBB
    await update.message.reply_text("⏳ جاري رفع الصورة...")
    link = upload_to_imgbb(bytes(file_bytes))

    if not link:
        log_activity(user.id, "خطأ_رفع_صورة", f"الزاوية: {PHOTO_STEPS[current_step]['angle']}")
        await update.message.reply_text(
            "❌ حصل خطأ في الرفع. أرسل الصورة مرة ثانية."
        )
        return PHOTO_1 + current_step

    # حفظ الرابط
    context.user_data["photos"].append(
        {"angle": PHOTO_STEPS[current_step]["angle"], "url": link}
    )

    log_activity(user.id, "رفع_صورة", f"{current_step + 1}/٦ — {PHOTO_STEPS[current_step]['angle']}")

    await update.message.reply_text(f"✅ تم رفع الصورة {current_step + 1}/٦")

    # هل كملنا ٦ صور؟
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


# ══════════════════════════════════════════════════════════
# 🎉 دالة الإنهاء — تحفظ كل شيء في قاعدة البيانات
# ══════════════════════════════════════════════════════════
async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    name = context.user_data["name"]
    item_name = context.user_data["item_name"]
    item_type = context.user_data.get("item_type", item_name)
    photos = context.user_data["photos"]
    participant_id = context.user_data["participant_id"]

    # ─── حفظ القطعة في قاعدة البيانات ───
    item_id = save_item(participant_id, item_type, item_name)

    # ─── حفظ كل الصور في قاعدة البيانات ───
    for p in photos:
        if p["url"] != "—":
            save_photo(item_id, p["angle"], p["url"])

    log_activity(user.id, "اكتمال_قطعة", f"{item_name} — {len(photos)} صور")

    # ─── بناء رسالة الروابط ───
    links_text = ""
    for i, p in enumerate(photos, 1):
        links_text += f"{i}. {p['angle']}\n🔗 {p['url']}\n\n"

    all_urls = "\n".join([p["url"] for p in photos])

    await update.message.reply_text(
        f"🎉 *ممتاز {name}!*\n\n"
        f"تم رفع ٦ صور لـ *{item_name}* بنجاح!\n"
        "✅ تم حفظ البيانات في قاعدة بيانات بِكسلة\n\n"
        "─────────────────\n"
        f"📋 *روابط الصور:*\n\n"
        f"{links_text}"
        "─────────────────\n\n"
        "📋 *انسخ جميع الروابط:*",
        parse_mode="Markdown",
    )

    # رسالة الروابط للنسخ
    await update.message.reply_text(
        f"📎 روابط صور: {item_name}\n\n{all_urls}",
    )

    # رابط الفورم إذا موجود
    if AIRTABLE_FORM_URL:
        await update.message.reply_text(
            "📝 *الخطوة الأخيرة:*\n\n"
            "الصق الروابط في نموذج المشاركة 👇\n"
            f"🔗 {AIRTABLE_FORM_URL}\n\n"
            "شكرًا لمشاركتك في بِكسلة! 🙏✨\n\n"
            "لتصوير قطعة أخرى أرسل أي رسالة",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "شكرًا لمشاركتك في بِكسلة! 🙏✨\n\n"
            "لتصوير قطعة أخرى أرسل أي رسالة",
        )

    return ConversationHandler.END


# ══════════════════════════════════════════════════════════
# 📊 أمر الإحصائيات — /stats
# يعرض ملخص سريع لكل العمليات (لك أنت فقط)
# ══════════════════════════════════════════════════════════
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = get_stats()

    # بناء نص آخر ٥ أحداث
    activity_text = ""
    for action, details, timestamp in stats["recent_activity"]:
        # نعرض الوقت بشكل مختصر
        time_str = timestamp[11:16] if len(timestamp) > 16 else timestamp
        date_str = timestamp[:10] if len(timestamp) > 10 else ""
        activity_text += f"• {action}: {details} ({date_str} {time_str})\n"

    if not activity_text:
        activity_text = "لا توجد أحداث بعد"

    await update.message.reply_text(
        "📊 *إحصائيات بِكسلة*\n\n"
        "─────────────────\n"
        f"👥 عدد المشاركين: *{stats['total_participants']}*\n"
        f"🏺 عدد القطع: *{stats['total_items']}*\n"
        f"📸 عدد الصور: *{stats['total_photos']}*\n"
        f"🏆 أكثر نوع شيوعًا: *{stats['top_type']}*\n"
        f"🚫 محاولات دخول فاشلة: *{stats['failed_attempts']}*\n"
        "─────────────────\n\n"
        f"📋 *آخر ٥ أحداث:*\n{activity_text}",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════
# ❌ دالة الإلغاء
# ══════════════════════════════════════════════════════════
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    log_activity(user.id, "إلغاء_محادثة")

    await update.message.reply_text(
        "تم الإلغاء ❌\nتقدر تبدأ من جديد بإرسال أي رسالة",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════
# ⏭️ دالة تخطي الصورة
# ══════════════════════════════════════════════════════════
async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    current_step = len(context.user_data["photos"])

    if current_step == 5:
        context.user_data["photos"].append(
            {"angle": PHOTO_STEPS[5]["angle"], "url": "—"}
        )
        return await finish(update, context)

    await update.message.reply_text("⚠️ هذي الصورة مطلوبة. أرسل الصورة لو سمحت.")
    return PHOTO_1 + current_step


# ══════════════════════════════════════════════════════════
# 🚀 الدالة الرئيسية
# ══════════════════════════════════════════════════════════
def main():
    # إنشاء قاعدة البيانات عند التشغيل
    init_database()

    app = Application.builder().token(BOT_TOKEN).build()

    # ─── مسار المحادثة ───
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, start),
            MessageHandler(filters.PHOTO, start),
        ],
        states={
            # مرحلة كلمة السر
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)],
            # مرحلة الاسم
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            # مرحلة اختيار نوع القطعة
            ITEM_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_type)],
            # مرحلة كتابة اسم القطعة يدويًا
            ITEM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_item_name)],
            # مراحل الصور الست
            PHOTO_1: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
            PHOTO_2: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
            PHOTO_3: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
            PHOTO_4: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
            PHOTO_5: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
            PHOTO_6: [MessageHandler(filters.PHOTO, handle_photo), CommandHandler("skip", skip_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    # أمر الإحصائيات — تقدر تستخدمه في أي وقت
    app.add_handler(CommandHandler("stats", stats_command))

    # أي رسالة خارج المحادثة تبدأ البوت تلقائيًا
    app.add_handler(MessageHandler(filters.ALL, start))

    logger.info("🚀 بوت بِكسلة شغّال!")
    app.run_polling()


# ▶️ نقطة البداية
if __name__ == "__main__":
    main()
