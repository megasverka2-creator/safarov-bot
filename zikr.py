# -*- coding: utf-8 -*-
"""
ZIKR ESLATMA MODULI  (@safarovblog_bot)
=======================================
Ishlash tartibi:
  1. Foydalanuvchi /zikr bosadi -> obuna bo'ladi ("Yoqildi")
  2. Har kuni bot o'sha foydalanuvchi uchun 3 ta TASODIFIY vaqt tanlaydi
  3. Vaqt kelganda ro'yxatdan tasodifiy zikr yuboriladi + "Aytdim" tugmasi
  4. Tugma bosilsa xabar o'rnida faqat "Hammamiz bugun: N" qoladi
  5. Kunlik hisob 00:00 da nolga qaytadi, oylik hisob yig'ilib boradi
  6. Oy oxirida obunachilarga umumiy natija yuboriladi
  7. /zikr_off -> "To'xtadi"

MUHIM: bu yerda AI ISHLATILMAYDI. Zikr matnlari qat'iy ro'yxatdan olinadi,
shuning uchun noto'g'ri matn yozilishi mumkin emas va xarajat = $0.
"""

import logging
import os
import random
import sqlite3
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

log = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "."), "zikr.db")

# Kuniga nechta eslatma
PER_DAY = int(os.environ.get("ZIKR_PER_DAY", "3"))
# Tasodifiy vaqt shu oraliqdan tanlanadi (tunda bezovta qilmaslik uchun).
# To'liq sutka kerak bo'lsa: ZIKR_FROM=0, ZIKR_TO=23
HOUR_FROM = int(os.environ.get("ZIKR_FROM", "7"))
HOUR_TO = int(os.environ.get("ZIKR_TO", "22"))

# ======================================================================
# ZIKR RO'YXATI — qat'iy, AI tegmaydi
# ======================================================================
ZIKRLAR = [
    ("الحمد لله", "Alhamdulillah",
     "Barcha maqtov — hamd Allohnikidir!"),
    ("سبحان الله", "Subhanalloh",
     "Alloh pok va benuqsondir!"),
    ("الله أكبر", "Allohu Akbar",
     "Alloh eng buyukdir!"),
    ("أستغفر الله", "Astag'firulloh",
     "Allohdan mag'firat so'rayman!"),
    ("لا إله إلا الله محمد رسول الله", "La ilaha illalloh, Muhammadur Rasululloh",
     "Allohdan o'zga iloh yo'q, Muhammad Uning elchisidir!"),
]


def zikr_matni(arab, lotin, mano):
    return f"{arab}\n\n«{lotin} ({mano})», deb ayting."


# ======================================================================
# BAZA
# ======================================================================
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS zikr_users (
        uid INTEGER PRIMARY KEY,
        active INTEGER DEFAULT 1,
        joined_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS zikr_plan (
        uid INTEGER,
        kun TEXT,
        vaqt TEXT,
        yuborildi INTEGER DEFAULT 0,
        PRIMARY KEY (uid, kun, vaqt))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS zikr_meta (
        k TEXT PRIMARY KEY, v TEXT)""")
    conn.commit()
    conn.close()


def meta_get(conn, k, default=None):
    row = conn.execute("SELECT v FROM zikr_meta WHERE k=?", (k,)).fetchone()
    return row[0] if row else default


def meta_set(conn, k, v):
    conn.execute("INSERT OR REPLACE INTO zikr_meta (k, v) VALUES (?, ?)",
                 (k, str(v)))


# ======================================================================
# HISOBLAGICHLAR (kunlik + oylik)
# ======================================================================
def _bugun():
    return datetime.now(TZ).date().isoformat()


def _shu_oy():
    return datetime.now(TZ).strftime("%Y-%m")


def kunlik_hisob(conn):
    """Bugungi umumiy son. Kun almashgan bo'lsa nolga qaytadi."""
    if meta_get(conn, "kun_sana") != _bugun():
        meta_set(conn, "kun_sana", _bugun())
        meta_set(conn, "kun_soni", "0")
    return int(meta_get(conn, "kun_soni", "0"))


def oylik_hisob(conn):
    """Shu oydagi umumiy son. Oy almashgan bo'lsa nolga qaytadi.
    Nolga qaytishdan OLDIN o'tgan oy natijasi saqlanadi — aks holda
    bot 00:05 da o'chiq bo'lsa, oylik hisobot yo'qolib ketardi."""
    joriy = meta_get(conn, "oy_nomi")
    if joriy != _shu_oy():
        if joriy:
            meta_set(conn, "oy_zaxira_nomi", joriy)
            meta_set(conn, "oy_zaxira_soni", meta_get(conn, "oy_soni", "0"))
        meta_set(conn, "oy_nomi", _shu_oy())
        meta_set(conn, "oy_soni", "0")
    return int(meta_get(conn, "oy_soni", "0"))


def hisob_oshir(conn):
    """Bitta 'Aytdim' bosilishi — kunlik ham, oylik ham +1."""
    kun = kunlik_hisob(conn) + 1
    oy = oylik_hisob(conn) + 1
    meta_set(conn, "kun_soni", kun)
    meta_set(conn, "oy_soni", oy)
    return kun


def raqam(n):
    """3847 -> '3 847'"""
    return f"{n:,}".replace(",", " ")


# ======================================================================
# BUYRUQLAR
# ======================================================================
async def cmd_zikr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    conn = db()
    conn.execute(
        "INSERT INTO zikr_users (uid, active, joined_at) VALUES (?, 1, ?) "
        "ON CONFLICT(uid) DO UPDATE SET active=1",
        (uid, datetime.now(TZ).isoformat()))
    conn.commit()
    # bugungi kun uchun hali reja bo'lmasa — darrov tuzamiz
    _reja_tuz(conn, uid, _bugun())
    conn.commit()
    conn.close()
    await update.message.reply_text("Yoqildi")


async def cmd_zikr_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    conn = db()
    conn.execute("UPDATE zikr_users SET active=0 WHERE uid=?", (uid,))
    conn.execute("DELETE FROM zikr_plan WHERE uid=? AND yuborildi=0", (uid,))
    conn.commit()
    conn.close()
    await update.message.reply_text("To'xtadi")


async def on_aytdim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'Aytdim' bosildi — xabar o'rnida faqat umumiy hisob qoladi."""
    query = update.callback_query
    conn = db()
    kun = hisob_oshir(conn)
    conn.commit()
    conn.close()
    await query.answer()
    try:
        await query.edit_message_text(f"Hammamiz bugun: {raqam(kun)}")
    except BadRequest as e:
        log.warning("Zikr xabarini tahrirlab bo'lmadi: %s", e)


# ======================================================================
# REJA: har kuni har foydalanuvchiga PER_DAY ta tasodifiy vaqt
# ======================================================================
def _reja_tuz(conn, uid, kun):
    """Shu foydalanuvchiga shu kun uchun tasodifiy vaqtlar tuzadi.
    Reja allaqachon bor bo'lsa — tegmaydi."""
    bor = conn.execute(
        "SELECT COUNT(*) FROM zikr_plan WHERE uid=? AND kun=?",
        (uid, kun)).fetchone()[0]
    if bor:
        return
    hozir = datetime.now(TZ)
    vaqtlar = set()
    urinish = 0
    while len(vaqtlar) < PER_DAY and urinish < 60:
        urinish += 1
        soat = random.randint(HOUR_FROM, HOUR_TO)
        daqiqa = random.randint(0, 59)
        t = f"{soat:02d}:{daqiqa:02d}"
        # bugun uchun tuzilayotgan bo'lsa — o'tib ketgan vaqtni olmaymiz
        if kun == _bugun():
            if (soat, daqiqa) <= (hozir.hour, hozir.minute):
                continue
        vaqtlar.add(t)
    for t in vaqtlar:
        conn.execute(
            "INSERT OR IGNORE INTO zikr_plan (uid, kun, vaqt) VALUES (?, ?, ?)",
            (uid, kun, t))


async def job_kunlik_reja(context: ContextTypes.DEFAULT_TYPE):
    """Har kuni 00:05 da: eski rejani tozalaydi, yangisini tuzadi,
    oy almashgan bo'lsa oylik natijani yuboradi."""
    conn = db()
    kun = _bugun()
    kunlik_hisob(conn)          # kun almashgani uchun nolga qaytadi

    # --- oy almashdimi? ---
    oxirgi = meta_get(conn, "oy_xabar")      # oxirgi hisobot yuborilgan oy
    # o'tgan oy: yo hali nolga qaytmagan, yo zaxirada saqlangan
    otgan_oy = meta_get(conn, "oy_nomi")
    jami = int(meta_get(conn, "oy_soni", "0"))
    if otgan_oy == _shu_oy():
        otgan_oy = meta_get(conn, "oy_zaxira_nomi")
        jami = int(meta_get(conn, "oy_zaxira_soni", "0"))
    if otgan_oy and otgan_oy != _shu_oy() and oxirgi != otgan_oy:
        meta_set(conn, "oy_xabar", otgan_oy)
        meta_set(conn, "oy_nomi", _shu_oy())
        meta_set(conn, "oy_soni", "0")
        conn.commit()
        if jami > 0:
            await _oylik_xabar(context, conn, otgan_oy, jami)

    # --- eski rejalarni tozalash (3 kundan eski) ---
    chegara = (datetime.now(TZ).date() - timedelta(days=3)).isoformat()
    conn.execute("DELETE FROM zikr_plan WHERE kun < ?", (chegara,))

    # --- bugungi reja ---
    users = conn.execute(
        "SELECT uid FROM zikr_users WHERE active=1").fetchall()
    for (uid,) in users:
        _reja_tuz(conn, uid, kun)
    conn.commit()
    conn.close()
    log.info("Zikr: %d foydalanuvchiga %s kuni uchun reja tuzildi",
             len(users), kun)


OYLAR = {"01": "Yanvar", "02": "Fevral", "03": "Mart", "04": "Aprel",
         "05": "May", "06": "Iyun", "07": "Iyul", "08": "Avgust",
         "09": "Sentabr", "10": "Oktabr", "11": "Noyabr", "12": "Dekabr"}


async def _oylik_xabar(context, conn, oy_nomi, jami):
    """Oy yakunida obunachilarga umumiy natijani yuboradi."""
    nom = OYLAR.get(oy_nomi.split("-")[1], oy_nomi)
    matn = f"{nom} oyida birgalikda {raqam(jami)} marta zikr aytdik."
    users = conn.execute(
        "SELECT uid FROM zikr_users WHERE active=1").fetchall()
    yuborildi = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=matn)
            yuborildi += 1
        except Forbidden:
            conn.execute("UPDATE zikr_users SET active=0 WHERE uid=?", (uid,))
        except Exception as e:
            log.warning("Zikr oylik xabar (%s): %s", uid, e)
    conn.commit()
    log.info("Zikr: oylik xabar %d kishiga yuborildi", yuborildi)


# ======================================================================
# YUBORISH: har daqiqada vaqti kelganlarni tekshiradi
# ======================================================================
async def job_tekshir(context: ContextTypes.DEFAULT_TYPE):
    """Har daqiqada ishlaydi. Vaqti kelgan, hali yuborilmagan eslatmalarni
    yuboradi. Baza orqali ishlagani uchun qayta ishga tushishga chidamli."""
    hozir = datetime.now(TZ)
    kun = hozir.date().isoformat()
    vaqt = hozir.strftime("%H:%M")
    conn = db()
    navbat = conn.execute(
        "SELECT uid, vaqt FROM zikr_plan "
        "WHERE kun=? AND vaqt<=? AND yuborildi=0 LIMIT 100",
        (kun, vaqt)).fetchall()
    if not navbat:
        conn.close()
        return

    tugma = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Aytdim", callback_data="zikr_ok")]])
    for uid, t in navbat:
        arab, lotin, mano = random.choice(ZIKRLAR)
        try:
            await context.bot.send_message(
                chat_id=uid, text=zikr_matni(arab, lotin, mano),
                reply_markup=tugma)
        except Forbidden:
            # bloklagan — ro'yxatdan chiqadi
            conn.execute("UPDATE zikr_users SET active=0 WHERE uid=?", (uid,))
            conn.execute("DELETE FROM zikr_plan WHERE uid=? AND yuborildi=0",
                         (uid,))
            log.info("Zikr: %s bloklagan, ro'yxatdan chiqarildi", uid)
            continue
        except Exception as e:
            log.warning("Zikr yuborishda xato (%s): %s", uid, e)
        conn.execute(
            "UPDATE zikr_plan SET yuborildi=1 WHERE uid=? AND kun=? AND vaqt=?",
            (uid, kun, t))
    conn.commit()
    conn.close()


# ======================================================================
# RO'YXATGA OLISH
# ======================================================================
def register(app: Application):
    """bot.py dan chaqiriladi: zikr.register(app)"""
    init_db()
    app.add_handler(CommandHandler("zikr", cmd_zikr))
    app.add_handler(CommandHandler("zikr_off", cmd_zikr_off))
    app.add_handler(CallbackQueryHandler(on_aytdim, pattern=r"^zikr_ok$"))

    jq = getattr(app, "job_queue", None)
    if jq is None:
        log.warning("job_queue yo'q — zikr eslatmalari ishlamaydi.")
        return
    jq.run_daily(job_kunlik_reja, time=dtime(0, 5, tzinfo=TZ),
                 name="zikr_reja")
    jq.run_repeating(job_tekshir, interval=60, first=20, name="zikr_tekshir")
    log.info("Zikr moduli yoqildi (kuniga %d ta, %02d:00-%02d:00 oralig'ida)",
             PER_DAY, HOUR_FROM, HOUR_TO)
