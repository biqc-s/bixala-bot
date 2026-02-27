# ============================================================
#  سيرفر صفحة البحث — Bixala Search Server
#  يخدم search.html ويحقن إعدادات Supabase من متغيرات البيئة
# ============================================================

import os
from flask import Flask, Response

app = Flask(__name__)

# ── قراءة الإعدادات من متغيرات البيئة ──
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")


@app.route("/")
def index():
    """يقرأ search.html ويحقن إعدادات Supabase فيه."""
    with open("search.html", "r", encoding="utf-8") as f:
        html = f.read()

    # حقن الإعدادات بدل ملف config.js الخارجي
    config_script = (
        "<script>\n"
        f'const SUPABASE_URL      = "{SUPABASE_URL}";\n'
        f'const SUPABASE_ANON_KEY = "{SUPABASE_ANON_KEY}";\n'
        "</script>"
    )
    html = html.replace('<script src="config.js"></script>', config_script)

    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/health")
def health():
    """نقطة فحص صحة السيرفر."""
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
