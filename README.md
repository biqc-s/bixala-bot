<div align="center">

# 🏺 بِكسلة — Bixala Bot

**حفظ الإرث العائلي رقمياً**

بوت تليجرام ذكي لجمع وتوثيق المقتنيات التراثية السعودية

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)](https://core.telegram.org/bots)
[![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?logo=supabase)](https://supabase.com)
[![Deploy on Railway](https://img.shields.io/badge/Deploy-Railway-0B0D0E?logo=railway)](https://railway.app)

</div>

---

## 🎯 الفكرة

بِكسلة مشروع سعودي يحفظ الإرث العائلي رقمياً عن طريق:
1. جمع المقتنيات التراثية من العائلات (دلال قهوة، سجاجيد، خناجر، مباخر...)
2. تصويرها من **٦ زوايا** مختلفة
3. تحويلها إلى نماذج ثلاثية الأبعاد (3D)
4. إصدار شهادة رقمية لكل قطعة برقم مميز

> اسم **بِكسلة** مشتق من: **بكسل** (تقنية) + **أصالة** (تراث)

---

## ⚙️ التقنيات

| التقنية | الوظيفة |
|---------|---------|
| **Python + python-telegram-bot** | بوت تليجرام |
| **Supabase (PostgreSQL)** | قاعدة البيانات |
| **Cloudinary** | تخزين الصور |
| **OpenAI GPT** | الوكيل الذكي |
| **Railway** | الاستضافة |

---

## 🚀 التشغيل

### المتطلبات
- حساب [Supabase](https://supabase.com)
- حساب [Cloudinary](https://cloudinary.com)
- مفتاح [OpenAI API](https://platform.openai.com)
- بوت تليجرام من [@BotFather](https://t.me/BotFather)

### متغيرات البيئة

```env
BOT_TOKEN=your_telegram_bot_token
BOT_PASSWORD=your_password
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
ADMIN_ID=123456789
SUPPORT_USERNAME=@your_support
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_service_role_key
CLOUDINARY_CLOUD_NAME=your_cloud
CLOUDINARY_API_KEY=your_key
CLOUDINARY_API_SECRET=your_secret
```

### تشغيل محلي
```bash
pip install -r requirements.txt
python bixala_bot.py
```

---

## 📁 هيكل المشروع

```
bixala-bot/
├── bixala_bot.py       # البوت الرئيسي
├── search.html         # صفحة بحث القطع
├── config.example.js   # نموذج إعدادات البحث
├── requirements.txt    # المكتبات
├── runtime.txt         # إصدار Python
├── Procfile            # إعدادات Railway
└── .gitignore          # الملفات المستبعدة
```

---

## 📜 الرخصة

هذا المشروع للاستخدام الخاص. جميع الحقوق محفوظة.
