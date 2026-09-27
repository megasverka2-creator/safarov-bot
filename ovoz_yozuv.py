# -*- coding: utf-8 -*-
"""
OVOZ YOZUVI — o'z ovozingizda ovoz modelini o'qitish uchun yozuvlar yig'ish
=========================================================================
Klon (15-30 s namuna) ovozga O'XSHAYDI; 1 ga 1 bo'lishi uchun modelni
o'z yozuvlaringiz bilan qo'shimcha o'qitish (fine-tune) kerak. Buning
uchun eng ko'p vaqt oladigan ish — soatlab TOZA yozuv va har birining
ANIQ matni. Shu modul aynan shuni botning ichida qiladi:

  /ovoz_yozuv        — bot jumla yuboradi, siz voice xabar bilan o'qiysiz,
                       bot tekshirib saqlaydi va keyingisini beradi
  /ovoz_yozuv_matn   — o'z matningizni (post, maqola) jumlalarga bo'lib
                       navbatning boshiga qo'shadi
  /ovoz_dataset      — hammasini ZIP qilib yuboradi (metadata.csv +
                       asl audio). Bu ham ZAXIRA: vaqti-vaqti bilan oling.

JUMLALAR: avval qo'lda tanlangan jumlalar (o' g' sh ch ng q x h, tutuq
belgisi, savol/xitob gaplar, raqamlar so'z bilan); ular tugagach navbat AI
yozgan xilma-xil jumlalar bilan to'ldiriladi. Matnda raqam bo'lmaydi —
"2025" ni har kim har xil o'qiydi, yozuv va matn mos kelmay qoladi.

TEKSHIRUV (har yozuvda, ffmpeg bilan): davomiylik, ovoz juda past /
juda baland (buzilish), jumlaga nisbatan juda qisqa yoki juda uzun.
Shubhali yozuv saqlanMAYDI — qayta o'qish yoki "Baribir saqlash".

SAQLASH: DATA_DIR/ovoz_yozuv/ — klip/ (Telegram'dan kelgan asl fayl,
qayta siqilmaydi) va holat.json. 3 soat voice ≈ 50-100 MB.
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import subprocess
import tempfile
import threading
import time
import wave
import zipfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import talaffuz

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
DATA_DIR = os.environ.get("DATA_DIR", ".")
PAPKA = os.path.join(DATA_DIR, "ovoz_yozuv")
KLIP_PAPKA = os.path.join(PAPKA, "klip")
HOLAT_FAYL = os.path.join(PAPKA, "holat.json")
MODEL = os.environ.get("AI_MODEL_SMART", "gpt-5.6-terra")

MAQSAD_DAQIQA = int(os.environ.get("OVOZ_YOZUV_MAQSAD", "180"))   # 3 soat
SESSIYA_SEK = 2 * 3600          # shuncha jimlikdan keyin rejim o'zi o'chadi
QISM_MAKS = 45 * 1024 * 1024    # Telegram 50 MB — ZIP qismlarga bo'linadi
JUMLA_MIN, JUMLA_MAKS = 25, 170  # belgi: ≈ 2-12 soniya

# ----------------------------------------------------------------------
# Qo'lda tanlangan boshlang'ich jumlalar. Raqamlar — so'z bilan.
# ----------------------------------------------------------------------
BOSHLANGICH = [
    "Bugun sizlar bilan sun'iy intellekt olamidagi eng qiziq yangiliklarni ko'rib chiqamiz.",
    "Marketing — bu mahsulot sotish emas, balki odamlarning muammosini tushunish san'ati.",
    "Ertalab soat yettida turib, bir piyola choy ichib, ishga otlandim.",
    "Qishloqdagi bog'imizda o'rik, olma va shaftoli daraxtlari bor edi.",
    "Nega ko'pchilik yangi ish boshlashdan qo'rqadi, hech o'ylab ko'rganmisiz?",
    "Bu g'oya juda oddiy ko'rinadi, lekin natijasi hammani hayratda qoldirdi!",
    "Toshkentda kuz faslida havo salqin, ko'chalar esa sarg'ish barglarga to'ladi.",
    "Mijoz sizdan emas, sizning qadriyatingizdan xarid qiladi.",
    "Yangi model avvalgisidan ikki barobar tezroq ishlaydi va kamroq xato qiladi.",
    "Shu hafta kanalimizga ming ikki yuz nafar yangi obunachi qo'shildi.",
    "Qanday qilib o'n besh daqiqada sifatli post yozish mumkin?",
    "Jamoamizda to'rt nafar dasturchi, ikki nafar dizayner va bitta menejer bor.",
    "Ishonchni qozonish uchun yillar kerak, yo'qotish uchun esa bir soniya kifoya.",
    "Chiroyli reklama emas, aniq taklif savdoni oshiradi.",
    "Men bu kitobni o'qib chiqqach, vaqtni rejalashtirishga boshqacha qaray boshladim.",
    "Oshxonadan palovning mazali hidi taralib turardi.",
    "Xo'sh, endi eng muhim savolga o'tamiz: bundan qanday foyda olamiz?",
    "Qizim maktabda ingliz tili va matematikadan a'lo baholar oladi.",
    "Kompaniya o'tgan yili daromadini qirq foizga oshirdi.",
    "OpenAI yangi versiyani taqdim etdi va u matn bilan birga rasmni ham tushunadi.",
    "Google qidiruv tizimida sun'iy intellekt javoblari tobora ko'payib bormoqda.",
    "Har kuni ozgina o'rganish bir kunda ko'p o'rganishdan afzalroq.",
    "Samarqandning qadimiy ko'chalarida sayr qilish menga katta zavq bag'ishlaydi.",
    "Siz ham shunday xatoga yo'l qo'yganmisiz? Izohlarda yozib qoldiring.",
    "Brend — bu logotip emas, odamlarning siz haqingizdagi taassuroti.",
    "Yomg'ir tinmay yog'ar, derazadan esa shahar chiroqlari xira ko'rinardi.",
    "Bu dastur yordamida hisobotni avtomatik tarzda tayyorlash mumkin.",
    "Chegirma faqat bugun kechgacha amal qiladi, shoshiling!",
    "Muvaffaqiyatning siri boshlagan ishni oxiriga yetkazishda.",
    "Uch yil oldin bu texnologiya haqida hech kim gapirmas edi.",
    "Telefoningizdagi bildirishnomalarni o'chirib qo'ying va diqqatingizni jamlang.",
    "Qo'shnimiz har bahorda hovlisiga gul ekadi.",
    "Nima deysiz, sun'iy intellekt dizaynerlarning o'rnini egallaydimi?",
    "Birinchi taassurot ko'pincha keyingi hamma narsani belgilab beradi.",
    "Kecha ikki soat davomida yangi loyiha ustida ishladik.",
    "Mahsulotingizni kimga sotayotganingizni bilmasangiz, reklama pulingiz behuda ketadi.",
    "Ajoyib! Aynan shu natijani kutgan edik.",
    "Farg'ona vodiysining shirin qovunlari butun mamlakatda mashhur.",
    "Yangi telefonning kamerasi tunda ham tiniq surat oladi.",
    "Sizga eng ko'p yoqqan kitob qaysi va nega?",
    "Ma'lumotlar xavfsizligi bugungi kunda har bir kompaniya uchun muhim masala.",
    "Tajriba shuni ko'rsatdiki, qisqa videolar uzunlariga qaraganda ko'proq ko'riladi.",
    "Chorshanba kuni soat uchda onlayn uchrashuv bo'lib o'tadi.",
    "O'g'lim velosiped haydashni bir haftada o'rganib oldi.",
    "Raqobatchilaringizni kuzating, lekin ulardan nusxa ko'chirmang.",
    "Bu ilova oyiga besh dollar turadi, birinchi hafta esa tekin.",
    "Hayotda eng qimmat narsa vaqt, uni to'g'ri sarflang.",
    "Nvidia aksiyalari bir kunda keskin ko'tarildi.",
    "Yozgi ta'tilda tog'larga chiqib, toza havodan bahramand bo'ldik.",
    "Auditoriyangizni qanday qilib ikki barobar oshirish mumkinligini hozir aytib beraman.",
    "Shoshilmang, avval rejani yaxshilab o'ylab chiqing.",
    "Mijozlarning fikri eng qimmatli maslahatdir.",
    "Kutubxonada jimjitlik hukm surar, faqat sahifalar shitirlashi eshitilardi.",
    "Siz ertaga qayerda bo'lasiz, uchrashsak bo'ladimi?",
    "Kontent reja tuzing: dushanba foydali maslahat, chorshanba keys, juma savol-javob.",
    "Bu voqea menga muhim saboq bo'ldi.",
    "Xatoga yo'l qo'yishdan qo'rqmang, faqat undan xulosa chiqaring.",
    "Buxoro, Xiva va Samarqand sayyohlar eng ko'p tashrif buyuradigan shaharlar.",
    "Sun'iy intellekt matn yozadi, rasm chizadi va hatto musiqa bastalaydi.",
    "Ovozli yordamchilar endi o'zbek tilini ham tushuna boshladi.",
    "Nahotki shuncha oddiy narsani oldin hech kim sezmagan bo'lsa?",
    "To'qqiz yuz ellik ming so'mlik buyurtma bir kunda yetkazib berildi.",
    "Sotuv voronkasining har bir bosqichini alohida tahlil qiling.",
    "Ukam futbolni juda yaxshi ko'radi va har kuni mashg'ulotga boradi.",
    "Qahva ichasizmi yoki choymi?",
    "Hamma narsa kichik qadamdan boshlanadi.",
    "Eng yaxshi reklama mamnun mijozning tavsiyasidir.",
    "Ikki ming yigirma beshinchi yilda bu bozor yana o'sishda davom etdi.",
    "Diqqat! Taqdimot bir necha daqiqadan so'ng boshlanadi.",
    "Men ham avvaliga ishonmagandim, lekin sinab ko'rgach fikrim o'zgardi.",
    "Grafik oylik o'sishni aniq ko'rsatib turibdi.",
    "Anthropic kompaniyasi xavfsiz sun'iy intellekt ustida ishlaydi.",
    "Qorong'i tushganda shahar chiroqlari birin-ketin yona boshladi.",
    "Siz bilan suhbatlashganimdan juda xursandman, rahmat!",
]

MAVZULAR = [
    "sun'iy intellekt yangiliklari", "marketing va sotuv", "SMM va kontent",
    "biznes boshlash", "texnologiya va gadjetlar", "kundalik hayot va oila",
    "sayohat va O'zbekiston shaharlari", "ovqat va dasturxon",
    "o'qish, kitob va o'z ustida ishlash", "sport va sog'lom turmush",
    "ish va jamoa", "tabiat va ob-havo", "pul va moliyaviy savodxonlik",
    "podkast suhbati: savol-javob", "reklama va brend",
]

JUMLA_PROMPT = """Sen ovoz modelini o'qitish uchun O'ZBEKCHA (lotin) jumlalar \
yozasan. Bitta odam ularni ovoz chiqarib o'qiydi.

QOIDALAR:
1. {soni} ta jumla, mavzu: {mavzu}. Har biri 6-20 so'z, bir nafasda o'qiladi.
2. Tabiiy og'zaki-adabiy o'zbek tili: jonli, ravon. Kitobiy iboralar taqiq \
("ushbu", "mazkur", "hisoblanadi", "amalga oshirmoqda").
3. Xilma-xil bo'lsin: har beshinchi jumla — savol, har o'ninchisi — \
xitob (!). Qisqa va uzun jumlalar aralash.
4. O' G' SH CH NG Q X H harflari va tutuq belgisi (ma'no, sun'iy) ko'p \
uchrasin.
5. RAQAM YOZMA — faqat so'z bilan: "ikki ming yigirma besh", "qirq foiz".
6. Chet nom (OpenAI, Google, Telegram) — ko'pi bilan har beshinchi jumlada.
7. Din, siyosat, kasallik, fojia mavzulari — TAQIQ. Aniq odamlar haqida \
da'vo — TAQIQ.
8. Jumlalar bir-birini takrorlamasin.

JAVOB — faqat JSON: {{"jumlalar": ["...", "..."]}}"""

_qulf = threading.RLock()
_toldirish_qulf = threading.Lock()
_sessiya = {"faol": False, "oxirgi": 0.0, "kutilayotgan": None}


# ======================================================================
# HOLAT (holat.json)
# ======================================================================
def _yangi_holat():
    return {"navbat": list(BOSHLANGICH), "ishlatilgan": [], "yozuvlar": [],
            "keyingi_id": 1}


def _oqi():
    with _qulf:
        try:
            with open(HOLAT_FAYL, "r", encoding="utf-8") as f:
                h = json.load(f)
            for k, v in _yangi_holat().items():
                h.setdefault(k, v)
            return h
        except FileNotFoundError:
            return _yangi_holat()


def _yoz(h):
    with _qulf:
        os.makedirs(PAPKA, exist_ok=True)
        vaqtincha = HOLAT_FAYL + ".tmp"
        with open(vaqtincha, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False)
        os.replace(vaqtincha, HOLAT_FAYL)


def _iz(matn):
    """Takrorni aniqlash uchun: harf-raqamdan boshqasi olib tashlanadi."""
    toza = re.sub(r"[\W_]+", "", talaffuz._apostrof(matn).lower())
    return hashlib.sha1(toza.encode("utf-8")).hexdigest()[:16]


def _tozala(jumla):
    """Jumlani yozuvga tayyorlaydi: apostrof, raqam so'zga. Yaroqsiz — None."""
    j = " ".join((jumla or "").split()).strip(" \"'«»")
    j = talaffuz._apostrof(j)
    if re.search(r"\d", j):
        j = talaffuz._raqamlar(j)
    if not (JUMLA_MIN <= len(j) <= JUMLA_MAKS):
        return None
    j = j[0].upper() + j[1:]
    if re.search(r"[А-Яа-яЁё]", j):      # kirill aralashib qolgan
        return None
    return j


def _navbatga(jumlalar, boshiga=False):
    """Yangi jumlalarni navbatga qo'shadi (takrorsiz). Qaytadi: qo'shilgan soni."""
    with _qulf:
        h = _oqi()
        bor = set(h["ishlatilgan"]) | {_iz(j) for j in h["navbat"]} \
            | {_iz(y["matn"]) for y in h["yozuvlar"]}
        yangi = []
        for j in jumlalar:
            j = _tozala(j)
            if j and _iz(j) not in bor:
                bor.add(_iz(j))
                yangi.append(j)
        h["navbat"] = yangi + h["navbat"] if boshiga else h["navbat"] + yangi
        _yoz(h)
        return len(yangi)


def statistika():
    h = _oqi()
    sek = sum(y["sek"] for y in h["yozuvlar"])
    return {"soni": len(h["yozuvlar"]), "daqiqa": sek / 60,
            "navbat": len(h["navbat"])}


# ======================================================================
# JUMLA YARATISH (AI)
# ======================================================================
_ai = None


def _ai_klient():
    global _ai
    if _ai is None:
        from openai import OpenAI
        _ai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _ai


def _ai_jumlalar(soni=30):
    mavzu = random.choice(MAVZULAR)
    r = _ai_klient().chat.completions.create(
        model=MODEL, response_format={"type": "json_object"},
        max_completion_tokens=6000,
        messages=[{"role": "user",
                   "content": JUMLA_PROMPT.format(soni=soni, mavzu=mavzu)}])
    try:
        data = json.loads(r.choices[0].message.content or "{}")
    except Exception:
        return []
    return [j for j in (data.get("jumlalar") or []) if isinstance(j, str)]


def navbatni_toldir(chegara=15):
    """Navbat kam qolsa AI'dan yangi jumlalar oladi. Bir vaqtda bittasi."""
    if statistika()["navbat"] >= chegara:
        return 0
    if not _toldirish_qulf.acquire(blocking=False):
        return 0
    try:
        qoshildi = 0
        for _ in range(3):
            qoshildi += _navbatga(_ai_jumlalar())
            if statistika()["navbat"] >= chegara:
                break
        return qoshildi
    except Exception as e:
        log.warning("Ovoz yozuvi: jumla yaratilmadi: %s", e)
        return 0
    finally:
        _toldirish_qulf.release()


def matndan_jumlalar(matn):
    """O'z matningizni (post, maqola) jumlalarga bo'ladi."""
    matn = re.sub(r"[#*_`>\[\]()]|https?://\S+|@\w+", " ", matn)
    qismlar = re.split(r"(?<=[.!?…])\s+|\n+", matn)
    return [q for q in (" ".join(q.split()) for q in qismlar) if q]


# ======================================================================
# AUDIO TEKSHIRUV
# ======================================================================
def tekshir(kirish_yol, matn):
    """Qaytadi: (soniya, [ogohlantirishlar]). Buzuq fayl — RuntimeError."""
    wav = kirish_yol + ".tekshir.wav"
    try:
        r = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-i", kirish_yol,
             "-af", "volumedetect", "-ac", "1", "-ar", "24000",
             "-c:a", "pcm_s16le", "-y", wav],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("audio o'qilmadi")
        with wave.open(wav, "rb") as w:
            sek = w.getnframes() / float(w.getframerate() or 24000)
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass

    def _db(nom):
        m = re.search(nom + r":\s*(-?[\d.]+|-inf) dB", r.stderr)
        if not m:
            return None
        return -120.0 if m.group(1) == "-inf" else float(m.group(1))

    ortacha, eng = _db("mean_volume"), _db("max_volume")
    ogoh = []
    if sek < 1.0:
        ogoh.append("juda qisqa (1 soniyadan kam)")
    if sek > 30:
        ogoh.append("30 soniyadan uzun — bitta jumlani o'qing")
    if eng is not None and eng >= -0.2:
        ogoh.append("ovoz juda baland — buzilgan bo'lishi mumkin; "
                    "telefonni biroz uzoqroq tuting")
    if ortacha is not None and ortacha < -40:
        ogoh.append("ovoz juda past — telefonni yaqinroq tuting")
    belgi = len(talaffuz.ozgartir(matn))
    if sek >= 1.0 and belgi / sek > 25:
        ogoh.append("jumlaga nisbatan juda qisqa — to'liq o'qilmaganga o'xshaydi")
    if sek > belgi / 5 + 3:
        ogoh.append("jumlaga nisbatan juda uzun — boshida/oxirida uzoq "
                    "jimlik yoki ortiqcha gap bor")
    return sek, ogoh


def _saqla(manba_yol, ext, matn, sek):
    """Yozuvni doimiy joyga ko'chiradi va holatga yozadi. Qaytadi: yozuv."""
    with _qulf:
        h = _oqi()
        i = h["keyingi_id"]
        fayl = f"{i:05d}.{ext}"
        os.makedirs(KLIP_PAPKA, exist_ok=True)
        os.replace(manba_yol, os.path.join(KLIP_PAPKA, fayl))
        yozuv = {"id": i, "fayl": fayl, "matn": matn, "sek": round(sek, 2),
                 "vaqt": int(time.time())}
        h["yozuvlar"].append(yozuv)
        h["keyingi_id"] = i + 1
        if h["navbat"] and h["navbat"][0] == matn:
            h["navbat"].pop(0)
        _yoz(h)
        return yozuv


def oxirgisini_ochir():
    """Oxirgi yozuvni o'chiradi, jumlasini navbat boshiga qaytaradi."""
    with _qulf:
        h = _oqi()
        if not h["yozuvlar"]:
            return None
        y = h["yozuvlar"].pop()
        try:
            os.remove(os.path.join(KLIP_PAPKA, y["fayl"]))
        except OSError:
            pass
        h["navbat"].insert(0, y["matn"])
        _yoz(h)
        return y


def otkazib_yubor():
    with _qulf:
        h = _oqi()
        if h["navbat"]:
            h["ishlatilgan"].append(_iz(h["navbat"].pop(0)))
            _yoz(h)


def joriy_jumla():
    h = _oqi()
    return h["navbat"][0] if h["navbat"] else None


# ======================================================================
# DATASET EKSPORT
# ======================================================================
README = """O'Z OVOZIM — ovoz modelini o'qitish uchun yozuvlar
===================================================

klip/          — asl yozuvlar (Telegram'dan qanday kelgan bo'lsa)
metadata.csv   — fayl|matn|oqilish|soniya
                 matn     — siz o'qigan jumla
                 oqilish  — ovoz modeliga beriladigan shakl (bot talaffuz
                            lug'ati bilan: Google -> gugl). O'qitishda
                            shu ustunni ishlating — bot ham ovoz
                            yasaganda matnni aynan shu shaklda beradi.

O'qitishdan oldin: hammasini 24 kHz mono WAV ga o'tkazing, masalan:
  mkdir wavs; for f in klip/*; do
    ffmpeg -loglevel error -i "$f" -ac 1 -ar 24000 "wavs/$(basename "${f%.*}").wav"
  done

Bu fayllar — sizning ovozingiz. Ochiq joyga qo'ymang.
"""


def eksport(papka):
    """ZIP qismlarini yasaydi. Qaytadi: [yo'llar], statistika."""
    h = _oqi()
    qatorlar = ["fayl|matn|oqilish|soniya"]
    for y in h["yozuvlar"]:
        qatorlar.append("|".join([
            "klip/" + y["fayl"], y["matn"].replace("|", " "),
            talaffuz.ozgartir(y["matn"]).replace("|", " "), f"{y['sek']:.2f}"]))
    yollar, qism, hajm, zf = [], 0, 0, None

    def _yangi_qism():
        nonlocal qism, hajm, zf
        if zf:
            zf.close()
        qism += 1
        yol = os.path.join(papka, f"ovozim_{qism:02d}.zip")
        yollar.append(yol)
        zf = zipfile.ZipFile(yol, "w", zipfile.ZIP_STORED)
        hajm = 0

    _yangi_qism()
    zf.writestr("metadata.csv", "\n".join(qatorlar) + "\n")
    zf.writestr("README.txt", README)
    for y in h["yozuvlar"]:
        yol = os.path.join(KLIP_PAPKA, y["fayl"])
        if not os.path.exists(yol):
            continue
        olcham = os.path.getsize(yol)
        if hajm + olcham > QISM_MAKS and hajm > 0:
            _yangi_qism()
        zf.write(yol, "klip/" + y["fayl"])
        hajm += olcham
    zf.close()
    return yollar


# ======================================================================
# TELEGRAM
# ======================================================================
def _admin(update):
    return update.effective_user is not None and update.effective_user.id == ADMIN_ID


def _faolmi():
    if _sessiya["faol"] and time.time() - _sessiya["oxirgi"] > SESSIYA_SEK:
        _sessiya.update(faol=False, kutilayotgan=None)
    return _sessiya["faol"]


def _chiziq(daqiqa):
    ulush = min(1.0, daqiqa / max(1, MAQSAD_DAQIQA))
    toza = int(ulush * 10)
    return "▰" * toza + "▱" * (10 - toza)


def _jumla_tugmalari():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏭ O'tkazish", callback_data="oyz:skip"),
        InlineKeyboardButton("↩️ Oxirgisini o'chir", callback_data="oyz:del"),
    ], [InlineKeyboardButton("⏹ Tugatish", callback_data="oyz:stop")]])


async def _keyingi(xabar):
    """Joriy jumlani yuboradi (navbat bo'sh bo'lsa to'ldiradi)."""
    jumla = joriy_jumla()
    if jumla is None:
        await xabar.reply_text("⏳ Yangi jumlalar tayyorlanmoqda...")
        await asyncio.to_thread(navbatni_toldir)
        jumla = joriy_jumla()
    if jumla is None:
        await xabar.reply_text(
            "Jumla qolmadi va yangisini yaratib bo'lmadi (OPENAI_API_KEY?).\n"
            "O'z matningizni qo'shing: /ovoz_yozuv_matn matn")
        return
    s = statistika()
    await xabar.reply_text(
        f"🎙 #{s['soni'] + 1} · {s['daqiqa']:.1f}/{MAQSAD_DAQIQA} daqiqa "
        f"{_chiziq(s['daqiqa'])}\n\n{jumla}\n\n"
        "Voice xabar bilan o'qing.",
        reply_markup=_jumla_tugmalari())
    if s["navbat"] < 15:              # oldindan to'ldirib qo'yamiz
        asyncio.get_running_loop().run_in_executor(None, navbatni_toldir)


async def cmd_ovoz_yozuv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update):
        return
    _sessiya.update(faol=True, oxirgi=time.time(), kutilayotgan=None)
    s = statistika()
    await update.message.reply_text(
        "🎙 OVOZ YOZISH REJIMI\n\n"
        f"Yozilgan: {s['soni']} ta · {s['daqiqa']:.1f} daqiqa "
        f"(maqsad {MAQSAD_DAQIQA} daqiqa)\n{_chiziq(s['daqiqa'])}\n\n"
        "Qoidalar:\n"
        "• Tinch, aks-sado bermaydigan xona; telefon og'izdan 15-20 sm\n"
        "• Jumlani AYNAN yozilganidek o'qing — so'z qo'shmang, tashlamang\n"
        "• Tabiiy, podkastdagidek ohangda; shoshilmang\n"
        "• Xato qilsangiz — shunchaki qayta yuboring yoki «↩️ Oxirgisini o'chir»\n"
        "• Kuniga 15-20 daqiqa — ovoz charchamasin, bir xil eshitilsin\n\n"
        "Tugatish: «⏹ Tugatish» tugmasi. Zaxira: /ovoz_dataset")
    await _keyingi(update.message)


async def cmd_ovoz_yozuv_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update):
        return
    matn = (update.message.text or "").partition(" ")[2].strip()
    if not matn:
        await update.message.reply_text(
            "O'z matningizni (post, maqola) buyruqdan keyin yozing:\n"
            "/ovoz_yozuv_matn Bugun sizga ... \n\n"
            "Bot uni jumlalarga bo'lib, navbatning BOSHIGA qo'yadi.")
        return
    soni = _navbatga(matndan_jumlalar(matn), boshiga=True)
    await update.message.reply_text(
        f"✅ {soni} ta jumla navbat boshiga qo'shildi."
        + ("" if soni else f"\n(Jumla {JUMLA_MIN}-{JUMLA_MAKS} belgi bo'lishi "
           "kerak; takrorlar tashlanadi.)")
        + "\nBoshlash: /ovoz_yozuv")


async def cmd_ovoz_dataset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _admin(update):
        return
    s = statistika()
    if not s["soni"]:
        await update.message.reply_text("Hali yozuv yo'q. Boshlash: /ovoz_yozuv")
        return
    holat = await update.message.reply_text("📦 Tayyorlanmoqda...")
    papka = tempfile.mkdtemp(prefix="ovozim_")
    try:
        yollar = await asyncio.to_thread(eksport, papka)
        for i, yol in enumerate(yollar, 1):
            with open(yol, "rb") as f:
                await update.message.reply_document(
                    document=f, filename=os.path.basename(yol),
                    caption=(f"{s['soni']} ta yozuv · {s['daqiqa']:.1f} daqiqa"
                             if i == 1 else None),
                    read_timeout=300, write_timeout=300)
        await holat.edit_text(
            f"✅ {len(yollar)} ta fayl. Bu — ovozingiz zaxirasi: "
            "kompyuterda saqlang, ochiq joyga qo'ymang.")
    except Exception as e:
        log.warning("Ovoz dataset eksporti: %s", e)
        await holat.edit_text(f"Xato: {str(e)[:200]}")
    finally:
        import shutil
        shutil.rmtree(papka, ignore_errors=True)


def _fayl_turi(msg):
    """Qaytadi: (telegram fayl, kengaytma) yoki (None, None)."""
    if msg.voice:
        return msg.voice, "ogg"
    if msg.audio:
        nom = (msg.audio.file_name or "").lower()
        return msg.audio, (nom.rsplit(".", 1)[-1] if "." in nom else "m4a")[:5]
    if msg.document and (msg.document.mime_type or "").startswith("audio/"):
        nom = (msg.document.file_name or "").lower()
        return msg.document, (nom.rsplit(".", 1)[-1] if "." in nom else "wav")[:5]
    return None, None


async def on_ovoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rejim yoqiq bo'lsa — yozuvni ushlaydi (boshqa modullarga o'tmaydi)."""
    if not _admin(update) or not _faolmi():
        return
    msg = update.message
    fayl, ext = _fayl_turi(msg)
    if fayl is None:
        return
    jumla = joriy_jumla()
    if jumla is None:
        return
    _sessiya["oxirgi"] = time.time()
    if not re.fullmatch(r"[a-z0-9]{2,5}", ext):
        ext = "ogg"
    fd, yol = tempfile.mkstemp(prefix="oyz_", suffix="." + ext)
    os.close(fd)
    try:
        tg = await context.bot.get_file(fayl.file_id)
        await tg.download_to_drive(yol)
        sek, ogoh = await asyncio.to_thread(tekshir, yol, jumla)
    except Exception as e:
        log.warning("Ovoz yozuvi o'qilmadi: %s", e)
        await msg.reply_text("Yozuv o'qilmadi, qayta yuboring.")
        _ochir(yol)
        raise ApplicationHandlerStop
    eski = _sessiya.get("kutilayotgan")
    if eski:
        _ochir(eski["yol"])
        _sessiya["kutilayotgan"] = None
    if ogoh:
        _sessiya["kutilayotgan"] = {"yol": yol, "ext": ext, "matn": jumla, "sek": sek}
        await msg.reply_text(
            f"⚠️ Saqlanmadi ({sek:.1f} s):\n• " + "\n• ".join(ogoh)
            + "\n\nQayta o'qib yuboring yoki:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Baribir saqlash", callback_data="oyz:save"),
                InlineKeyboardButton("⏭ O'tkazish", callback_data="oyz:skip"),
            ]]))
        raise ApplicationHandlerStop
    yozuv = await asyncio.to_thread(_saqla, yol, ext, jumla, sek)
    await msg.reply_text(f"✅ Saqlandi · {sek:.1f} s")
    await _keyingi(msg)
    raise ApplicationHandlerStop


def _ochir(yol):
    try:
        os.remove(yol)
    except OSError:
        pass


async def on_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer()
        return
    amal = q.data.split(":", 1)[1]
    _sessiya.update(faol=True, oxirgi=time.time())
    if amal == "stop":
        k = _sessiya.get("kutilayotgan")
        if k:
            _ochir(k["yol"])
        _sessiya.update(faol=False, kutilayotgan=None)
        s = statistika()
        await q.answer("To'xtatildi")
        await q.message.reply_text(
            f"⏹ Rejim o'chirildi. Jami: {s['soni']} ta · {s['daqiqa']:.1f} "
            f"daqiqa {_chiziq(s['daqiqa'])}\n\nDavom: /ovoz_yozuv · "
            "Zaxira: /ovoz_dataset")
        return
    if amal == "save":
        k = _sessiya.get("kutilayotgan")
        _sessiya["kutilayotgan"] = None
        if not k or k["matn"] != joriy_jumla() or not os.path.exists(k["yol"]):
            await q.answer("Bu yozuv endi yo'q")
            return
        yozuv = await asyncio.to_thread(_saqla, k["yol"], k["ext"], k["matn"], k["sek"])
        await q.answer("Saqlandi")
        await q.message.reply_text(f"✅ Saqlandi · {k['sek']:.1f} s")
    elif amal == "skip":
        k = _sessiya.get("kutilayotgan")
        if k:
            _ochir(k["yol"])
        _sessiya["kutilayotgan"] = None
        otkazib_yubor()
        await q.answer("O'tkazildi")
    elif amal == "del":
        y = await asyncio.to_thread(oxirgisini_ochir)
        await q.answer("O'chirildi" if y else "Yozuv yo'q")
        if y:
            await q.message.reply_text("↩️ Oxirgi yozuv o'chirildi — qayta o'qing:")
    await _keyingi(q.message)


def register(app: Application):
    """bot.py dan: ovoz_yozuv.register(app)"""
    if not ADMIN_ID:
        return
    app.add_handler(CommandHandler("ovoz_yozuv", cmd_ovoz_yozuv))
    app.add_handler(CommandHandler("ovoz_yozuv_matn", cmd_ovoz_yozuv_matn))
    app.add_handler(CommandHandler("ovoz_dataset", cmd_ovoz_dataset))
    app.add_handler(CallbackQueryHandler(on_tugma, pattern=r"^oyz:"))
    # -4 guruh: maqola.py (-3) va agent.py (0) dagi ovoz ushlovchilaridan
    # OLDIN. Rejim o'chiq bo'lsa tegmaydi — ovoz odatdagidek o'tadi.
    app.add_handler(MessageHandler(
        (filters.VOICE | filters.AUDIO | filters.Document.AUDIO)
        & filters.User(user_id=ADMIN_ID), on_ovoz), group=-4)
    log.info("Ovoz yozuvi moduli yoqildi")
