# -*- coding: utf-8 -*-
"""
reklama.py — bot foydalanuvchilariga rasmli, tugmali reklama (@safarovblog_bot).

/reklama (faqat admin):
  1. Avval reklama namunasi (rasm + izoh + tugma) va necha kishiga
     ketishi ko'rsatiladi — hech narsa yuborilmaydi.
  2. «Yuborish» bosilgach, botni bloklamagan barcha foydalanuvchilarga
     (users.json, oxirgi /tekshir bo'yicha) BIR MARTA yuboriladi:
     fon vazifasida, soniyasiga 20 tagacha, RetryAfter kutiladi.
  3. Holat reklama.db da: bot o'rtada qayta ishga tushsa, qolgan
     joyidan davom etadi; tugagan reklama qayta yuborilmaydi.
  4. Oxirida adminga hisobot: yetib bordi / bloklagan / xato.

Yangi reklama uchun JORIY ni yangi nomga almashtirib, REKLAMALAR ga
rasm, matn va tugma qo'shiladi — eski reklamaning holati alohida qoladi.

bot.py:  import reklama  →  reklama.register(app)
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import (
    BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut,
)
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

log = logging.getLogger("reklama")

TZ = ZoneInfo("Asia/Tashkent")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
DATA_DIR = os.environ.get("DATA_DIR", ".")
USERS_FILE = os.path.join(DATA_DIR, "users.json")     # bot.py dagi ro'yxat
DB_PATH = os.path.join(DATA_DIR, "reklama.db")
RASMLAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rasmlar")

# Soniyasiga nechta xabar. Telegram chegarasi ~30 — zaxira bilan 20.
TEZLIK = 20

REKLAMALAR = {
    # Sutuur kanali — "Yashirin satr": izohdagi satr spoyler ostida,
    # foydalanuvchi ustiga bosib ochadi. Satr kanalning o'z postidan.
    "sutuur-1": {
        "rasm": "sutuur_reklama.jpg",
        "matn": (
            "Sizga bitta satr yashirib qo'ydik.\n"
            "Ochish uchun ustiga bosing:\n\n"
            "<tg-spoiler>O'zingni buncha qiynama, oddiyroq bo'laver!"
            "</tg-spoiler>\n\n"
            "Shunday satrlar — «Sutuur | Satrlar» kanalida."
        ),
        "tugma": "✨ Yana satrlar",
        "havola": "https://t.me/+S0znGZNhut84MDFi",
    },
}
JORIY = "sutuur-1"

# Fon vazifasi (asyncio.Task) — bir vaqtda faqat bittasi
_vazifa = None


# ======================================================================
# HOLAT (reklama.db)
# ======================================================================
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    return conn


def _ol(conn, k, default=None):
    row = conn.execute("SELECT v FROM meta WHERE k=?", (f"{JORIY}:{k}",)).fetchone()
    return row[0] if row else default


def _qoy(conn, k, v):
    conn.execute("INSERT OR REPLACE INTO meta (k, v) VALUES (?, ?)",
                 (f"{JORIY}:{k}", str(v)))


def _hisob(conn):
    return {k: int(_ol(conn, k, "0") or 0)
            for k in ("yuborildi", "bloklagan", "xato")}


def _raqam(n):
    return f"{n:,}".replace(",", " ")


def _hisoboti(hisob):
    return (f"Yetib bordi: {_raqam(hisob['yuborildi'])}\n"
            f"Botni bloklagan: {_raqam(hisob['bloklagan'])}\n"
            f"Yetmadi (xato): {_raqam(hisob['xato'])}")


def _hozir():
    return datetime.now(TZ).isoformat(timespec="minutes")


# ======================================================================
# RO'YXAT VA YUBORISH
# ======================================================================
def royxat(oxirgi=0):
    """users.json dagi, oxirgi /tekshir bo'yicha botni bloklamagan
    foydalanuvchilar (admindan tashqari), uid tartibida. Fayl o'qilmasa
    xato ko'tariladi: bo'sh ro'yxat "hammaga yuborildi" bo'lib qolmasin."""
    with open(USERS_FILE, encoding="utf-8") as f:
        users = json.load(f)
    uidlar = []
    for kalit, u in users.items():
        try:
            uid = int(kalit)
        except (TypeError, ValueError):
            continue
        if uid <= oxirgi or uid == ADMIN_ID:
            continue
        if isinstance(u, dict) and u.get("blocked"):
            continue
        uidlar.append(uid)
    return sorted(uidlar)


def _tugma():
    r = REKLAMALAR[JORIY]
    return InlineKeyboardMarkup([[InlineKeyboardButton(r["tugma"], url=r["havola"])]])


def _rasm():
    try:
        with open(os.path.join(RASMLAR, REKLAMALAR[JORIY]["rasm"]), "rb") as f:
            return f.read()
    except OSError:
        log.warning("Reklama rasmi topilmadi — matnning o'zi ketadi")
        return None


def _soniya(qiymat):
    """RetryAfter.retry_after — PTB versiyasiga qarab son yoki timedelta."""
    if hasattr(qiymat, "total_seconds"):
        return qiymat.total_seconds()
    return float(qiymat)


async def _yubor(bot, chat_id, rasm):
    matn = REKLAMALAR[JORIY]["matn"]
    if rasm is None:
        return await bot.send_message(chat_id=chat_id, text=matn, parse_mode="HTML",
                                      reply_markup=_tugma())
    return await bot.send_photo(chat_id=chat_id, photo=rasm, caption=matn,
                                parse_mode="HTML", reply_markup=_tugma())


async def _bittaga(bot, uid, rasm):
    """Qaytadi: (natija, rasm). natija — "yuborildi" / "bloklagan" / "xato".
    rasm birinchi yuklashdan keyin file_id bo'ladi — qayta yuklanmaydi."""
    for _ in range(3):
        try:
            xabar = await _yubor(bot, uid, rasm)
            if rasm is not None and getattr(xabar, "photo", None):
                rasm = xabar.photo[-1].file_id
            return "yuborildi", rasm
        except RetryAfter as e:
            # Telegram "sekinroq" dedi — aytgan vaqticha kutib, qaytamiz
            await asyncio.sleep(_soniya(e.retry_after) + 1)
        except Forbidden:
            return "bloklagan", rasm
        except TimedOut as e:
            # Javob kelmadi, lekin xabar yetib borgan bo'lishi mumkin —
            # qayta yuborsak, ikki marta tushib qolardi
            log.warning("Reklama (%s): javob kelmadi: %s", uid, e)
            return "xato", rasm
        except BadRequest as e:
            log.warning("Reklama (%s): %s", uid, e)
            return "xato", rasm
        except NetworkError as e:
            log.warning("Reklama (%s): tarmoq: %s", uid, e)
            await asyncio.sleep(3)
        except Exception:
            log.exception("Reklama (%s): kutilmagan xato", uid)
            return "xato", rasm
    return "xato", rasm


async def _adminga(bot, matn):
    if not ADMIN_ID:
        return
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=matn)
    except Exception:
        log.warning("Reklama: adminga xabar yuborilmadi", exc_info=True)


async def _tarqat(bot):
    """Fon vazifasi. Har yuborishdan keyin oxirgi uid yoziladi — bot
    qayta ishga tushsa, qolgan joyidan davom etadi."""
    conn = db()
    try:
        oxirgi = int(_ol(conn, "oxirgi_uid", "0") or 0)
        uidlar = royxat(oxirgi)
        hisob = _hisob(conn)
        rasm = _rasm()
        oraliq = 1 / TEZLIK
        loop = asyncio.get_running_loop()
        log.info("Reklama %s: %d kishiga yuboriladi", JORIY, len(uidlar))
        for uid in uidlar:
            boshi = loop.time()
            natija, rasm = await _bittaga(bot, uid, rasm)
            hisob[natija] += 1
            _qoy(conn, natija, hisob[natija])
            _qoy(conn, "oxirgi_uid", uid)
            conn.commit()
            kut = oraliq - (loop.time() - boshi)
            if kut > 0:
                await asyncio.sleep(kut)
        _qoy(conn, "holat", "tugadi")
        _qoy(conn, "tugadi", _hozir())
        conn.commit()
    except Exception:
        log.exception("Reklama %s to'xtab qoldi", JORIY)
        await _adminga(bot, "Reklama yuborilayotganda to'xtab qoldi. "
                            "/reklama — qolgan joyidan davom ettiradi.")
        return
    finally:
        conn.close()
    log.info("Reklama %s tugadi: %s", JORIY, hisob)
    await _adminga(bot, "Reklama yuborildi.\n\n" + _hisoboti(hisob))


def _boshlat(app):
    """Fon vazifasini ishga tushiradi; ishlayotgan bo'lsa — False."""
    global _vazifa
    if _vazifa is not None and not _vazifa.done():
        return False
    _vazifa = app.create_task(_tarqat(app.bot), name="reklama")
    return True


async def _davom(context: ContextTypes.DEFAULT_TYPE):
    _boshlat(context.application)


# ======================================================================
# BUYRUQ VA TASDIQ
# ======================================================================
async def cmd_reklama(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reklama — namuna + tasdiq; boshlangan bo'lsa holatini aytadi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    xabar = update.effective_message
    conn = db()
    try:
        holat = _ol(conn, "holat")
        hisob = _hisob(conn)
        tugadi = _ol(conn, "tugadi", "")
    finally:
        conn.close()

    if holat == "tugadi":
        await xabar.reply_text(f"Bu reklama {tugadi} da yuborilgan — qayta "
                               f"yuborilmaydi.\n\n" + _hisoboti(hisob))
        return
    if holat == "jarayonda":
        boshi = ("Yuborish to'xtab qolgan edi — qolgan joyidan davom etyapti."
                 if _boshlat(context.application) else "Reklama yuborilmoqda.")
        await xabar.reply_text(f"{boshi}\n\n" + _hisoboti(hisob))
        return

    try:
        nechta = len(royxat())
    except (OSError, ValueError):
        log.exception("Reklama: users.json o'qilmadi")
        await xabar.reply_text("Foydalanuvchilar ro'yxatini o'qib bo'lmadi. "
                               "Birozdan keyin qayta urinib ko'ring.")
        return
    if nechta == 0:
        await xabar.reply_text("Reklama yuboriladigan odam yo'q.")
        return

    await _yubor(context.bot, ADMIN_ID, _rasm())
    daqiqa = max(1, -(-nechta // (TEZLIK * 60)))
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Yuborish", callback_data="rekl|ha"),
        InlineKeyboardButton("Bekor", callback_data="rekl|yoq")]])
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(f"Yuqoridagi reklama {_raqam(nechta)} kishiga bir marta "
              f"yuboriladi (taxminan {daqiqa} daqiqa).\n\n"
              "Ro'yxat — botdagi hamma, botni bloklaganlardan tashqari "
              "(oxirgi /tekshir natijasi). Yashirin satrni ochib, tugmani "
              "bosib tekshirib ko'ring.\n\nYuborilsinmi?"),
        reply_markup=kb)


async def on_tasdiq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Bu tugma faqat admin uchun.", show_alert=True)
        return
    if (query.data or "").split("|")[-1] != "ha":
        await query.answer("Bekor qilindi")
        await query.edit_message_text("Reklama yuborilmadi.")
        return

    conn = db()
    try:
        yangi = _ol(conn, "holat") is None
        if yangi:
            _qoy(conn, "holat", "jarayonda")
            _qoy(conn, "boshlandi", _hozir())
            conn.commit()
    finally:
        conn.close()
    await query.answer()
    if not yangi:
        await query.edit_message_text("Reklama allaqachon boshlangan. Holati: /reklama")
        return
    _boshlat(context.application)
    await query.edit_message_text("Reklama yuborish boshlandi. Tugagach hisobot keladi.")


def register(app):
    """bot.py dan chaqiriladi: reklama.register(app)"""
    app.add_handler(CommandHandler("reklama", cmd_reklama))
    app.add_handler(CallbackQueryHandler(on_tasdiq, pattern=r"^rekl\|"))
    conn = db()
    try:
        holat = _ol(conn, "holat")
    finally:
        conn.close()
    jq = getattr(app, "job_queue", None)
    if holat == "jarayonda" and jq is not None:
        # Yuborish o'rtasida qayta ishga tushgan — davom etadi
        jq.run_once(_davom, when=30, name="reklama")
