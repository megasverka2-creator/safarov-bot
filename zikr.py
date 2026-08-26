# -*- coding: utf-8 -*-
"""
ZIKR ESLATMA MODULI  (@safarovblog_bot)
=======================================
Ishlash tartibi:
  1. Foydalanuvchi /zikr bosadi -> obuna bo'ladi ("Yoqildi")
  2. Har kuni bot o'sha foydalanuvchi uchun ZIKR_PER_DAY ta TASODIFIY
     vaqt tanlaydi (standart 5) va har vaqtga TAKRORSIZ zikr biriktiradi —
     ya'ni beshala zikr ham kun davomida aynan bir martadan keladi
  3. Vaqt kelganda rejadagi zikr yuboriladi + "Aytdim" tugmasi
  4. Tugma TASBEHDEK ZIKR_TAKROR marta bosiladi (standart 3).
     Har bosishda tasbeh chizig'i to'ladi: ○○○ -> ●○○ -> ●●○ -> ●●●
     Oxirgi bosishda xabar o'rnida "Hammamiz bugun: N" qoladi.
  5. Kunning BARCHA eslatmalari to'liq aytib bo'linganda — yakuniy xabar
     (ketma-ketlik + kunlik natija). Unga vaqti-vaqti bilan "Yaqinlaringizni
     taklif qiling" tugmasi qo'shiladi (har kuni emas — ZIKR_TAKLIF_KUN
     kunda bir). Tugma bosilganda bot UZATISH uchun tayyor xabar
     yuboradi: obunachi uni yaqinlariga forward qiladi, uzatilgan
     xabarda esa "Qo'shilish" tugmasi saqlanib qoladi. Do'st havolani
     ochib, keyin START qidirib o'tirmaydi — bir bosishda qo'shiladi.
     Usulni ZIKR_TAKLIF_USUL bilan almashtirish mumkin: uzatish
     (standart) / inline (BotFather'da /setinline shart) / havola.
  6. Kunlik hisob 00:00 da nolga qaytadi, oylik hisob yig'ilib boradi
  7. Oy oxirida obunachilarga umumiy natija yuboriladi
  8. /zikr_off -> "To'xtadi"

MUHIM: bu yerda AI ISHLATILMAYDI. Zikr matnlari qat'iy ro'yxatdan olinadi,
shuning uchun noto'g'ri matn yozilishi mumkin emas va xarajat = $0.
Taklif matni ham qo'lda yozilgan — hech qanday diniy hukm yoki savob va'dasi
yo'q, faqat samimiy chaqiruv.
"""

import logging
import os
import random
import sqlite3
from io import BytesIO
from urllib.parse import quote
from datetime import datetime, date, time as dtime, timedelta
from zoneinfo import ZoneInfo

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InlineQueryResultArticle, InputTextMessageContent,
)
from telegram.error import Forbidden, BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
)

try:  # Pillow — kanal banneri uchun. Bo'lmasa modul banner'siz ishlayveradi.
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except Exception:
    Image = None

log = logging.getLogger(__name__)
TZ = ZoneInfo("Asia/Tashkent")

DB_PATH = os.path.join(os.environ.get("DATA_DIR", "."), "zikr.db")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")

# Kuniga nechta eslatma
PER_DAY = int(os.environ.get("ZIKR_PER_DAY", "5"))
# Bitta eslatma nechta marta aytiladi (tasbeh). 1 qilinsa — eski tartib.
TAKROR = max(1, int(os.environ.get("ZIKR_TAKROR", "3")))
# Taklif tugmasi necha kunda bir ko'rsatilsin (0 = umuman ko'rsatilmasin)
TAKLIF_HAR = int(os.environ.get("ZIKR_TAKLIF_KUN", "7"))
# Tasodifiy vaqt shu oraliqdan tanlanadi (tunda bezovta qilmaslik uchun).
# To'liq sutka kerak bo'lsa: ZIKR_FROM=0, ZIKR_TO=23
HOUR_FROM = int(os.environ.get("ZIKR_FROM", "7"))
HOUR_TO = int(os.environ.get("ZIKR_TO", "22"))

_SONLAR = {1: "bir", 2: "ikki", 3: "uch", 4: "to'rt", 5: "besh",
           6: "olti", 7: "yetti", 8: "sakkiz", 9: "to'qqiz", 10: "o'n"}


def son_soz(n):
    """4 -> "to'rt". Ro'yxatda bo'lmasa raqamning o'zi qaytadi."""
    return _SONLAR.get(int(n), str(n))


CHANNEL_ID = os.environ.get("CHANNEL_ID", "@safaroov_blog")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "safarovblog_bot")

# Taklif qanday ketadi (ZIKR_TAKLIF_USUL):
#   "uzatish" (standart) — bot sizga TAYYOR xabar yuboradi, siz uni
#                 yaqinlaringizga uzatasiz. Uzatilgan xabarda "Qo'shilish"
#                 tugmasi saqlanadi. Hech qanday qo'shimcha sozlama
#                 talab qilmaydi — shuning uchun standart shu.
#   "inline"    — tugma chat tanlash oynasini ochadi va xabarni o'zi
#                 yuboradi (bir qadam kam). LEKIN BotFather'da inline
#                 rejim yoqilgan bo'lishi SHART: /setinline -> botni
#                 tanlang. Yoqilmasa do'stga faqat "@bot_nomi" degan
#                 matn tushadi — foydasi yo'q.
#   "havola"    — eski usul: t.me/share havolasi, tugmasiz oddiy matn.
TAKLIF_USUL = os.environ.get("ZIKR_TAKLIF_USUL", "uzatish").strip().lower()
if TAKLIF_USUL not in ("uzatish", "inline", "havola"):
    TAKLIF_USUL = "uzatish"

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


def tasbeh(bosildi, jami=None):
    """0,3 -> '○○○'   1,3 -> '●○○'   3,3 -> '●●●'"""
    jami = jami or TAKROR
    bosildi = max(0, min(bosildi, jami))
    return "●" * bosildi + "○" * (jami - bosildi)


def zikr_matni(arab, lotin, mano, bosildi=0):
    matn = f"{arab}\n\n«{lotin} ({mano})», deb ayting."
    if TAKROR > 1:
        matn += f"\n\n{tasbeh(bosildi)}   {bosildi}/{TAKROR}"
    return matn


def _tugma(kun, vaqt):
    """Callback ichida kun va vaqt — qaysi eslatma ekani aniq bo'lsin."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Aytdim", callback_data=f"zikr_ok|{kun}|{vaqt}")]])


# ======================================================================
# BAZA
# ======================================================================
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ustun(conn, jadval, nom, tur):
    """Mavjud bazaga ustun qo'shish (eski bazani buzmasdan)."""
    try:
        conn.execute(f"ALTER TABLE {jadval} ADD COLUMN {nom} {tur}")
    except sqlite3.OperationalError:
        pass  # allaqachon bor


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
    # kunlik yakun bir martadan ortiq yuborilmasligi uchun
    conn.execute("""CREATE TABLE IF NOT EXISTS zikr_yakun (
        uid INTEGER, kun TEXT, PRIMARY KEY (uid, kun))""")

    # --- migratsiya: yangi ustunlar ---
    _ustun(conn, "zikr_plan", "bosildi", "INTEGER DEFAULT 0")
    _ustun(conn, "zikr_plan", "zikr_idx", "INTEGER DEFAULT -1")
    _ustun(conn, "zikr_users", "streak", "INTEGER DEFAULT 0")
    _ustun(conn, "zikr_users", "oxirgi_kun", "TEXT")
    _ustun(conn, "zikr_users", "oxirgi_taklif", "TEXT")
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


# ======================================================================
# "AYTDIM" — tasbehdek TAKROR marta bosiladi
# ======================================================================
async def on_aytdim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data or ""
    bolak = data.split("|")

    conn = db()
    row = None
    kun = vaqt = None
    if len(bolak) == 3:
        kun, vaqt = bolak[1], bolak[2]
        row = conn.execute(
            "SELECT bosildi, zikr_idx FROM zikr_plan "
            "WHERE uid=? AND kun=? AND vaqt=?", (uid, kun, vaqt)).fetchone()

    # Eski format (zikr_ok) yoki reja tozalangan — bir marta hisoblab yopamiz
    if row is None:
        kunlik = hisob_oshir(conn)
        conn.commit()
        conn.close()
        await query.answer()
        try:
            await query.edit_message_text(f"Hammamiz bugun: {raqam(kunlik)}")
        except BadRequest as e:
            log.warning("Zikr xabarini tahrirlab bo'lmadi: %s", e)
        return

    bosildi, idx = int(row[0] or 0), int(row[1] or 0)
    if bosildi >= TAKROR:                      # ikki marta bosib yuborilgan
        conn.close()
        await query.answer()
        return

    bosildi += 1
    conn.execute(
        "UPDATE zikr_plan SET bosildi=? WHERE uid=? AND kun=? AND vaqt=?",
        (bosildi, uid, kun, vaqt))
    kunlik = hisob_oshir(conn)
    conn.commit()
    await query.answer()

    # --- hali tasbeh to'lmadi ---
    if bosildi < TAKROR:
        arab, lotin, mano = ZIKRLAR[idx % len(ZIKRLAR)]
        try:
            await query.edit_message_text(
                zikr_matni(arab, lotin, mano, bosildi),
                reply_markup=_tugma(kun, vaqt))
        except BadRequest as e:
            log.warning("Zikr tasbehini yangilab bo'lmadi: %s", e)
        conn.close()
        return

    # --- bu eslatma to'liq aytildi ---
    try:
        await query.edit_message_text(f"Hammamiz bugun: {raqam(kunlik)}")
    except BadRequest as e:
        log.warning("Zikr xabarini tahrirlab bo'lmadi: %s", e)

    # --- kunning hamma eslatmasi tugadimi? ---
    if _kun_yakunlandimi(conn, uid, kun):
        streak = _streak_yangila(conn, uid, kun)
        taklif = _taklif_vaqtimi(conn, uid, kun)
        if taklif:
            conn.execute("UPDATE zikr_users SET oxirgi_taklif=? WHERE uid=?",
                         (kun, uid))
        conn.commit()
        await _kun_yakun_xabar(context, uid, kun, streak, kunlik, taklif)
    conn.commit()
    conn.close()


# ======================================================================
# KUNLIK YAKUN
# ======================================================================
def _kun_yakunlandimi(conn, uid, kun):
    """Shu kundagi barcha eslatmalar yuborilgan VA har biri TAKROR marta
    bosilgan bo'lsa — True. Faqat bir marta True qaytaradi."""
    row = conn.execute(
        "SELECT COUNT(*), "
        "       SUM(CASE WHEN yuborildi=1 THEN 1 ELSE 0 END), "
        "       SUM(CASE WHEN bosildi>=? THEN 1 ELSE 0 END) "
        "FROM zikr_plan WHERE uid=? AND kun=?",
        (TAKROR, uid, kun)).fetchone()
    jami = int(row[0] or 0)
    yuborilgan = int(row[1] or 0)
    tugagan = int(row[2] or 0)
    if jami == 0 or yuborilgan < jami or tugagan < jami:
        return False
    if conn.execute("SELECT 1 FROM zikr_yakun WHERE uid=? AND kun=?",
                    (uid, kun)).fetchone():
        return False                            # allaqachon yuborilgan
    conn.execute("INSERT OR IGNORE INTO zikr_yakun (uid, kun) VALUES (?, ?)",
                 (uid, kun))
    return True


def _streak_yangila(conn, uid, kun):
    """Ketma-ket to'liq kunlar soni."""
    row = conn.execute(
        "SELECT streak, oxirgi_kun FROM zikr_users WHERE uid=?",
        (uid,)).fetchone()
    streak = int(row[0] or 0) if row else 0
    oxirgi = row[1] if row else None
    if oxirgi == kun:
        return streak or 1
    try:
        kecha = (date.fromisoformat(kun) - timedelta(days=1)).isoformat()
    except Exception:
        kecha = None
    streak = streak + 1 if (oxirgi and oxirgi == kecha) else 1
    conn.execute("UPDATE zikr_users SET streak=?, oxirgi_kun=? WHERE uid=?",
                 (streak, kun, uid))
    return streak


def _taklif_vaqtimi(conn, uid, kun):
    """Taklif tugmasi HAR KUNI chiqmaydi — birinchi to'liq kunda, keyin
    TAKLIF_HAR kunda bir marta. Aks holda zerikartiradi."""
    if TAKLIF_HAR <= 0:
        return False
    row = conn.execute("SELECT oxirgi_taklif FROM zikr_users WHERE uid=?",
                       (uid,)).fetchone()
    oxirgi = row[0] if row else None
    if not oxirgi:
        return True
    try:
        farq = (date.fromisoformat(kun) - date.fromisoformat(oxirgi)).days
    except Exception:
        return True
    return farq >= TAKLIF_HAR


# --- Taklif matni va tugmasi -------------------------------------------
# DIQQAT: quyidagi TAKLIF_MATNI — kanal egasi (Muslim Safarov) tomonidan
# yozilgan va tasdiqlangan matn. Ichida hadis rivoyati bor.
# AI bu matnni YOZMAYDI, O'ZGARTIRMAYDI, QISQARTIRMAYDI.
# Tahrir kerak bo'lsa — faqat egasi qo'li bilan, shu joyda.
TAKLIF_MATNI = (
    "Halqamiz qanchalik keng bo‘lsa, hayotimiz shunchalar nurli bo‘ladi.\n\n"
    "Yaqinlaringizga ham ilining va ikki karra yaxshilik sohibi bo‘ling.\n\n"
    "Abu Mas’ud Ansoriy roziyallohu anhudan rivoyat qilinadi:\n\n"
    "«Nabiy sollallohu alayhi vasallam: “Kim bir yaxshilikka dalolat qilsa, "
    "unga o‘sha yaxshilikni qilganning ajridek ajr beriladi”, dedilar».\n\n"
    "Muslim rivoyat qilgan."
)

ULASH_MATNI = (f"Zikr halqasi. Kun davomida {son_soz(PER_DAY)} marta qisqa "
               f"eslatma keladi — aytasiz va tugmani bosasiz, xolos. "
               f"Qo'shilasizmi?")


def _qoshilish_tugma():
    """Do'stga boradigan xabardagi tugma — bosilsa bot ochiladi va
    /start zikr ishga tushadi (bot.py shu argumentni tushunadi)."""
    return InlineKeyboardMarkup([[InlineKeyboardButton(
        "Qo'shilish", url=f"https://t.me/{BOT_USERNAME}?start=zikr")]])


def _taklif_tugma():
    """Obunachi bosadigan "taklif qilish" tugmasi. Usul TAKLIF_USUL bilan
    tanlanadi — yuqoridagi izohga qarang."""
    if TAKLIF_USUL == "uzatish":
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            "Yaqinlaringizni taklif qiling", callback_data="zikr_taklif")]])
    if TAKLIF_USUL == "inline":
        # Bo'sh so'rov: chat tanlanishi bilan taklif kartasi darrov chiqadi
        return InlineKeyboardMarkup([[InlineKeyboardButton(
            "Yaqinlaringizni taklif qiling", switch_inline_query="")]])
    havola = f"https://t.me/{BOT_USERNAME}?start=zikr"
    ulash = (f"https://t.me/share/url?url={quote(havola, safe='')}"
             f"&text={quote(ULASH_MATNI, safe='')}")
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Yaqinlaringizni taklif qiling", url=ulash)]])


UZATISH_KORSATMA = (
    "Quyidagi xabarni yaqinlaringizga uzating (forward) 👇\n\n"
    "Ular xabar ostidagi tugmani bosishi kifoya — havolani ochib, "
    "keyin qidirib o'tirmaydi."
)


async def on_taklif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """"Taklif qiling" bosilganda: uzatish uchun tayyor xabar yuboriladi.

    Nega shunday: uzatilgan (forward) xabarda inline tugma saqlanadi.
    Ya'ni do'st oddiy havolani emas, "Qo'shilish" tugmasini ko'radi va
    bir bosishda botga tushadi. Bu usul hech qanday qo'shimcha sozlama
    talab qilmaydi — inline rejimdan farqli."""
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    try:
        await context.bot.send_message(chat_id=uid, text=UZATISH_KORSATMA)
        await context.bot.send_message(chat_id=uid, text=ULASH_MATNI,
                                       reply_markup=_qoshilish_tugma())
    except Forbidden:
        pass
    except Exception as e:
        log.warning("Taklif xabari yuborilmadi (%s): %s", uid, e)


async def on_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline so'rov: taklif kartasini qaytaradi.

    Foydalanuvchi chatni tanlagach shu natija ko'rinadi; bosilganda
    do'stga ULASH_MATNI va "Qo'shilish" tugmasi ketadi.

    So'rov matni tekshirilmaydi — bu botda inline rejimning yagona
    vazifasi shu taklif."""
    natija = InlineQueryResultArticle(
        id="zikr_taklif",
        title="Zikr halqasiga taklif qilish",
        description="Do'stingizga qo'shilish tugmasi bilan xabar ketadi",
        input_message_content=InputTextMessageContent(ULASH_MATNI),
        reply_markup=_qoshilish_tugma(),
    )
    try:
        await update.inline_query.answer([natija], cache_time=300)
    except Exception as e:
        log.warning("Inline taklif javobi ketmadi: %s", e)


async def _kun_yakun_xabar(context, uid, kun, streak, kunlik, taklif):
    qatorlar = ["Bugungi halqa to'ldi."]
    if streak >= 2:
        qatorlar.append(f"Ketma-ket {streak}-kun.")
    qatorlar.append(f"Hammamiz bugun: {raqam(kunlik)} marta.")
    if taklif:
        qatorlar.append("\n" + TAKLIF_MATNI)
    matn = "\n".join(qatorlar)
    try:
        await context.bot.send_message(
            chat_id=uid, text=matn,
            reply_markup=_taklif_tugma() if taklif else None)
    except Forbidden:
        pass
    except Exception as e:
        log.warning("Zikr yakuniy xabari (%s): %s", uid, e)


# ======================================================================
# REJA: har kuni har foydalanuvchiga PER_DAY ta tasodifiy vaqt
# ======================================================================
def _zikr_tartibi(nechta):
    """Zikrlarni TAKRORSIZ taqsimlaydi: ro'yxat aralashtiriladi va navbat
    bilan beriladi. PER_DAY=5 bo'lsa — beshalasi ham aynan bir martadan.
    PER_DAY 5 dan kam bo'lsa — tasodifiy shuncha tasi (baribir takrorsiz).
    5 dan ko'p bo'lsa — ro'yxat qaytadan aralashtirilib davom etadi."""
    tartib = []
    while len(tartib) < nechta:
        bolak = list(range(len(ZIKRLAR)))
        random.shuffle(bolak)
        tartib.extend(bolak)
    return tartib[:nechta]


def _reja_tuz(conn, uid, kun):
    """Shu foydalanuvchiga shu kun uchun tasodifiy vaqtlar tuzadi va har
    vaqtga TAKRORSIZ zikr biriktiradi. Reja bor bo'lsa — tegmaydi."""
    bor = conn.execute(
        "SELECT COUNT(*) FROM zikr_plan WHERE uid=? AND kun=?",
        (uid, kun)).fetchone()[0]
    if bor:
        return
    hozir = datetime.now(TZ)
    vaqtlar = set()
    urinish = 0
    while len(vaqtlar) < PER_DAY and urinish < 200:
        urinish += 1
        soat = random.randint(HOUR_FROM, HOUR_TO)
        daqiqa = random.randint(0, 59)
        t = f"{soat:02d}:{daqiqa:02d}"
        # bugun uchun tuzilayotgan bo'lsa — o'tib ketgan vaqtni olmaymiz
        if kun == _bugun():
            if (soat, daqiqa) <= (hozir.hour, hozir.minute):
                continue
        vaqtlar.add(t)

    vaqtlar = sorted(vaqtlar)
    tartib = _zikr_tartibi(len(vaqtlar))
    for t, idx in zip(vaqtlar, tartib):
        conn.execute(
            "INSERT OR IGNORE INTO zikr_plan (uid, kun, vaqt, zikr_idx) "
            "VALUES (?, ?, ?, ?)", (uid, kun, t, idx))


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
    conn.execute("DELETE FROM zikr_yakun WHERE kun < ?", (chegara,))

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
            await context.bot.send_message(chat_id=uid, text=matn,
                                           reply_markup=_taklif_tugma())
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
        "SELECT uid, vaqt, zikr_idx FROM zikr_plan "
        "WHERE kun=? AND vaqt<=? AND yuborildi=0 LIMIT 100",
        (kun, vaqt)).fetchall()
    if not navbat:
        conn.close()
        return

    for uid, t, saqlangan in navbat:
        # reja tuzilganda biriktirilgan zikr. Eski qatorlarda (-1) yo'q —
        # o'shanda tasodifiy olinadi.
        idx = int(saqlangan) if saqlangan is not None and int(saqlangan) >= 0 \
            else random.randrange(len(ZIKRLAR))
        arab, lotin, mano = ZIKRLAR[idx % len(ZIKRLAR)]
        try:
            await context.bot.send_message(
                chat_id=uid, text=zikr_matni(arab, lotin, mano, 0),
                reply_markup=_tugma(kun, t))
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
            "UPDATE zikr_plan SET yuborildi=1, zikr_idx=?, bosildi=0 "
            "WHERE uid=? AND kun=? AND vaqt=?", (idx, uid, kun, t))
    conn.commit()
    conn.close()


# ======================================================================
# SINOV BUYRUQLARI (faqat admin)
# ======================================================================
async def cmd_zikr_sinov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/zikr_sinov — o'zingizga darhol bitta eslatma yuboradi.
    Reja jadvaliga yozilmaydi, shuning uchun kunlik yakunga ta'sir qilmaydi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    idx = random.randrange(len(ZIKRLAR))
    arab, lotin, mano = ZIKRLAR[idx]
    conn = db()
    kun, t = _bugun(), "00:00"
    conn.execute(
        "INSERT OR REPLACE INTO zikr_plan (uid, kun, vaqt, yuborildi, "
        "bosildi, zikr_idx) VALUES (?, ?, ?, 1, 0, ?)",
        (update.effective_user.id, kun, t, idx))
    conn.commit()
    conn.close()
    await update.message.reply_text(zikr_matni(arab, lotin, mano, 0),
                                    reply_markup=_tugma(kun, t))


async def cmd_zikr_yakun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/zikr_yakun — kunlik yakuniy xabarni taklif tugmasi bilan ko'rsatadi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    conn = db()
    kunlik = kunlik_hisob(conn)
    conn.close()
    await _kun_yakun_xabar(context, update.effective_user.id, _bugun(),
                           4, kunlik, True)


# ======================================================================
# KANAL BANNERI — /zikr_elon
# ======================================================================
_FONT_B = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
           "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]
_FONT_R = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
           "/usr/share/fonts/dejavu/DejaVuSans.ttf",
           "/System/Library/Fonts/Supplemental/Arial.ttf"]


def _fnt(paths, size):
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def make_banner(kanal=None):
    """Kanal uchun banner (1280x720). Mini App bilan bir xil binafsha-lavanda uslub.
    Arabcha matn QO'YILMAYDI — Pillow arab harflarini to'g'ri ulamaydi."""
    if Image is None:
        return None
    kanal = kanal or CHANNEL_ID
    W, H = 1280, 720
    LAV, LAV_DIM = (210, 195, 246), (150, 138, 182)
    img = Image.new("RGB", (W, H), (15, 10, 28))
    d = ImageDraw.Draw(img)
    for y in range(H):                     # yumshoq vertikal gradient
        t = y / H * 0.75
        d.line([(0, y), (W, y)],
               fill=(int(15 + 39 * t), int(10 + 27 * t), int(28 + 64 * t)))
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([W * .52, -H * .35, W * 1.25, H * .72], fill=(75, 51, 132))
    g.ellipse([-W * .15, H * .45, W * .38, H * 1.35], fill=(54, 37, 92))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(150)), 0.5)

    d = ImageDraw.Draw(img)
    d.text((90, 250), "ZIKR HALQASI", font=_fnt(_FONT_B, 86), fill=LAV)
    f34 = _fnt(_FONT_R, 34)
    d.text((94, 372), f"Kun davomida {son_soz(PER_DAY)} marta qisqa eslatma",
           font=f34, fill=LAV)
    d.text((94, 420), "Vaqti tasodifiy. Xohlagan payt to'xtatasiz.",
           font=f34, fill=LAV_DIM)
    d.line([(94, 540), (320, 540)], fill=LAV, width=2)
    d.text((94, 566), kanal, font=_fnt(_FONT_R, 26), fill=LAV_DIM)

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def cmd_zikr_elon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/zikr_elon [@kanal] — kanalga banner + tugma joylaydi (faqat admin).
    Kanal ko'rsatilmasa CHANNEL_ID ga tushadi.
      /zikr_elon                 -> @safaroov_blog
      /zikr_elon @Sutuur_uz      -> o'sha kanalga
    DIQQAT: kanal postida Mini App tugmasi ishlamaydi, shuning uchun
    havola tugmasi qo'yiladi — u botni ochib, zikrni darrov yoqadi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    kanal = (context.args[0] if context.args else CHANNEL_ID).strip()
    if not kanal.startswith("@") and not kanal.startswith("-"):
        kanal = "@" + kanal

    rasm = make_banner(kanal)
    if rasm is None:
        await update.message.reply_text("Pillow yo'q — banner yasab bo'lmadi.")
        return
    tugma = InlineKeyboardMarkup([[InlineKeyboardButton(
        "ZIKRNI YOQISH ✅",
        url=f"https://t.me/{BOT_USERNAME}?start=zikr")]])
    matn = (f"Zikr halqasi\n\n"
            f"Botimizda kun davomida {son_soz(PER_DAY)} marta qisqa zikr "
            f"eslatmasi keladi. Har birini tasbehdek "
            f"{son_soz(TAKROR)} marta aytasiz.")
    try:
        await context.bot.send_photo(chat_id=kanal, photo=rasm,
                                     caption=matn, reply_markup=tugma)
        await update.message.reply_text(
            f"Banner {kanal} ga joylandi.\n\n"
            f"Endi o'sha postni PIN qiling — shunda tugma yuqoridagi "
            f"panelda doim ko'rinib turadi.")
    except Exception as e:
        await update.message.reply_text(
            f"Joylab bo'lmadi: {e}\n\n"
            f"Bot {kanal} da 'Post messages' huquqli admin ekanini tekshiring.")


# ======================================================================
# RO'YXATGA OLISH
# ======================================================================
def register(app: Application):
    """bot.py dan chaqiriladi: zikr.register(app)"""
    init_db()
    app.add_handler(CommandHandler("zikr", cmd_zikr))
    app.add_handler(CommandHandler("zikr_off", cmd_zikr_off))
    app.add_handler(CommandHandler("zikr_elon", cmd_zikr_elon))
    app.add_handler(CommandHandler("zikr_sinov", cmd_zikr_sinov))
    app.add_handler(CommandHandler("zikr_yakun", cmd_zikr_yakun))
    # eski "zikr_ok" ham, yangi "zikr_ok|kun|vaqt" ham shu handlerga tushadi
    app.add_handler(CallbackQueryHandler(on_aytdim, pattern=r"^zikr_ok"))
    app.add_handler(CallbackQueryHandler(on_taklif, pattern=r"^zikr_taklif$"))
    if TAKLIF_USUL == "inline":
        # Botdagi yagona inline funksiya — zikr taklifi.
        # BotFather: /setinline yoqilmagan bo'lsa tugma javob bermaydi.
        app.add_handler(InlineQueryHandler(on_inline))

    jq = getattr(app, "job_queue", None)
    if jq is None:
        log.warning("job_queue yo'q — zikr eslatmalari ishlamaydi.")
        return
    jq.run_daily(job_kunlik_reja, time=dtime(0, 5, tzinfo=TZ),
                 name="zikr_reja")
    jq.run_repeating(job_tekshir, interval=60, first=20, name="zikr_tekshir")
    log.info("Zikr moduli yoqildi (kuniga %d ta x %d takror, %02d:00-%02d:00, "
             "taklif: %s)", PER_DAY, TAKROR, HOUR_FROM, HOUR_TO,
             TAKLIF_USUL)
