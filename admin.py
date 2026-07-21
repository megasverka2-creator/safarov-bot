# -*- coding: utf-8 -*-
"""
admin.py — Yagona boshqaruv paneli (@safarovblog_bot).

/panel — butun tizimning jonli holati + barcha buyruqlar bo'limlarga
ajratilgan, bir bosishda ishlaydigan ko'rinishda.

bot.py:  import admin  →  admin.register(app)
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

log = logging.getLogger("admin")

TZ = ZoneInfo("Asia/Tashkent")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "agent.db"))


def _jload(name, default):
    try:
        with open(os.path.join(DATA_DIR, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _metrics():
    """Barcha modullardan jonli raqamlar (faqat o'qish, hech narsani o'zgartirmaydi)."""
    m = {}
    today = datetime.now(TZ).strftime("%Y-%m-%d")

    users = _jload("users.json", {})
    m["users"] = len(users)
    m["blocked"] = sum(1 for u in users.values() if u.get("blocked"))
    m["active7"] = "-"
    try:
        from datetime import timedelta
        days7 = {(datetime.now(TZ) - timedelta(days=i)).strftime("%Y-%m-%d")
                 for i in range(7)}
        m["active7"] = sum(1 for u in users.values()
                           if u.get("last_seen", "") in days7)
        m["new_today"] = sum(1 for u in users.values()
                             if u.get("first_seen") == today)
    except Exception:
        m["new_today"] = "-"

    kurs = _jload("kurs.json", {"users": {}})
    buyers = [u for u in kurs.get("users", {}).values()
              if u.get("paid") and not u.get("free_admin")]
    m["kurs_buyers"] = len(buyers)
    m["kurs_stars"] = len(buyers) * 10

    m["drafts"] = m["pub_today"] = m["api_today"] = "-"
    try:
        conn = sqlite3.connect(DB_PATH)
        m["drafts"] = conn.execute(
            "SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
        m["pub_today"] = conn.execute(
            "SELECT COUNT(*) FROM agent_posts WHERE status='published' "
            "AND created_at LIKE ?", (today + "%",)).fetchone()[0]
        try:
            row = conn.execute(
                "SELECT value FROM agent_meta WHERE key='api_calls'").fetchone()
            day = conn.execute(
                "SELECT value FROM agent_meta WHERE key='api_day'").fetchone()
            if day and day[0] == today and row:
                m["api_today"] = int(row[0])
            else:
                m["api_today"] = 0
        except Exception:
            m["api_today"] = "-"
        conn.close()
    except Exception as e:
        log.warning("Panel DB o'qishda xato: %s", e)
    return m


PANEL_TEMPLATE = """🏛 <b>SAFAROV TIZIMI — Boshqaruv paneli</b>
<i>{sana}</i>

📊 <b>Jonli holat</b>
👥 Foydalanuvchi: <b>{users}</b> (🚫 {blocked}) · Haftada faol: <b>{active7}</b> · Bugun yangi: <b>{new_today}</b>
📥 Kutayotgan postlar: <b>{drafts}</b> · Bugun chiqdi: <b>{pub_today}</b> · API: <b>{api_today}</b>
🎓 Kurs xaridorlari: <b>{kurs_buyers}</b> (⭐ {kurs_stars})

━━━━━━━━━━━━━━━
📰 <b>YANGILIKLAR AGENTI</b> (9 rubrika)
/agent_run — manbalarni tekshirish
/postlar — kutayotgan postlar ro'yxati
/agent_status — agent holati
/agent_sources — manbalar ro'yxati

🎨 <b>KANAL AGENTLARI</b>
/farosat — Farosatdan uchun 5 kuzatuv
/sutuur — Sutuur: satr yoki adabiyot hikoyasi

🎓 <b>MARKETING KURSI</b>
/kurs_stats — sotuvlar hisobi
/kurs — kursni ko'rish (admin bepul)

📊 <b>STATISTIKA</b>
/stats — bot statistikasi va grafik
/tekshir — bloklaganlarni aniqlash

📢 <b>OMMAVIY</b>
/xabar — barchaga xabar yuborish
/elon2 /golib2 /reset2 — 2-konkurs

━━━━━━━━━━━━━━━
💡 Bu panel: /panel · To'liq hujjat: strategiya faylida"""


async def cmd_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    m = _metrics()
    await update.message.reply_text(
        PANEL_TEMPLATE.format(sana=datetime.now(TZ).strftime("%d.%m.%Y %H:%M"),
                              **m),
        parse_mode="HTML")


def register(app):
    app.add_handler(CommandHandler("panel", cmd_panel))
    log.info("Boshqaruv paneli ulandi: /panel")
