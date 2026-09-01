# -*- coding: utf-8 -*-
"""
miniapp.py — Telegram Mini App uchun kichik HTTP server.

NEGA KERAK: `tg.sendData()` faqat BIR TOMONLAMA — app botga xabar yubora
oladi, lekin botdan ma'lumot O'QIY olmaydi. Ustiga-ustak sendData faqat
ilova REPLY-KLAVIATURA tugmasidan ochilganda ishlaydi; menyu tugmasidan
yoki havoladan ochilganda umuman ishlamaydi. Shu sababli butun bot
ilovaga ko'chirilganda HTTP yo'li kerak bo'ldi.

QANDAY ISHLAYDI: server botning O'SHA jarayonida, o'sha asyncio
halqasida ko'tariladi (python-telegram-bot ham asyncio'da ishlaydi).
Ya'ni yangi servis, yangi to'lov, alohida deploy kerak emas. index.html
ham shu yerdan beriladi — Netlify kerak emas va CORS muammosi yo'q.

AMALLAR QANDAY BAJARILADI: ilovadagi tugma `POST /api/amal` yoki
`POST /api/buyruq` ga so'rov yuboradi; server soxta (lekin haqiqiy
telegram.Update) yasab, MAVJUD buyruq funksiyasini chaqiradi. Ya'ni
mantiq ikki marta yozilmaydi — ilova ham, chatdagi buyruq ham bitta
kodni ishlatadi. Natija (post, rasm, video, tugmalar) chatga tushadi:
tasdiqlash va nashr oqimi allaqachon sinalgan, uni qayta yozish kanalni
buzish xavfini tug'diradi.

XAVFSIZLIK: Telegram ilovani ochganda `initData` beradi — bu bot tokeni
bilan imzolangan qator. Server har so'rovda imzoni qayta hisoblab
tekshiradi, shundan keyingina foydalanuvchi ID'siga ishonadi. Admin
amallari qo'shimcha ravishda ADMIN_ID bilan solishtiriladi, ustiga
buyruq funksiyalarining o'z `admin_only` tekshiruvi ham saqlanadi.

ATAYLAB QO'SHILMAGAN — tasdiqsiz, qaytarib bo'lmaydigan amallar
faqat chatda qoladi:
  /xabar            — minglab odamga tarqatma;
  /reset1, /reset2  — konkurs natijasini o'chiradi;
  /golib2           — g'olibni tanlab, konkursni yopadi;
  /zikr_elon        — kanalga post joylaydi;
  /elon2            — rasmga reply qilishni talab qiladi (ilovada
                      reply yo'q, shuning uchun baribir ishlamasdi).

Railway: Procfile'da `web:` bo'lishi va PORT o'qilishi kerak.
Tashqi manzil: WEBAPP_URL — BotFather'dagi Mini App manzili ham shu.

bot.py:
    post_init ichida:      await miniapp.ishga_tushir(app)
    Application quruvchida: .post_shutdown(miniapp.toxtat)
"""

import asyncio
import hashlib
import hmac
import importlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl

from aiohttp import web
from telegram import Chat, Message, Update, User
from telegram.ext import CallbackContext

import zikr

log = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
PORT = int(os.environ.get("PORT", "8080"))
ILDIZ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ILDIZ, "index.html")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "agent.db"))
# initData qancha vaqt amal qiladi. Telegram uni ilova ochilganda beradi;
# uzoq ochiq turgan ilova eskirgan imzo bilan so'rov yuborishi mumkin.
IMZO_MUDDATI = int(os.environ.get("MINIAPP_IMZO_MUDDATI", "86400"))  # 24 soat

_runner = None
_app = None          # python-telegram-bot Application (bot.py beradi)


# ======================================================================
# IMZO TEKSHIRUVI
# ======================================================================
def initdata_tekshir(init_data):
    """Telegram Mini App imzosini tekshiradi.

    Qaytaradi: user dict (id, first_name, ...) yoki None.

    Tartib (Telegram hujjatidan): hash'siz maydonlar "kalit=qiymat"
    ko'rinishida alifbo bo'yicha tartiblanadi va "\\n" bilan qo'shiladi;
    kalit sifatida HMAC(bot_token, "WebAppData") ishlatiladi."""
    if not init_data or not TOKEN:
        return None
    try:
        juftlar = dict(parse_qsl(init_data, keep_blank_values=True))
    except Exception:
        return None
    imzo = juftlar.pop("hash", None)
    if not imzo:
        return None

    satr = "\n".join(f"{k}={juftlar[k]}" for k in sorted(juftlar))
    maxfiy = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    kutilgan = hmac.new(maxfiy, satr.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(kutilgan, imzo):
        return None

    try:                      # eskirgan imzo qabul qilinmaydi
        if time.time() - int(juftlar.get("auth_date", "0")) > IMZO_MUDDATI:
            return None
    except ValueError:
        return None

    try:
        user = json.loads(juftlar.get("user") or "{}")
    except Exception:
        return None
    return user if user.get("id") else None


def _kim(request):
    """So'rovdan foydalanuvchini aniqlaydi. Imzo yaroqsiz bo'lsa None."""
    xom = (request.headers.get("X-Init-Data")
           or request.query.get("initData") or "")
    return initdata_tekshir(xom)


def _admin_mi(user):
    try:
        return bool(ADMIN_ID) and int(user["id"]) == ADMIN_ID
    except Exception:
        return False


def _xato(matn, kod=401):
    return web.json_response({"xato": matn}, status=kod)


async def _tana(request):
    try:
        return await request.json()
    except Exception:
        return {}


# ======================================================================
# SOXTA UPDATE — mavjud buyruq funksiyalarini qayta ishlatish uchun
# ======================================================================
def _sahna(user):
    """Haqiqiy telegram.Update va CallbackContext yasaydi.

    Nega shunday: barcha buyruqlar `(update, context)` kutadi va
    `update.message.reply_text(...)` bilan javob beradi. Shu ikkitasini
    yasab bersak, ilovadagi tugma AYNAN chatdagi buyruqni ishlatadi —
    mantiq nusxalanmaydi.

    Muhimi: `CallbackContext.from_update` haqiqiy `application.user_data`
    lug'atini beradi. Shuning uchun ko'p bosqichli oqimlar (masalan
    /reels → matn kutish) ilovadan boshlanib, chatda davom etadi."""
    uid = int(user["id"])
    tg_user = User(id=uid, is_bot=False,
                   first_name=user.get("first_name") or "Foydalanuvchi",
                   last_name=user.get("last_name") or None,
                   username=user.get("username") or None,
                   language_code=user.get("language_code") or None)
    chat = Chat(id=uid, type=Chat.PRIVATE,
                first_name=tg_user.first_name, username=tg_user.username)
    xabar = Message(message_id=0, date=datetime.now(timezone.utc),
                    chat=chat, from_user=tg_user, text="")
    xabar.set_bot(_app.bot)
    upd = Update(update_id=0, message=xabar)
    upd.set_bot(_app.bot)
    return upd, CallbackContext.from_update(upd, _app)


def _fonda(korutin, uid, nom):
    """Amalni fonda bajaradi.

    Nega fonda: ba'zi amallar uzoq ketadi (/agent_run manbalarni
    aylanadi, /reels video yig'adi). HTTP so'rovi ularni kutib turса
    brauzer uzib yuboradi. Shuning uchun darhol "boshlandi" deymiz,
    natija esa chatga tushadi."""
    async def qobiq():
        try:
            await korutin
        except Exception as e:
            log.exception("Mini App amali xato berdi: %s", nom)
            try:
                await _app.bot.send_message(
                    uid, f"⚠️ «{nom}» bajarilmadi: {e}")
            except Exception:
                pass
    asyncio.create_task(qobiq())


# Ilovadan ishga tushiriladigan ADMIN buyruqlari: nom → (modul, funksiya).
# Ataylab yo'q: xabar (ommaviy tarqatma), reset1/reset2 (o'chirish) —
# ular faqat chatda qoladi, chunki bitta noto'g'ri bosish qaytmaydi.
ADMIN_BUYRUQLARI = {
    # Yangiliklar agenti
    "agent_run":     ("agent", "cmd_run"),
    "agent_status":  ("agent", "cmd_status"),
    "agent_pause":   ("agent", "cmd_pause"),
    "agent_resume":  ("agent", "cmd_resume"),
    "agent_sources": ("agent", "cmd_sources"),
    "agent_requeue": ("agent", "cmd_requeue"),
    "postlar":       ("agent", "cmd_postlar"),
    # Kanal agentlari
    "farosat":       ("farosat", "cmd_farosat"),
    "sutuur":        ("sutuur", "cmd_sutuur"),
    # Kontent studiyasi
    "iqtibos":       ("iqtibos", "cmd_iqtibos"),
    "iqtibos_rasm":  ("iqtibos", "cmd_iqtibos_rasm"),
    "reels":         ("reels", "cmd_reels"),
    "maqola":        ("maqola", "cmd_maqola"),
    "uslub":         ("subtitr", "cmd_uslub"),
    "shriftlar":     ("subtitr", "cmd_shriftlar"),
    "rich_test":     ("agent", "cmd_rich_test"),
    "rich_oxirgi":   ("agent", "cmd_rich_oxirgi"),
    # Statistika
    "panel":         ("admin", "cmd_panel"),
    "stats":         ("bot", "stats"),
    "tekshir":       ("bot", "tekshir"),
    "kurs_stats":    ("kurs", "cmd_kurs_stats"),
    # Zikr (admin tomoni — ikkalasi ham faqat o'zingizga yuboradi)
    "zikr_sinov":    ("zikr", "cmd_zikr_sinov"),
    "zikr_yakun":    ("zikr", "cmd_zikr_yakun"),
}


def _modul(nom):
    """Modulni QAYTA import qilmasdan topadi.

    Bu ikki sabab bilan muhim:
    1) bot.py miniapp'ni import qiladi — fayl boshida `import bot`
       yozilsa aylanma import bo'lardi;
    2) bot.py `python bot.py` bilan ishga tushadi, ya'ni u `__main__`
       nomi bilan yuklangan. `import bot` yozilsa fayl IKKINCHI marta
       bajarilib, ikkinchi Application yasalardi. Shuning uchun avval
       sys.modules dan qidiramiz."""
    if nom == "bot":
        return sys.modules.get("bot") or sys.modules.get("__main__")
    modul = sys.modules.get(nom)
    if modul is not None:
        return modul
    try:
        return importlib.import_module(nom)
    except Exception:
        log.warning("Mini App: %s moduli import qilinmadi", nom)
        return None


def _buyruq_ol(nom):
    """Buyruq funksiyasini ro'yxatdan topadi."""
    juft = ADMIN_BUYRUQLARI.get(nom)
    if not juft:
        return None
    modul = _modul(juft[0])
    return getattr(modul, juft[1], None) if modul else None


# ======================================================================
# YO'LLAR — sahifa
# ======================================================================
async def _index(request):
    if not os.path.exists(INDEX):
        return web.Response(text="index.html topilmadi", status=404)
    # Ilova tez-tez yangilanadi — brauzer eski nusxani ushlab qolmasin
    return web.FileResponse(INDEX, headers={"Cache-Control": "no-cache"})


async def _sog(request):
    """Railway va monitoring uchun — bot tirikligini bildiradi."""
    return web.json_response({"holat": "ishlayapti"})


# ======================================================================
# YO'LLAR — foydalanuvchi
# ======================================================================
async def _api_men(request):
    """Ilova ochilganda birinchi so'rov: men kimman va nimalarim bor."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    uid = int(user["id"])
    javob = {"id": uid,
             "ism": user.get("first_name") or "",
             "admin": _admin_mi(user)}

    try:
        z = zikr.holat(uid)
        b = z.get("bugun") or {}
        javob["zikr"] = {"yoqilgan": z.get("yoqilgan", False),
                         "streak": z.get("streak", 0),
                         "tugagan": b.get("tugagan", 0),
                         "jami": b.get("jami", 0),
                         "kuniga": z.get("kuniga", 0),
                         "takror": z.get("takror", 0)}
    except Exception:
        log.exception("Mini App: zikr holati o'qilmadi")
        javob["zikr"] = None

    try:
        kurs = _modul("kurs")
        d = kurs._load()
        u = kurs._user(d, uid)
        javob["kurs"] = {"ochiq": bool(u.get("paid")),
                         "foiz": kurs._progress(u),
                         "darslar": kurs._total_lessons()}
    except Exception:
        javob["kurs"] = None

    try:
        botmod = _modul("bot")
        users = botmod.load_json(botmod.USERS_FILE, {})
        ochko = int((users.get(str(uid)) or {}).get("points", 0))
        reyting = botmod.ranking()
        orin = next((i + 1 for i, (k, _) in enumerate(reyting)
                     if k == str(uid)), None)
        javob["konkurs"] = {"faol": bool(botmod.CONTEST_ACTIVE)
                                    and not botmod.contest_over(),
                            "ochko": ochko, "orin": orin,
                            "qoldi": botmod.left_str()}
    except Exception:
        javob["konkurs"] = None
    return web.json_response(javob)


async def _api_zikr(request):
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    try:
        malumot = zikr.holat(int(user["id"]))
    except Exception as e:
        log.exception("Zikr holati o'qilmadi")
        return _xato(f"Ma'lumot o'qilmadi: {e}", 500)
    malumot["ism"] = user.get("first_name") or ""
    return web.json_response(malumot)


async def _api_konkurs(request):
    """Konkurs ekrani: ochkolar, o'rin, TOP-10 va shaxsiy havola."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    uid = int(user["id"])
    try:
        botmod = _modul("bot")
        users = botmod.load_json(botmod.USERS_FILE, {})
        reyting = botmod.ranking()
        top = [{"ism": u.get("name") or "Foydalanuvchi",
                "ochko": int(u.get("points", 0)),
                "men": k == str(uid)}
               for k, u in reyting[:10]]
        return web.json_response({
            "faol": bool(botmod.CONTEST_ACTIVE) and not botmod.contest_over(),
            "nom": botmod.CONTEST_TITLE,
            "sovrin": botmod.CONTEST_PRIZE,
            "kanal": botmod.CONTEST_CHANNEL,
            "qoldi": botmod.left_str(),
            "ochko": int((users.get(str(uid)) or {}).get("points", 0)),
            "orin": next((i + 1 for i, (k, _) in enumerate(reyting)
                          if k == str(uid)), None),
            "har_taklif": botmod.REF_POINTS,
            "havola": f"https://t.me/{botmod.BOT_USERNAME}?start=ref_{uid}",
            "top": top,
        })
    except Exception as e:
        log.exception("Konkurs ma'lumoti o'qilmadi")
        return _xato(f"Ma'lumot o'qilmadi: {e}", 500)


async def _api_amal(request):
    """Foydalanuvchi amali — `tg.sendData` bilan bir xil ma'lumot.

    Ikkalasi ham bot.webapp_amal ga tushadi, ya'ni ilova qaysi yo'l
    bilan ochilganidan qat'i nazar bir xil ishlaydi."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    data = await _tana(request)
    if not isinstance(data, dict) or not data:
        return _xato("Bo'sh so'rov", 400)
    if _app is None:
        return _xato("Bot hali tayyor emas", 503)
    botmod = _modul("bot")
    if botmod is None:
        return _xato("Bot moduli topilmadi", 503)
    upd, ctx = _sahna(user)
    _fonda(botmod.webapp_amal(data, upd, ctx), int(user["id"]),
           str(data.get("action") or "amal"))
    return web.json_response({"ok": True})


# ======================================================================
# YO'LLAR — admin
# ======================================================================
async def _api_buyruq(request):
    """Admin buyrug'ini ishga tushiradi (ro'yxat: ADMIN_BUYRUQLARI)."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    if not _admin_mi(user):
        return _xato("Bu bo'lim faqat admin uchun", 403)
    if _app is None:
        return _xato("Bot hali tayyor emas", 503)
    data = await _tana(request)
    nom = str(data.get("buyruq") or "")
    funksiya = _buyruq_ol(nom)
    if funksiya is None:
        return _xato("Bunday buyruq yo'q yoki moduli o'chirilgan", 404)
    upd, ctx = _sahna(user)
    _fonda(funksiya(upd, ctx), int(user["id"]), nom)
    return web.json_response({"ok": True, "buyruq": nom})


def _agent_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=3000")
    return conn


async def _api_admin_holat(request):
    """Panel raqamlari — /panel dagi bilan bir xil manba."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    if not _admin_mi(user):
        return _xato("Bu bo'lim faqat admin uchun", 403)
    javob = {}
    try:
        javob.update(_modul("admin")._metrics())
    except Exception:
        log.exception("Mini App: panel raqamlari o'qilmadi")
    try:
        agent = _modul("agent")
        conn = _agent_db()
        javob["pauza"] = agent.meta_get(conn, "paused") == "1"
        javob["api_limit"] = agent.MAX_API_CALLS_PER_DAY
        javob["post_limit"] = agent.MAX_POSTS_PER_DAY
        conn.close()
    except Exception:
        javob.setdefault("pauza", False)
    javob["vaqt"] = datetime.now().strftime("%H:%M")
    return web.json_response(javob)


async def _api_admin_postlar(request):
    """Kutayotgan post-nomzodlar ro'yxati (faqat o'qish)."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    if not _admin_mi(user):
        return _xato("Bu bo'lim faqat admin uchun", 403)
    agent = _modul("agent")
    if agent is None:
        return _xato("Agent moduli topilmadi", 503)
    try:
        conn = _agent_db()
        qatorlar = conn.execute(
            "SELECT p.id, p.text, COALESCE(a.rubrika,'ai'), p.created_at "
            "FROM agent_posts p LEFT JOIN agent_articles a "
            "ON a.url = p.article_url WHERE p.status='draft' "
            "ORDER BY p.id DESC LIMIT 20").fetchall()
        jami = conn.execute(
            "SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
        conn.close()
    except Exception as e:
        log.exception("Mini App: qoralamalar o'qilmadi")
        return _xato(f"Ma'lumot o'qilmadi: {e}", 500)
    postlar = []
    for pid, matn, rub, sana in qatorlar:
        satrlar = (matn or "").splitlines()
        postlar.append({
            "id": pid,
            "sarlavha": (satrlar[0].strip() if satrlar else "—")[:80],
            "parcha": " ".join(" ".join(satrlar[1:]).split())[:160],
            "rubrika": agent.RUBRIKA_NOMI.get(rub, rub),
            "emoji": agent.RUBRIKA_EMOJI.get(rub, "📰"),
            "sana": (sana or "")[:16].replace("T", " "),
        })
    return web.json_response({"jami": jami, "postlar": postlar})


async def _api_admin_post(request):
    """Tanlangan qoralamani chatga tugmalari bilan yuboradi.

    Nashr oqimi ATAYLAB chatda qoladi: «Kanalga / Fikr / Ovozli»
    tugmalari allaqachon sinalgan va rasm tanlash bosqichi bor.
    Uni ilovada qaytadan yozish kanalga xato post ketish xavfini
    tug'diradi."""
    user = _kim(request)
    if not user:
        return _xato("Imzo tekshiruvidan o'tmadi")
    if not _admin_mi(user):
        return _xato("Bu bo'lim faqat admin uchun", 403)
    data = await _tana(request)
    try:
        pid = int(data.get("id"))
    except Exception:
        return _xato("Post raqami noto'g'ri", 400)
    agent = _modul("agent")
    if agent is None or _app is None:
        return _xato("Bot hali tayyor emas", 503)
    try:
        conn = _agent_db()
        qator = conn.execute(
            "SELECT text, status FROM agent_posts WHERE id=?", (pid,)).fetchone()
        conn.close()
    except Exception as e:
        return _xato(f"Ma'lumot o'qilmadi: {e}", 500)
    if not qator:
        return _xato("Post topilmadi", 404)
    if qator[1] != "draft":
        return _xato("Bu post allaqachon ko'rilgan", 409)
    await _app.bot.send_message(int(user["id"]), qator[0],
                                reply_markup=agent.draft_keyboard(pid))
    return web.json_response({"ok": True})


# ======================================================================
# ISHGA TUSHIRISH
# ======================================================================
def server_yasa():
    server = web.Application()
    server.router.add_get("/", _index)
    server.router.add_get("/index.html", _index)
    server.router.add_get("/sog", _sog)
    server.router.add_get("/api/men", _api_men)
    server.router.add_get("/api/zikr", _api_zikr)
    server.router.add_get("/api/konkurs", _api_konkurs)
    server.router.add_post("/api/amal", _api_amal)
    server.router.add_post("/api/buyruq", _api_buyruq)
    server.router.add_get("/api/admin/holat", _api_admin_holat)
    server.router.add_get("/api/admin/postlar", _api_admin_postlar)
    server.router.add_post("/api/admin/post", _api_admin_post)
    return server


async def ishga_tushir(app=None):
    """bot.py dagi post_init ichidan chaqiriladi."""
    global _runner, _app
    _app = app
    if _runner is not None:
        return
    _runner = web.AppRunner(server_yasa())
    await _runner.setup()
    await web.TCPSite(_runner, "0.0.0.0", PORT).start()
    log.info("Mini App serveri ishga tushdi: 0.0.0.0:%d", PORT)
    print(f"[MINIAPP] Server tayyor: port {PORT}")


async def toxtat(app=None):
    global _runner, _app
    if _runner is not None:
        await _runner.cleanup()
        _runner = None
    _app = None
