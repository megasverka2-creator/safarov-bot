# -*- coding: utf-8 -*-
"""
miniapp.py — Telegram Mini App uchun kichik HTTP server.

NEGA KERAK: `tg.sendData()` faqat BIR TOMONLAMA — app botga xabar yubora
oladi, lekin botdan ma'lumot O'QIY olmaydi. Shuning uchun ilovada zikr
progressi, kurs holati yoki statistika ko'rsatib bo'lmasdi.

QANDAY ISHLAYDI: server botning O'SHA jarayonida, o'sha asyncio
halqasida ko'tariladi (python-telegram-bot ham asyncio'da ishlaydi).
Ya'ni yangi servis, yangi to'lov, alohida deploy kerak emas. index.html
ham shu yerdan beriladi — Netlify kerak emas va CORS muammosi yo'q.

XAVFSIZLIK: Telegram ilovani ochganda `initData` beradi — bu bot tokeni
bilan imzolangan qator. Server har so'rovda imzoni qayta hisoblab
tekshiradi, shundan keyingina foydalanuvchi ID'siga ishonadi. Ya'ni
birov boshqa odamning ID'sini yozib ma'lumotini o'qiy olmaydi.

Railway: Procfile'da `web:` bo'lishi va PORT o'qilishi kerak.
Tashqi manzil: WEBAPP_URL — BotFather'dagi Mini App manzili ham shu.

bot.py:
    post_init ichida:      await miniapp.ishga_tushir(app)
    Application quruvchida: .post_shutdown(miniapp.toxtat)
"""

import hashlib
import hmac
import json
import logging
import os
import time
from urllib.parse import parse_qsl

from aiohttp import web

import zikr

log = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
PORT = int(os.environ.get("PORT", "8080"))
ILDIZ = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(ILDIZ, "index.html")
# initData qancha vaqt amal qiladi. Telegram uni ilova ochilganda beradi;
# uzoq ochiq turgan ilova eskirgan imzo bilan so'rov yuborishi mumkin.
IMZO_MUDDATI = int(os.environ.get("MINIAPP_IMZO_MUDDATI", "86400"))  # 24 soat

_runner = None


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


def _xato(matn, kod=401):
    return web.json_response({"xato": matn}, status=kod)


# ======================================================================
# YO'LLAR
# ======================================================================
async def _index(request):
    if not os.path.exists(INDEX):
        return web.Response(text="index.html topilmadi", status=404)
    # Ilova tez-tez yangilanadi — brauzer eski nusxani ushlab qolmasin
    return web.FileResponse(INDEX, headers={"Cache-Control": "no-cache"})


async def _sog(request):
    """Railway va monitoring uchun — bot tirikligini bildiradi."""
    return web.json_response({"holat": "ishlayapti"})


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


# ======================================================================
# ISHGA TUSHIRISH
# ======================================================================
def server_yasa():
    server = web.Application()
    server.router.add_get("/", _index)
    server.router.add_get("/index.html", _index)
    server.router.add_get("/sog", _sog)
    server.router.add_get("/api/zikr", _api_zikr)
    return server


async def ishga_tushir(app=None):
    """bot.py dagi post_init ichidan chaqiriladi."""
    global _runner
    if _runner is not None:
        return
    _runner = web.AppRunner(server_yasa())
    await _runner.setup()
    await web.TCPSite(_runner, "0.0.0.0", PORT).start()
    log.info("Mini App serveri ishga tushdi: 0.0.0.0:%d", PORT)
    print(f"[MINIAPP] Server tayyor: port {PORT}")


async def toxtat(app=None):
    global _runner
    if _runner is not None:
        await _runner.cleanup()
        _runner = None
