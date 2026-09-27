# -*- coding: utf-8 -*-
"""
OVOZ NAVBATI — bot va Mac'dagi ovoz ishchisi o'rtasidagi navbat
================================================================
NEGA BUNDAY: VoiceStudio sizning Mac'ingizda ishlaydi, bot esa Railway'da.
Eng oddiy yo'l — VoiceStudio'ni tunnel bilan internetga ochish — XAVFLI:
tunnel orqali kelgan so'rov VoiceStudio'ga "shu kompyuterning o'zidan"
bo'lib ko'rinadi va u hech qanday kalit so'ramaydi, jumladan sozlamalar
bo'limi uchun ham (VoiceStudio hujjatining o'zi shunday ogohlantiradi).

Shuning uchun yo'nalish TESKARI: Mac'dagi kichik skript (ovoz_ishchi.py)
botdan "ish bormi?" deb o'zi so'raydi, ovozni VoiceStudio'da MAHALLIY
yasaydi va natijani botga yuklaydi. Mac'da hech qanday port ochilmaydi,
VoiceStudio internetga umuman chiqmaydi.

Bu modul ikki tomondan ishlatiladi:
  * dublyaj.py (alohida oqimda) — qosh() + kut()
  * miniapp.py (asyncio)         — ol(), topshir(), xato()
Shuning uchun hamma narsa bitta qulf (Lock) ostida.

Xotirada saqlanadi: bot qayta ishga tushsa, navbat yo'qoladi — dublyaj
jarayoni ham baribir to'xtaydi, demak yo'qotadigan narsa yo'q.
"""

import threading
import time
import uuid

_qulf = threading.Lock()
_ishlar = {}          # id -> ish lug'ati
_navbat = []          # kutayotgan id'lar (birinchi kelgan — birinchi)
_oxirgi_korinish = 0.0

ESKIRISH_SEK = 3600   # shundan eski ishlar tozalanadi


def _tozala():
    """Bir soatdan eski ishlarni o'chiradi (qulf ostida chaqiriladi)."""
    chegara = time.time() - ESKIRISH_SEK
    for i in [i for i, v in _ishlar.items() if v["vaqt"] < chegara]:
        _ishlar.pop(i, None)
        if i in _navbat:
            _navbat.remove(i)


def qosh(matn, ovoz="default", til="uz", model="omnivoice"):
    """Yangi ovoz ishi. Qaytadi: ish id'si."""
    ish_id = uuid.uuid4().hex[:16]
    with _qulf:
        _tozala()
        _ishlar[ish_id] = {"id": ish_id, "matn": matn, "ovoz": ovoz,
                           "til": til, "model": model, "holat": "kutmoqda",
                           "vaqt": time.time(), "natija": None, "sabab": "",
                           "tayyor": threading.Event()}
        _navbat.append(ish_id)
    return ish_id


def kut(ish_id, timeout=300):
    """Natijani kutadi (dublyaj oqimidan chaqiriladi). Qaytadi: baytlar.

    Vaqt tugasa yoki ishchi xato qaytarsa — RuntimeError. Kutib qolgan
    ish navbatdan olib tashlanadi: ishchi uni keyinroq olib behuda
    vaqt sarflamasin."""
    with _qulf:
        ish = _ishlar.get(ish_id)
    if ish is None:
        raise RuntimeError("Ovoz ishi topilmadi")
    if not ish["tayyor"].wait(timeout):
        with _qulf:
            if ish_id in _navbat:
                _navbat.remove(ish_id)
            _ishlar.pop(ish_id, None)
        raise RuntimeError(
            f"Mac'dagi ovoz ishchisi {int(timeout)} soniyada javob bermadi")
    with _qulf:
        _ishlar.pop(ish_id, None)
    if ish["holat"] != "tayyor":
        raise RuntimeError(f"Ovoz ishchisi xatosi: {ish['sabab'] or 'nomalum'}")
    return ish["natija"]


def yurak_urishi():
    """Ishchi so'rov yubordi — tirik ekanini qayd qilamiz."""
    global _oxirgi_korinish
    with _qulf:
        _oxirgi_korinish = time.time()


def ishchi_tirikmi(sek=90):
    """Ishchi so'nggi `sek` soniyada ko'ringanmi."""
    with _qulf:
        return time.time() - _oxirgi_korinish <= sek


def oxirgi_korinish():
    with _qulf:
        return _oxirgi_korinish


def ol():
    """Ishchi uchun navbatdagi ish (yoki None). Holat -> 'olindi'."""
    yurak_urishi()
    with _qulf:
        _tozala()
        while _navbat:
            ish_id = _navbat.pop(0)
            ish = _ishlar.get(ish_id)
            if ish and ish["holat"] == "kutmoqda":
                ish["holat"] = "olindi"
                return {"id": ish_id, "matn": ish["matn"], "ovoz": ish["ovoz"],
                        "til": ish["til"], "model": ish["model"]}
    return None


def topshir(ish_id, baytlar):
    """Ishchi natija yukladi. Qaytadi: qabul qilindimi."""
    yurak_urishi()
    with _qulf:
        ish = _ishlar.get(ish_id)
        if ish is None or ish["holat"] != "olindi":
            return False
        ish["natija"], ish["holat"] = baytlar, "tayyor"
        ish["tayyor"].set()
        return True


def xato(ish_id, sabab=""):
    """Ishchi bu ishni bajara olmadi."""
    yurak_urishi()
    with _qulf:
        ish = _ishlar.get(ish_id)
        if ish is None or ish["holat"] != "olindi":
            return False
        ish["holat"], ish["sabab"] = "xato", (sabab or "")[:300]
        ish["tayyor"].set()
        return True


def holat():
    """Kuzatuv uchun: navbatdagi va bajarilayotgan ishlar soni."""
    with _qulf:
        return {"kutmoqda": len(_navbat),
                "olingan": sum(1 for v in _ishlar.values() if v["holat"] == "olindi"),
                "oxirgi_korinish": _oxirgi_korinish}
