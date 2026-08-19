# -*- coding: utf-8 -*-
"""
SUBTITR MODULI — video uchun o'zbekcha subtitr  (faqat ADMIN uchun)
===================================================================
Ishlash tartibi:
  1. Admin botga video tashlaydi
  2. ffmpeg videodan ovozni ajratadi (kichik mono mp3)
  3. Whisper (whisper-1) matnga o'giradi — VAQT BELGILARI bilan
     (diqqat: gpt-4o transkripsiya modellari vaqt belgisi bermaydi).
     Uzun yozuv bo'laklarga bo'lib o'giriladi — video uzunligi cheklovsiz.
  4. AI segmentlarni o'zbekchaga o'giradi — to'plamlab, kontekst saqlanadi
  5. Matn "kartalar"ga bo'linadi (1-2 qator), .srt yasaladi va kuyiladi
  6. Admin oladi: subtitrli video + .srt fayl + to'liq tarjima matni

KO'RINISH: standart uslub — "captions", ya'ni Captions/CapCut ilovalaridagi
ko'rinish: Montserrat ExtraBold, yirik matn, bir kartada 7 tagacha so'z,
ekranning pastki uchdan birida. /uslub buyrug'i bilan almashtiriladi.

Qator eni endi qo'lda sozlanmaydi — matn eni SHRIFTNING O'ZIDAN o'lchanadi
(Pillow), shuning uchun shrift almashsa ham qatorlar to'g'ri bo'linadi.

MUHIM: og'ir ishlar (ffmpeg, API) asyncio.to_thread orqali ishlaydi —
botning qolgan qismi muzlab qolmaydi.

Railway'da ffmpeg BO'LISHI SHART. Bo'lmasa repoga nixpacks.toml qo'shiladi.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

try:  # Pillow — mavjud subtitrni aniqlash va matn enini o'lchash uchun
    from PIL import Image, ImageFont
except Exception:
    Image = ImageFont = None

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
MODEL_SMART = os.environ.get("AI_MODEL_SMART", "gpt-5.6-terra")
STT_MODEL = os.environ.get("AI_MODEL_STT", "whisper-1")   # vaqt belgisi beradi

# Ovoz bo'lak-bo'lak o'girilgani uchun uzun video ham o'tadi.
# Chegara faqat xavfsizlik uchun — tasodifan 1 soatlik fayl kelib qolmasin.
MAX_SECONDS = int(os.environ.get("SUBTITR_MAX_SEC", "1800"))   # 30 daqiqa
# Whisper 25 MB fayl qabul qiladi. 48 kbit/s mono'da 15 daqiqa ≈ 5.4 MB —
# zaxira bilan sig'adi va bitta so'rov ham juda cho'zilib ketmaydi.
STT_BOLAK_SEK = int(os.environ.get("SUBTITR_STT_BOLAK", "900"))
# Tarjima ham to'plamlarga bo'linadi: bitta javobda 400 ta segment
# so'ralsa, model matnni qirqib qo'yadi.
TARJIMA_TOPLAM = int(os.environ.get("SUBTITR_TARJIMA_TOPLAM", "60"))

# Bo'sh qoldirilsa — video formatiga qarab AVTOMATIK tanlanadi.
# Qiymat berilsa — o'sha ustuvor (shrift almashganda qo'l bilan sozlash uchun).
_LINE_ENV = os.environ.get("SUBTITR_LINE", "").strip()
_FS_ENV = os.environ.get("SUBTITR_FONT_SIZE", "").strip()
MAX_LINE = int(_LINE_ENV) if _LINE_ENV.isdigit() else 0   # 0 = o'lchab topiladi
FONT_SIZE = int(_FS_ENV) if _FS_ENV.isdigit() else 0      # 0 = uslub belgilaydi
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
BRAND = os.environ.get("SUBTITR_BRAND", "@safaroov_blog")   # videodagi yozuv
BRAND_OLCHAM = int(os.environ.get("SUBTITR_BRAND_OLCHAM", "28"))  # h/28 — kichikroq son = kattaroq yozuv
BRAND_ORQA = os.environ.get("SUBTITR_BRAND_ORQA", "0.92")         # matn shaffofligi
BRAND_QUTI = os.environ.get("SUBTITR_BRAND_QUTI", "0.35")         # orqa quti (0 = quti yo'q)
BRAND_JOY = os.environ.get("SUBTITR_BRAND_JOY", "tepa_chap")      # tepa_chap/tepa_ong/past_chap/past_ong
KANAL = os.environ.get("CHANNEL_ID", "@safaroov_blog")      # qaysi kanalga
# Bo'sh bo'lsa — uslubning o'z shrifti ishlatiladi (pastdagi USLUBLAR).
FONT_NAME = os.environ.get("SUBTITR_FONT", "").strip()

# Brend yozuvi (video burchagidagi @kanal) uchun shrift.
# Repodagi shrift birinchi: Railway'da tizim shriftlari kafolatlanmagan.
_FONT_YOLLARI = [
    os.path.join(FONTS_DIR, "TTDrugs-BoldItalic.ttf"),
    os.path.join(FONTS_DIR, "Montserrat-ExtraBold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

_client = None


def ai():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


def ffmpeg_bor():
    return shutil.which("ffmpeg") is not None


# ======================================================================
# TARJIMA PROMPTI — subtitr uchun maxsus (qisqalik muhim)
# ======================================================================
TARJIMA_PROMPT = """Sen ikki tomonlama mutaxassissan: chet tilini eng yuqori \
darajada tushunasan va o'zbek tilining professional muharririsan. Vazifang — \
video nutqini O'ZBEK TILIGA (lotin yozuvida) subtitr qilib o'girish.

A. MA'NONI TO'G'RI OLISH (birinchi navbatda):
1. IBORALARNI so'zma-so'z o'girma — o'zbekcha muqobilini top. \
"it's a game changer" -> "bu hammasini o'zgartiradi" (o'yin almashtirgich EMAS). \
"reach out" -> "murojaat qilish". "keep up with" -> "ortda qolmaslik".
2. OHANGNI SAQLA: ishonchsizlik ("I guess", "sort of", "maybe") -> \
"menimcha", "shekilli", "balki". Qat'iylik ("absolutely", "definitely") -> \
"albatta", "shubhasiz". Yumshatib yoki kuchaytirib yuborma.
3. FE'L ZAMONI va shaxsni aniq ber. "we were building" -> "qurayotgan edik" \
(qurdik EMAS).
4. ATAMALAR: keng tarqalgani o'zbekcha ("model", "ma'lumot", "tarmoq"), \
lekin sohaviy atama tarjimasiz tushunarliroq bo'lsa — asl holicha \
("machine learning" -> "machine learning" emas, "mashinali o'qitish"; \
lekin "startup" -> "startap", "AI" -> "AI").
5. Ism, kompaniya, mahsulot nomlari MANBADAGIDEK: Mark Zuckerberg, Alphabet, \
Steve Jobs. O'zbekchalashtirishga urinma.

B. SUBTITR TALABLARI:
6. QISQA yoz. Subtitr ekranda 2-4 soniya turadi — o'quvchi o'qib ulgurishi \
kerak. Uzun jumlani ikkiga bo'lib emas, QISQARTIRIB ber.
7. Har segment alohida tarjima qilinadi, lekin oldingisi bilan mazmunan \
bog'lansin. Segmentlarni birlashtirma yoki bo'lma.
8. Nutqdagi ikkilanish, takror, "uh", "you know", "I mean" — TUSHIRIB QOLDIR. \
Toza, tugallangan jumla yoz.

C. O'ZBEK TILI SIFATI:
9. Jonli, og'zaki-adabiy til. Kitobiy va idoraviy iboralar TAQIQ: "ushbu", \
"mazkur", "hisoblanadi", "amalga oshirmoqda", "e'tibor qaratmoq", \
"...bo'yicha", "...tomonidan".
10. Bitta jumlada ikkita "uchun" yoki "ushbu" bo'lmasin.
11. Ruscha-inglizcha ko'chirmalar taqiq: "yangradi" (прозвучало) -> \
"aytildi"; "issiq to'lqinlar" -> "jazirama issiq".
12. Sonlar: to'rt xonagacha so'z bilan qulay ("uch yil"), kattalari raqamda \
("117 mln"). Valyuta belgisi emas, so'z bilan: "$20" -> "20 dollar".

D. QAT'IY TAQIQ:
13. Manbada YO'Q narsani QO'SHMA. To'qima fakt, to'qima izoh, "menimcha" \
qabilidagi o'z fikring — TAQIQ.
14. Tushunmagan joyingni tashlab ketma — eng yaqin ma'noni ber.

O'Z-O'ZINI TEKSHIRISH: har qatorni o'qib chiq — (1) o'zbek shunday gapiradimi? \
(2) 2-4 soniyada o'qib bo'ladimi? (3) manbadagi ma'no to'liq saqlanganmi?

JAVOB SHAKLI — faqat JSON, izohsiz:
{"lines": [{"n": 1, "uz": "tarjima"}, {"n": 2, "uz": "tarjima"}]}
Har kirish segmenti uchun bittadan qator bo'lishi SHART."""


# ======================================================================
# YORDAMCHILAR
# ======================================================================
def _vaqt(sek):
    """12.34 -> '00:00:12,340'"""
    if sek < 0:
        sek = 0
    soat = int(sek // 3600)
    daq = int((sek % 3600) // 60)
    son = int(sek % 60)
    mil = int(round((sek - int(sek)) * 1000))
    if mil > 999:
        mil = 999
    return f"{soat:02d}:{daq:02d}:{son:02d},{mil:03d}"


# ======================================================================
# USLUB TO'PLAMLARI
# ======================================================================
# libass SRT faylni ASS'ga o'girganda standart "sahna" o'lchovi 384x288
# bo'ladi va tayyor tasvir video o'lchamiga masshtablanadi. Shuning uchun
# barcha o'lchovlar (FontSize, MarginV, matn eni) SHU 384x288 tizimida.
ASS_EN, ASS_BAL = 384.0, 288.0

# Har uslub — tugallangan to'plam: shrift, ASS bo'lagi, o'lcham, joylashuv.
#   shrift     — libass'ga beriladigan oila nomi (shriftning ichidagi nom)
#   fayl       — fonts/ dagi fayl; matn enini O'LCHASH uchun kerak
#   ass        — force_style bo'lagi
#   olcham     — video nisbatiga qarab FontSize
#   en_ulush   — matn maydoni kadr enining necha ulushini egallaydi
#   maks_qator — bir kartada nechta qator
#   maks_soz   — bir kartada nechta so'z (0 = cheklovsiz)
#   margin     — pastdan masofa (288 birlik ichida)
#   spacing    — ASS Spacing qiymati (o'lchashda hisobga olinadi)
USLUBLAR = {
    "captions": {
        "izoh": "Captions ilovasidek — yirik qalin matn, qisqa bo'laklar",
        "shrift": "Montserrat ExtraBold",
        "fayl": "Montserrat-ExtraBold.ttf",
        "ass": ("PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=2.6,Shadow=1.1,Bold=0,Spacing=0.4"),
        "olcham": {"tik": 18, "4:5": 17, "kvadrat": 16, "keng": 15},
        "en_ulush": {"tik": 0.86, "4:5": 0.84, "kvadrat": 0.78, "keng": 0.62},
        "maks_qator": 2, "maks_soz": 7, "margin": 96, "spacing": 0.4,
    },
    "klassik": {
        "izoh": "Oq qalin, ingichka kontur — universal",
        "shrift": "Montserrat SemiBold",
        "fayl": "Montserrat-SemiBold.ttf",
        "ass": ("PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=0.9,Shadow=1.2,Bold=0,Spacing=0.2"),
        "olcham": {"tik": 13, "4:5": 14, "kvadrat": 15, "keng": 16},
        "en_ulush": {"tik": 0.88, "4:5": 0.86, "kvadrat": 0.82, "keng": 0.74},
        "maks_qator": 2, "maks_soz": 0, "margin": 70, "spacing": 0.2,
    },
    "qutili": {
        "izoh": "Yarim shaffof qora qutida — har qanday fonda o'qiladi",
        "shrift": "Montserrat SemiBold",
        "fayl": "Montserrat-SemiBold.ttf",
        "ass": ("PrimaryColour=&HFFFFFF,BackColour=&HA0000000,"
                "BorderStyle=3,Outline=0.8,Shadow=0,Bold=0,Spacing=0.2"),
        "olcham": {"tik": 13, "4:5": 14, "kvadrat": 15, "keng": 16},
        "en_ulush": {"tik": 0.86, "4:5": 0.84, "kvadrat": 0.80, "keng": 0.72},
        "maks_qator": 2, "maks_soz": 0, "margin": 74, "spacing": 0.2,
    },
    "kontrast": {
        "izoh": "Qalin qora kontur — sershovqin videolar uchun",
        "shrift": "Montserrat ExtraBold",
        "fayl": "Montserrat-ExtraBold.ttf",
        "ass": ("PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=3.0,Shadow=0,Bold=0,Spacing=0.1"),
        "olcham": {"tik": 15, "4:5": 15, "kvadrat": 15, "keng": 16},
        "en_ulush": {"tik": 0.88, "4:5": 0.86, "kvadrat": 0.82, "keng": 0.70},
        "maks_qator": 2, "maks_soz": 0, "margin": 78, "spacing": 0.1,
    },
    "oltin": {
        "izoh": "Sariq-oltin urg'u — reels uslubi",
        "shrift": "Montserrat ExtraBold",
        "fayl": "Montserrat-ExtraBold.ttf",
        "ass": ("PrimaryColour=&H4FD7FF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=2.2,Shadow=1.0,Bold=0,Spacing=0.4"),
        "olcham": {"tik": 18, "4:5": 17, "kvadrat": 16, "keng": 15},
        "en_ulush": {"tik": 0.86, "4:5": 0.84, "kvadrat": 0.78, "keng": 0.62},
        "maks_qator": 2, "maks_soz": 7, "margin": 96, "spacing": 0.4,
    },
    "yumshoq": {
        "izoh": "Konturisiz, faqat soya — tinch videolar uchun",
        "shrift": "Montserrat SemiBold",
        "fayl": "Montserrat-SemiBold.ttf",
        "ass": ("PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=0,Shadow=2.2,Bold=0,Spacing=0.3"),
        "olcham": {"tik": 13, "4:5": 14, "kvadrat": 15, "keng": 16},
        "en_ulush": {"tik": 0.86, "4:5": 0.84, "kvadrat": 0.80, "keng": 0.72},
        "maks_qator": 2, "maks_soz": 0, "margin": 72, "spacing": 0.3,
    },
}
USLUB = os.environ.get("SUBTITR_USLUB", "captions")
# 0 = uslubning o'z qiymati ishlatiladi
MARGIN_ODDIY = int(os.environ.get("SUBTITR_MARGIN", "0") or "0")
MARGIN_YUQORI = int(os.environ.get("SUBTITR_MARGIN2", "150"))  # mavjud subtitr bo'lsa
# Barcha matnni BOSH HARFDA ko'rsatish (reels uslubi)
KATTA_HARF = os.environ.get("SUBTITR_KATTA_HARF", "0").strip() in ("1", "ha", "true")
# Bir karta ekranda kamida shuncha turadi
MIN_KARTA = float(os.environ.get("SUBTITR_MIN_KARTA", "0.7"))


def uslub_ol(nomi=None):
    return USLUBLAR.get(nomi or USLUB, USLUBLAR["captions"])


# ======================================================================
# MATN ENINI O'LCHASH
# ======================================================================
# Qatorga nechta belgi sig'ishini taxmin qilish o'rniga shriftning O'ZIDAN
# o'lchaymiz. Shrift almashsa ham qator eni to'g'ri qoladi — ilgari bu
# qiymat qo'lda sozlanardi va har shrift uchun qaytadan tuzatish kerak edi.
_OLCHOV_MASSHTAB = 8          # aniqlik uchun kattaroq o'lchamda o'lchab, bo'lamiz
_shrift_kesh = {}


def _shrift_yoli(uslub):
    yol = os.path.join(FONTS_DIR, uslub.get("fayl") or "")
    return yol if uslub.get("fayl") and os.path.exists(yol) else None


def _olchov_shrifti(yol, px):
    kalit = (yol, px)
    if kalit not in _shrift_kesh:
        _shrift_kesh[kalit] = ImageFont.truetype(yol, px)
    return _shrift_kesh[kalit]


def matn_eni(matn, uslub, fs):
    """Matn enini ASS birligida qaytaradi (FontSize = em balandligi)."""
    spacing = uslub.get("spacing", 0.0) * len(matn)
    yol = _shrift_yoli(uslub)
    if ImageFont is None or not yol:
        return len(matn) * fs * 0.58 + spacing      # taxminiy zaxira
    try:
        f = _olchov_shrifti(yol, max(int(fs * _OLCHOV_MASSHTAB), 8))
        return f.getlength(matn) / _OLCHOV_MASSHTAB + spacing
    except Exception as e:
        log.warning("Shrift o'lchanmadi (%s): %s", yol, e)
        return len(matn) * fs * 0.58 + spacing


# ======================================================================
# MATNNI KARTALARGA BO'LISH
# ======================================================================
_TINISH = ".,!?;:…"


def _iboralarga(sozlar):
    """So'zlarni tinish belgisi bo'yicha ibora-ibora guruhlaydi.
    Shu tufayli qator jumla o'rtasidan emas, ma'no chegarasidan uziladi."""
    ibora, natija = [], []
    for s in sozlar:
        ibora.append(s)
        if s and s[-1] in _TINISH:
            natija.append(ibora)
            ibora = []
    if ibora:
        natija.append(ibora)
    return natija


def _joylash(sozlar, maks_en, olcha, maks_qator, maks_belgi=0):
    """So'zlarni eng kam sondagi qatorga MUVOZANATLI joylaydi.
    Qaytaradi: qatorlar ro'yxati, sig'masa None.

    Muvozanat muhim: 'juda uzun birinchi qator + bitta so'z' ko'rinishi
    subtitrni xunuk qiladi. Shuning uchun qatorlar soni bir xil bo'lgan
    variantlardan eng uzun qatori eng qisqasi tanlanadi."""
    n = len(sozlar)
    if not n:
        return []
    CHEK = float("inf")
    en = [[CHEK] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(i + 1, n + 1):
            qator = " ".join(sozlar[i:j])
            e = olcha(qator)
            if (e > maks_en or (maks_belgi and len(qator) > maks_belgi)) \
                    and j > i + 1:
                break                      # uzunroq bo'lagi ham sig'maydi
            en[i][j] = e
    dp = [[None] * (n + 1) for _ in range(maks_qator + 1)]
    dp[0][0] = (0.0, [])
    for k in range(1, maks_qator + 1):
        for j in range(1, n + 1):
            eng = None
            for i in range(j):
                if dp[k - 1][i] is None or en[i][j] == CHEK:
                    continue
                qiymat = max(dp[k - 1][i][0], en[i][j])
                if eng is None or qiymat < eng[0]:
                    eng = (qiymat, dp[k - 1][i][1] + [" ".join(sozlar[i:j])])
            dp[k][j] = eng
        if dp[k][n] is not None:            # eng kam qator afzal
            return dp[k][n][1]
    return None


def kartalarga(matn, uslub, fs, maks_en):
    """Matnni ekranda ketma-ket ko'rinadigan "kartalar"ga bo'ladi.
    Har karta — bir vaqtda ko'rinadigan 1-2 qator."""
    matn = " ".join((matn or "").split())
    if not matn:
        return []
    if KATTA_HARF:
        matn = matn.upper()
    maks_qator = uslub.get("maks_qator", 2)
    maks_soz = uslub.get("maks_soz", 0)

    def olcha(t):
        return matn_eni(t, uslub, fs)

    def joyla(sozlar):
        if maks_soz and len(sozlar) > maks_soz:
            return None
        return _joylash(sozlar, maks_en, olcha, maks_qator, MAX_LINE)

    kartalar, joriy = [], []
    for ibora in _iboralarga(matn.split(" ")):
        if joriy and joyla(joriy + ibora) is None:
            kartalar.append(joriy)
            joriy = []
        if not joriy and joyla(ibora) is None:
            # Ibora yolg'iz o'zi ham sig'maydi — so'zma-so'z to'ldiramiz
            bolak = []
            for s in ibora:
                if bolak and joyla(bolak + [s]) is None:
                    kartalar.append(bolak)
                    bolak = []
                bolak.append(s)
            joriy = bolak
        else:
            joriy = joriy + ibora
    if joriy:
        kartalar.append(joriy)
    return ["\n".join(joyla(k) or [" ".join(k)]) for k in kartalar]


def vaqtga_taqsimla(segmentlar, tarjimalar, uslub, fs, maks_en):
    """Har segmentni kartalarga bo'lib, vaqtini uzunligiga qarab taqsimlaydi.
    Natija: ekranda bir vaqtda faqat bitta qisqa karta turadi."""
    natija = []
    for (b, o, _), matn in zip(segmentlar, tarjimalar):
        kartalar = kartalarga(matn, uslub, fs, maks_en)
        if not kartalar:
            continue
        davom = max(float(o) - float(b), 0.8)
        jami = sum(len(x) for x in kartalar) or 1
        t = float(b)
        for i, karta in enumerate(kartalar):
            ulush = davom * (len(karta) / jami)
            oxiri = float(o) if i == len(kartalar) - 1 else t + ulush
            if oxiri - t < MIN_KARTA:
                oxiri = t + MIN_KARTA
            natija.append((t, oxiri, karta))
            t = oxiri

    # Vaqtlarni tartibga solamiz: kartalar bir-birining ustiga chiqmasin va
    # hech biri MIN_KARTA dan qisqa bo'lmasin. Whisper ba'zan bir xil
    # boshlanish vaqtiga ega segment qaytaradi — shunda subtitr sakraydi.
    tozalangan, oxirgi = [], 0.0
    for b, o, m in natija:
        b = max(b, oxirgi)
        o = max(o, b + MIN_KARTA)
        tozalangan.append((b, o, m))
        oxirgi = o
    return tozalangan


def srt_yasa(segmentlar):
    """[(bosh, oxir, matn), ...] -> .srt matni"""
    qismlar = []
    for i, (b, o, m) in enumerate(segmentlar, 1):
        if o <= b:
            o = b + 1.2
        qismlar.append(f"{i}\n{_vaqt(b)} --> {_vaqt(o)}\n{m.strip()}\n")
    return "\n".join(qismlar)


def _nisbat_kalit(en, balandlik):
    if balandlik <= 0:
        return "tik"
    nisbat = en / balandlik
    if nisbat < 0.70:
        return "tik"          # 9:16 — Reels, TikTok, Shorts
    if nisbat < 0.95:
        return "4:5"          # Instagram
    if nisbat < 1.30:
        return "kvadrat"      # 1:1
    return "keng"             # 16:9 — YouTube


def format_sozlamasi(en, balandlik, uslub_nomi=None):
    """Video nisbatiga qarab (shrift o'lchami, matn maydoni eni, yon chekka).
    Env orqali qiymat berilgan bo'lsa — O'SHA ustuvor."""
    u = uslub_ol(uslub_nomi)
    kalit = _nisbat_kalit(en, balandlik)
    fs = FONT_SIZE or u["olcham"][kalit]
    maks_en = ASS_EN * u["en_ulush"][kalit]
    yon = int(round((ASS_EN - maks_en) / 2))
    return fs, maks_en, yon


def _video_olchami(video_yol):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", video_yol],
        capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)
    except (ValueError, IndexError):
        return 720, 1280


def mavjud_subtitr_bormi(video_yol, davomiylik):
    """Videoda ALLAQACHON kuydirilgan subtitr bor-yo'qligini VA qayerdaligini
    aniqlaydi. Bir necha kadrni tekshirib, matnga o'xshash sohani qidiradi.

    Qaytaradi: (band_ulush, eng_yuqori_nuqta)
      band_ulush     — 0.0-1.0, nechta kadrda matn topilgani
      eng_yuqori_nuqta — matn boshlanadigan joy (0.0 = tepa, 1.0 = past)

    DIQQAT: taxminiy usul. Oq kiyim yoki yorug' fon ham 'matn' deb
    hisoblanishi mumkin, shuning uchun chegara ehtiyotkor qo'yilgan."""
    if Image is None:
        return 0.0, 1.0
    band, tekshirildi = 0, 0
    eng_yuqori = 1.0
    nuqtalar = [davomiylik * k for k in (0.2, 0.4, 0.6, 0.8)]
    papka = tempfile.mkdtemp(prefix="scan_")
    try:
        for i, t in enumerate(nuqtalar):
            kadr = os.path.join(papka, f"k{i}.png")
            r = subprocess.run(
                ["ffmpeg", "-ss", f"{t:.2f}", "-i", video_yol, "-frames:v", "1",
                 "-vf", "scale=320:-1", "-y", kadr], capture_output=True)
            if r.returncode != 0 or not os.path.exists(kadr):
                continue
            im = Image.open(kadr).convert("L")
            W, H = im.size
            tekshirildi += 1
            topildi_kadrda = False
            # pastki yarmini yupqa yo'laklarga bo'lib skanerlaymiz
            yolak = max(int(H * 0.03), 4)
            y = int(H * 0.45)
            while y + yolak <= H:
                qism = im.crop((0, y, W, y + yolak))
                px = list(qism.getdata())
                if px:
                    oq = sum(1 for p in px if p > 225) / len(px)
                    qora = sum(1 for p in px if p < 60) / len(px)
                    if oq > 0.02 and qora > 0.05:      # matnga xos qarama-qarshilik
                        topildi_kadrda = True
                        eng_yuqori = min(eng_yuqori, y / H)
                        break
                y += yolak
            if topildi_kadrda:
                band += 1
    except Exception as e:
        log.warning("Kadr tahlili xatosi: %s", e)
    finally:
        shutil.rmtree(papka, ignore_errors=True)
    return ((band / tekshirildi) if tekshirildi else 0.0), eng_yuqori


def margin_asosi(uslub_nomi=None):
    """Uslubning odatdagi pastki chekkasi (env qiymati ustuvor)."""
    return MARGIN_ODDIY or uslub_ol(uslub_nomi)["margin"]


def margin_hisobla(eng_yuqori, uslub_nomi=None):
    """Mavjud subtitr tepasiga bizning matnni joylash uchun MarginV.
    ASS o'lchovi 288 birlik balandlikka nisbatan hisoblanadi."""
    pastdan = (1.0 - eng_yuqori) * ASS_BAL   # mavjud matn qayerdan boshlanadi
    kerak = int(pastdan + 26)                # + o'z matnimiz balandligi va bo'shliq
    return max(margin_asosi(uslub_nomi), min(kerak, 150))


# ======================================================================
# BLOKLOVCHI ISHLAR (to_thread orqali chaqiriladi)
# ======================================================================
def _ovoz_ajrat(video_yol, ovoz_yol):
    """Videodan kichik mono mp3 ajratadi (Whisper 25 MB chegarasi uchun)."""
    r = subprocess.run(
        ["ffmpeg", "-i", video_yol, "-vn", "-ac", "1", "-ar", "16000",
         "-b:a", "48k", "-y", ovoz_yol],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Ovoz ajratilmadi: {r.stderr[-300:]}")


def _davomiylik(video_yol):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_yol],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _transkripsiya_bir(ovoz_yol, siljish=0.0):
    """Bitta ovoz faylini o'giradi. `siljish` — vaqt belgilariga qo'shiladi
    (uzun yozuv bo'laklarga bo'linganda kerak bo'ladi)."""
    with open(ovoz_yol, "rb") as f:
        r = ai().audio.transcriptions.create(
            model=STT_MODEL, file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"])
    segs = getattr(r, "segments", None) or []
    natija = []
    for s in segs:
        b = getattr(s, "start", None)
        o = getattr(s, "end", None)
        t = (getattr(s, "text", "") or "").strip()
        if b is None and isinstance(s, dict):
            b, o, t = s.get("start"), s.get("end"), (s.get("text") or "").strip()
        if t:
            natija.append((float(b or 0) + siljish, float(o or 0) + siljish, t))
    til = getattr(r, "language", "") or ""
    return natija, til


def _ovoz_bolagi(ovoz_yol, bosh, davom, chiqish_yol):
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-ss", f"{bosh:.2f}", "-t", f"{davom:.2f}", "-i", ovoz_yol,
         "-ac", "1", "-ar", "16000", "-b:a", "48k", "-y", chiqish_yol],
        capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(chiqish_yol):
        raise RuntimeError(f"Ovoz bo'lagi ajratilmadi: {r.stderr[-300:]}")


def _transkripsiya(ovoz_yol, davomiylik=0.0):
    """Whisper — segment darajasidagi vaqt belgilari bilan.

    Whisper bitta so'rovda 25 MB gacha fayl oladi, shuning uchun uzun yozuv
    STT_BOLAK_SEK bo'yicha kesiladi va vaqt belgilari qayta bir tizimga
    keltiriladi. Video uzunligi cheklovi shu sababli olib tashlandi."""
    davomiylik = davomiylik or _davomiylik(ovoz_yol)
    if davomiylik <= STT_BOLAK_SEK + 30:
        return _transkripsiya_bir(ovoz_yol)

    papka = tempfile.mkdtemp(prefix="stt_")
    hammasi, til, t, i = [], "", 0.0, 0
    try:
        while t < davomiylik:
            bolak = os.path.join(papka, f"b{i}.mp3")
            _ovoz_bolagi(ovoz_yol, t, STT_BOLAK_SEK, bolak)
            segs, bolak_til = _transkripsiya_bir(bolak, t)
            hammasi += segs
            til = til or bolak_til
            t += STT_BOLAK_SEK
            i += 1
    finally:
        shutil.rmtree(papka, ignore_errors=True)
    return hammasi, til


def _tarjima_toplam(matnlar, kontekst=""):
    """Bitta to'plamni o'giradi. Qaytadi: tartib bo'yicha tarjimalar."""
    kirish = "\n".join(f"[{i}] {t}" for i, t in enumerate(matnlar, 1))
    xabarlar = [{"role": "system", "content": TARJIMA_PROMPT}]
    if kontekst:
        xabarlar.append({
            "role": "user",
            "content": ("OLDINGI QISM (faqat kontekst uchun, tarjima QILINMAYDI "
                        "va javobga KIRMAYDI):\n" + kontekst)})
    xabarlar.append({"role": "user", "content": kirish})
    r = ai().chat.completions.create(
        model=MODEL_SMART,
        response_format={"type": "json_object"},
        max_completion_tokens=120 * len(matnlar) + 400,
        messages=xabarlar)
    data = json.loads(r.choices[0].message.content)
    xarita = {}
    for el in (data.get("lines") or []):
        try:
            xarita[int(el.get("n"))] = (el.get("uz") or "").strip()
        except (TypeError, ValueError):
            continue
    # tushib qolgan segment bo'lsa — asl matn qoladi (bo'sh qolmasin)
    return [xarita.get(i) or matnlar[i - 1] for i in range(1, len(matnlar) + 1)]


def _tarjima(segmentlar, toplam_no=None):
    """Segmentlarni o'giradi.

    Uzun videoda segment yuzlab bo'ladi — hammasini bitta javobda so'rasak,
    model matnni yarmida qirqib qo'yadi. Shuning uchun TARJIMA_TOPLAM tadan
    bo'lib so'raymiz, har to'plamga oldingisining oxirgi qatorlari kontekst
    qilib beriladi — shunda ohang va atamalar bir xil qoladi.

    toplam_no — ixtiyoriy: (nechanchi, nechtadan) bilan chaqiriladigan
    funksiya (jarayonni ko'rsatish uchun)."""
    matnlar = [t for _, _, t in segmentlar]
    if len(matnlar) <= TARJIMA_TOPLAM:
        if toplam_no:
            toplam_no(1, 1)
        return _tarjima_toplam(matnlar)

    natija, kontekst = [], ""
    jami = (len(matnlar) + TARJIMA_TOPLAM - 1) // TARJIMA_TOPLAM
    for k in range(jami):
        bolak = matnlar[k * TARJIMA_TOPLAM:(k + 1) * TARJIMA_TOPLAM]
        if toplam_no:
            toplam_no(k + 1, jami)
        uz = _tarjima_toplam(bolak, kontekst)
        natija += uz
        kontekst = " ".join(uz[-3:])
    return natija


def _kuydir(video_yol, srt_yol, chiqish_yol, fs=None, marginv=None,
            uslub_nomi=None, yon=None):
    """Subtitrni videoga kuydiradi.
    fs        — shrift o'lchami (video formatiga qarab tanlanadi)
    marginv   — pastdan masofa (mavjud subtitr bo'lsa oshiriladi)
    uslub_nomi— USLUBLAR dan biri
    yon       — chap/o'ng chekka (matn maydoni enidan hisoblanadi)

    DIQQAT: libass shriftni video o'lchamiga O'ZI masshtablaydi (384x288
    etalon). Shuning uchun fs video eniga qarab kattalashtirilmaydi."""
    u = uslub_ol(uslub_nomi)
    fs = fs or FONT_SIZE or u["olcham"]["tik"]
    marginv = marginv if marginv is not None else margin_asosi(uslub_nomi)
    yon = yon if yon is not None else 20
    shrift = FONT_NAME or u["shrift"]
    uslub = (f"FontName={shrift},FontSize={fs},{u['ass']},"
             f"Alignment=2,MarginV={marginv},MarginL={yon},MarginR={yon}")

    papka = os.path.dirname(srt_yol) or "."
    nom = os.path.basename(srt_yol)
    filtr = f"subtitles={nom}:force_style='{uslub}'"
    if os.path.isdir(FONTS_DIR):      # repodagi fonts/ papkasidan shrift olinadi
        filtr += f":fontsdir={FONTS_DIR}"
    brend_shrift = next((f for f in _FONT_YOLLARI if os.path.exists(f)), None)
    if BRAND and brend_shrift:
        matn = BRAND.replace("'", "").replace(":", "")
        joy = {"tepa_chap":  ("w*0.04", "h*0.035"),
               "tepa_ong":   ("w-tw-w*0.04", "h*0.035"),
               "past_chap":  ("w*0.04", "h-th-h*0.05"),
               "past_ong":   ("w-tw-w*0.04", "h-th-h*0.05")}
        x, y = joy.get(BRAND_JOY, joy["tepa_chap"])

        # Railway'dagi eski/yangi FFmpeg versiyalarida boxborderw uchun
        # h/140 kabi expression bir xil ishlamaydi. Shuning uchun video
        # balandligidan piksel qiymatlarini Python'da oldindan hisoblaymiz.
        _, video_h = _video_olchami(video_yol)
        brand_font_px = max(16, int(round(video_h / max(BRAND_OLCHAM, 1))))
        brand_box_px = max(1, int(round(video_h / 140)))

        filtr += (f",drawtext=fontfile='{brend_shrift}':text='{matn}'"
                  f":fontcolor=white@{BRAND_ORQA}:fontsize={brand_font_px}"
                  f":x={x}:y={y}"
                  f":box=1:boxcolor=black@{BRAND_QUTI}:boxborderw={brand_box_px}"
                  f":shadowcolor=black@0.5:shadowx=1:shadowy=1")

    def _ishga_tushir(vf):
        return subprocess.run(
            ["ffmpeg", "-hide_banner", "-i", video_yol, "-vf", vf,
             "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "copy", "-preset", "veryfast", "-movflags", "+faststart",
             "-y", chiqish_yol],
            capture_output=True, text=True, cwd=papka)

    r = _ishga_tushir(filtr)

    # Brend drawtext Railway FFmpeg build'ida ishlamasa ham subtitrning
    # o'zi to'xtab qolmasin: brendsiz qayta urinib ko'ramiz.
    if r.returncode != 0 and ",drawtext=" in filtr:
        log.warning("drawtext ishlamadi, brendsiz qayta urinish: %s",
                    r.stderr[-1500:])
        faqat_subtitr = filtr.split(",drawtext=", 1)[0]
        r = _ishga_tushir(faqat_subtitr)

    if r.returncode != 0:
        raise RuntimeError(f"Subtitr kuydirilmadi: {r.stderr[-1500:]}")


def _shrift_nomlari(yol):
    """TTF/OTF faylidan shrift OILA NOMINI o'qiydi ('name' jadvalidan).
    ffmpeg shriftni fayl nomi bilan emas, shu nom bilan topadi."""
    import struct
    try:
        with open(yol, "rb") as f:
            data = f.read()
        if len(data) < 12:
            return []
        jadval_soni = struct.unpack(">H", data[4:6])[0]
        nom_ofset = nom_uzunlik = None
        for i in range(jadval_soni):
            p = 12 + i * 16
            teg = data[p:p + 4]
            if teg == b"name":
                nom_ofset, nom_uzunlik = struct.unpack(">II", data[p + 8:p + 16])
                break
        if nom_ofset is None:
            return []
        n = data[nom_ofset:nom_ofset + nom_uzunlik]
        soni = struct.unpack(">H", n[2:4])[0]
        satr_ofset = struct.unpack(">H", n[4:6])[0]
        natija = []
        for i in range(soni):
            p = 6 + i * 12
            plat, enc, lang, nom_id, uzun, ofs = struct.unpack(">HHHHHH", n[p:p + 12])
            if nom_id not in (1, 4):          # 1 = oila, 4 = to'liq nom
                continue
            xom = n[satr_ofset + ofs: satr_ofset + ofs + uzun]
            try:
                matn = xom.decode("utf-16-be") if plat == 3 else xom.decode("latin-1")
            except Exception:
                continue
            matn = matn.strip()
            if matn and matn not in natija:
                natija.append(matn)
        return natija
    except Exception as e:
        log.warning("Shrift o'qilmadi (%s): %s", yol, e)
        return []


async def cmd_shriftlar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/shriftlar — fonts/ papkasidagi shriftlarning ANIQ nomlarini ko'rsatadi.
    SUBTITR_FONT ga aynan shu nom yozilishi kerak."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    if not os.path.isdir(FONTS_DIR):
        await update.message.reply_text(
            "fonts/ papkasi yo'q.\n\n"
            "Repoda 'fonts' papkasini ochib, .ttf faylni o'sha yerga qo'ying, "
            "keyin qayta deploy qiling.")
        return
    qatorlar = []
    for f in sorted(os.listdir(FONTS_DIR)):
        if not f.lower().endswith((".ttf", ".otf")):
            continue
        nomlar = _shrift_nomlari(os.path.join(FONTS_DIR, f))
        qatorlar.append(f"📄 {f}\n   → " + (" · ".join(nomlar[:3]) if nomlar
                                            else "nom o'qilmadi"))
    if not qatorlar:
        await update.message.reply_text("fonts/ papkasi bo'sh (.ttf topilmadi).")
        return
    await update.message.reply_text(
        "Topilgan shriftlar:\n\n" + "\n\n".join(qatorlar) +
        f"\n\nHozirgi uslub: {joriy_uslub()} — "
        f"{uslub_ol(joriy_uslub())['shrift']}\n"
        f"SUBTITR_FONT: {FONT_NAME or '(uslub belgilaydi)'}\n\n"
        "Uslubni almashtirish: /uslub\n"
        "Doimiy shrift: Railway Variables'da SUBTITR_FONT ga yuqoridagi "
        "nomlardan birini yozing.")


# ======================================================================
# USLUBNI ALMASHTIRISH — /uslub
# ======================================================================
# Uslubni tekshirish uchun har safar qayta deploy qilish shart emas:
# tanlov shu jarayon xotirasida saqlanadi. Qayta ishga tushganda
# SUBTITR_USLUB qiymatiga qaytadi.
_JORIY = {"uslub": USLUB if USLUB in USLUBLAR else "captions"}


def joriy_uslub():
    return _JORIY["uslub"]


def _uslub_tugmalari():
    qatorlar = []
    for nomi in USLUBLAR:
        belgi = "✅ " if nomi == joriy_uslub() else ""
        qatorlar.append([InlineKeyboardButton(
            f"{belgi}{nomi} — {USLUBLAR[nomi]['izoh']}"[:60],
            callback_data=f"suslub:{nomi}")])
    return InlineKeyboardMarkup(qatorlar)


def _uslub_matni():
    u = uslub_ol(joriy_uslub())
    return (f"🎨 Subtitr uslubi: <b>{joriy_uslub()}</b>\n"
            f"{u['izoh']}\n\n"
            f"Shrift: {u['shrift']}\n"
            f"Bir kartada: {u['maks_qator']} qator"
            + (f", {u['maks_soz']} so'zgacha" if u.get("maks_soz") else "")
            + f"\nPastdan masofa: {margin_asosi(joriy_uslub())}/288\n\n"
            "Quyidan tanlang — keyingi videoga shu uslub qo'llanadi.")


async def cmd_uslub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/uslub — subtitr uslubini ko'rish va almashtirish."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(_uslub_matni(), parse_mode="HTML",
                                    reply_markup=_uslub_tugmalari())


async def on_uslub_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Faqat admin uchun.", show_alert=True)
        return
    nomi = q.data.split(":", 1)[1]
    if nomi not in USLUBLAR:
        await q.answer("Bunday uslub yo'q.")
        return
    _JORIY["uslub"] = nomi
    await q.answer(f"Uslub: {nomi}")
    try:
        await q.edit_message_text(_uslub_matni(), parse_mode="HTML",
                                  reply_markup=_uslub_tugmalari())
    except Exception:
        pass


# ======================================================================
# OVOZLI VARIANT (dublyaj) — OpenAI TTS
# ======================================================================
TTS_MODEL = os.environ.get("SUBTITR_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE = os.environ.get("SUBTITR_TTS_VOICE", "onyx")
TTS_INSTR = os.environ.get(
    "SUBTITR_TTS_INSTR",
    "Speak in Uzbek with natural Uzbek pronunciation. "
    "Calm, clear, neutral narrator tone. Do not add an English accent.")
ASL_OVOZ = float(os.environ.get("SUBTITR_ASL_OVOZ", "0.18"))   # asl ovoz darajasi


def _tts_bytes(matn):
    """Bitta bo'lak uchun o'zbekcha ovoz (mp3 baytlari)."""
    kw = {"model": TTS_MODEL, "voice": TTS_VOICE, "input": matn[:1800],
          "response_format": "mp3"}
    if TTS_MODEL.startswith("gpt-"):        # yangi modellar yo'riqnoma qabul qiladi
        kw["instructions"] = TTS_INSTR
    r = ai().audio.speech.create(**kw)
    return r.content


def _audio_davomiylik(yol):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", yol],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def _ovoz_bolaklari(segmentlar, matnlar, papka):
    """Har segment uchun TTS yasaydi va uni segment vaqtiga moslaydi.
    O'zbekcha matn odatda uzunroq chiqadi — ovoz biroz tezlashtiriladi.
    Tezlik 0.75-1.6 oralig'ida cheklangan: undan tashqarida ovoz buziladi."""
    natija = []
    for i, ((b, o, _), m) in enumerate(zip(segmentlar, matnlar)):
        m = (m or "").strip()
        if not m:
            continue
        yol = os.path.join(papka, f"tts{i}.mp3")
        try:
            with open(yol, "wb") as f:
                f.write(_tts_bytes(m))
        except Exception as e:
            log.warning("TTS xatosi (%d): %s", i, e)
            continue
        d = _audio_davomiylik(yol)
        maqsad = max(float(o) - float(b), 0.6)
        if d > 0.1:
            tempo = max(0.75, min(d / maqsad, 1.6))
            if abs(tempo - 1.0) > 0.04:
                tez = os.path.join(papka, f"tez{i}.mp3")
                r = subprocess.run(
                    ["ffmpeg", "-i", yol, "-filter:a", f"atempo={tempo:.3f}",
                     "-y", tez], capture_output=True)
                if r.returncode == 0:
                    yol = tez
        natija.append((float(b), yol))
    return natija


def _dublyaj_qil(video_yol, bolaklar, chiqish_yol):
    """Asl ovozni pasaytirib, ustiga o'zbekcha ovozni qo'yadi."""
    if not bolaklar:
        raise RuntimeError("Ovoz bo'laklari yasalmadi")
    inp = ["-i", video_yol]
    for _, y in bolaklar:
        inp += ["-i", y]
    filt = [f"[0:a]volume={ASL_OVOZ}[orig]"]
    for i, (b, _) in enumerate(bolaklar, start=1):
        ms = int(max(b, 0) * 1000)
        filt.append(f"[{i}:a]adelay={ms}|{ms}[d{i}]")
    yorliq = "[orig]" + "".join(f"[d{i}]" for i in range(1, len(bolaklar) + 1))
    filt.append(f"{yorliq}amix=inputs={len(bolaklar) + 1}"
                f":duration=first:normalize=0[a]")
    r = subprocess.run(
        ["ffmpeg", *inp, "-filter_complex", ";".join(filt),
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
         "-y", chiqish_yol], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Dublyaj xatosi: {r.stderr[-300:]}")


MAQOLA_PROMPT = """Sen o'zbek Telegram kanalining muharririsan. Senga video \
nutqining o'zbekcha tarjimasi beriladi. Undan qisqa KANAL POSTI yoz.

QOIDALAR:
1. Sarlavha — qisqa, tasdiqlovchi gap (40-60 belgi). Emoji YO'Q. \
Videoning eng kuchli fikrini aks ettirsin.
2. 2-3 gap: nutqda nima aytilgani. Kim gapiryapti — agar matndan aniq \
bo'lsa, ismini yoz.
3. Oxirida bitta qator: "Nima qilish kerak:" — o'quvchi uchun amaliy xulosa. \
Agar aytadigan yangi gap bo'lmasa, bu qatorni umuman yozma.
4. Jonli, tabiiy o'zbek tili. Kitobiy iboralar taqiq: "ushbu", "mazkur", \
"hisoblanadi", "amalga oshirmoqda".
5. Matnda YO'Q narsani qo'shma. To'qima fakt, to'qima iqtibos TAQIQ.
6. Ismlar va kompaniya nomlari asl holicha (Mark Zuckerberg, Alphabet).

JAVOB — faqat post matni, izohsiz. Shu tuzilmada:

[Sarlavha]

[2-3 gap]

Nima qilish kerak: [bir gap]"""


def _maqola_yoz(tarjima_matni):
    """Tarjimadan kanal posti yasaydi."""
    r = ai().chat.completions.create(
        model=MODEL_SMART, max_completion_tokens=500,
        messages=[{"role": "system", "content": MAQOLA_PROMPT},
                  {"role": "user", "content": tarjima_matni[:6000]}])
    return (r.choices[0].message.content or "").strip()


def _post_matni(maqola, kanal):
    """Post oxiriga hashtag va kanal imzosini qo'shadi."""
    maqola = maqola.strip()
    if "#" not in maqola.split("\n")[-1]:
        maqola += f"\n\n#video · {kanal}"
    return maqola


# --- Qoralamalar: {id: {file_id, matn, kanal}} ---
_qoralama = {}
_kutilmoqda = {}          # {admin_id: (draft_id, "fikr" yoki "tahrir")}
_navbat = [0]


def _qoralama_tugmalari(qid):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Kanalga", callback_data=f"vpub:{qid}"),
        InlineKeyboardButton("✍️ Fikr", callback_data=f"vfikr:{qid}"),
    ], [
        InlineKeyboardButton("✏️ Tahrir", callback_data=f"vtah:{qid}"),
        InlineKeyboardButton("🔊 Ovozli", callback_data=f"vovoz:{qid}"),
    ], [
        InlineKeyboardButton("❌ Bekor", callback_data=f"vno:{qid}"),
    ]])


async def on_video_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    amal, qid = q.data.split(":", 1)
    d = _qoralama.get(qid)
    if not d:
        await q.answer("Qoralama topilmadi (bot qayta ishga tushgan).",
                       show_alert=True)
        return

    if amal == "vno":
        _qoralama.pop(qid, None)
        await q.answer("Bekor qilindi.")
        await q.edit_message_text("❌ BEKOR QILINDI")
        return

    if amal in ("vfikr", "vtah"):
        _kutilmoqda[q.from_user.id] = (qid, "fikr" if amal == "vfikr" else "tahrir")
        await q.answer()
        matn = ("✍️ Fikringizni yozing (2-3 jumla) — u post oxiriga qo'shiladi."
                if amal == "vfikr" else
                "✏️ Post matnini to'liq qayta yozib yuboring.")
        await context.bot.send_message(chat_id=q.from_user.id,
                                       text=matn + "\n\nBekor qilish: /bekor")
        return

    if amal == "vovoz":
        segs = d.get("segmentlar") or []
        trs = d.get("tarjimalar") or []
        if not segs or not trs:
            await q.answer("Segment ma'lumoti yo'q.", show_alert=True)
            return
        await q.answer("Ovoz tayyorlanmoqda...")
        holat = await context.bot.send_message(
            chat_id=q.from_user.id,
            text=f"🔊 O'zbekcha ovoz yasalmoqda ({len(segs)} bo'lak)...\n"
                 f"Bu bir necha daqiqa olishi mumkin.")
        ish = tempfile.mkdtemp(prefix="dub_")
        try:
            fayl = await context.bot.get_file(d["file_id"])
            video_yol = os.path.join(ish, "kirish.mp4")
            await fayl.download_to_drive(video_yol)

            bolaklar = await asyncio.to_thread(_ovoz_bolaklari, segs, trs, ish)
            if not bolaklar:
                await holat.edit_text("Ovoz yasalmadi — TTS javob bermadi.")
                return
            await holat.edit_text(
                f"🎚 Ovoz aralashtirilmoqda ({len(bolaklar)} bo'lak)...")
            chiqish = os.path.join(ish, "ovozli.mp4")
            await asyncio.to_thread(_dublyaj_qil, video_yol, bolaklar, chiqish)

            with open(chiqish, "rb") as f:
                await context.bot.send_video(
                    chat_id=q.from_user.id, video=f,
                    caption="O'zbekcha ovoz bilan (asl ovoz pastda)")
            await holat.delete()
        except Exception as e:
            log.exception("Dublyaj xatosi")
            try:
                await holat.edit_text(f"Xato: {e}")
            except Exception:
                pass
        finally:
            shutil.rmtree(ish, ignore_errors=True)
        return

    if amal == "vpub":
        kanal = d["kanal"]
        try:
            await context.bot.send_video(
                chat_id=kanal, video=d["file_id"],
                caption=_post_matni(d["matn"], kanal)[:1024])
            _qoralama.pop(qid, None)
            await q.answer("Kanalga chiqdi ✅")
            await q.edit_message_text(f"✅ {kanal} GA CHIQDI\n\n{d['matn']}")
        except Exception as e:
            await q.answer(f"Xato: {e}", show_alert=True)


async def on_qoralama_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fikr yoki tahrir matnini qabul qiladi."""
    uid = update.effective_user.id if update.effective_user else None
    holat = _kutilmoqda.get(uid)
    if not holat:
        return                       # bizga tegishli emas — o'tib ketsin
    qid, turi = holat
    d = _qoralama.get(qid)
    matn = (update.message.text or "").strip()
    if not matn:
        return
    _kutilmoqda.pop(uid, None)
    if not d:
        await update.message.reply_text("Qoralama topilmadi.")
        raise ApplicationHandlerStop

    if turi == "tahrir":
        d["matn"] = matn
    else:
        qoshimcha = matn if matn.endswith("?") else matn + "\n\nSiz nima deb o'ylaysiz?"
        d["matn"] = d["matn"].rstrip() + "\n\n" + qoshimcha
    await update.message.reply_text(
        f"Yangilandi:\n\n{d['matn']}", reply_markup=_qoralama_tugmalari(qid))
    raise ApplicationHandlerStop


async def cmd_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user and _kutilmoqda.pop(update.effective_user.id, None):
        await update.message.reply_text("Bekor qilindi.")


# ======================================================================
# ASOSIY ISHLOVCHI
# ======================================================================
async def on_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    v = msg.video or msg.document
    if v is None:
        return
    if not ffmpeg_bor():
        await msg.reply_text(
            "ffmpeg topilmadi — server sozlanmagan.\n"
            "Repoga nixpacks.toml qo'shilishi kerak.")
        return

    holat = await msg.reply_text("🎬 Video olinmoqda...")
    ish = tempfile.mkdtemp(prefix="sub_")
    try:
        try:
            fayl = await context.bot.get_file(v.file_id)
        except Exception as e:
            await holat.edit_text(
                f"Faylni olib bo'lmadi: {e}\n\n"
                f"Telegram botlari 20 MB dan katta faylni yuklay olmaydi.")
            return
        video_yol = os.path.join(ish, "kirish.mp4")
        await fayl.download_to_drive(video_yol)

        async def holat_yoz(matn):
            try:
                await holat.edit_text(matn)
            except Exception:
                pass

        uzunlik = await asyncio.to_thread(_davomiylik, video_yol)
        if uzunlik > MAX_SECONDS:
            await holat.edit_text(
                f"Video juda uzun: {int(uzunlik // 60)} daqiqa "
                f"(chegara {MAX_SECONDS // 60} daqiqa).")
            return

        await holat_yoz("🎧 Ovoz ajratilmoqda...")
        ovoz_yol = os.path.join(ish, "ovoz.mp3")
        await asyncio.to_thread(_ovoz_ajrat, video_yol, ovoz_yol)

        if uzunlik > STT_BOLAK_SEK:
            await holat_yoz(
                f"📝 Nutq matnga o'girilmoqda "
                f"({int(uzunlik // 60)} daqiqa — biroz vaqt oladi)...")
        else:
            await holat_yoz("📝 Nutq matnga o'girilmoqda...")
        segmentlar, til = await asyncio.to_thread(
            _transkripsiya, ovoz_yol, uzunlik)
        if not segmentlar:
            await holat.edit_text("Nutq topilmadi — videoda ovoz bormi?")
            return

        await holat_yoz(
            f"🌐 Tarjima qilinmoqda ({len(segmentlar)} segment, manba: {til})...")
        loop = asyncio.get_running_loop()

        def tarjima_belgisi(k, jami):
            if jami > 1:
                asyncio.run_coroutine_threadsafe(
                    holat_yoz(f"🌐 Tarjima qilinmoqda... {k}/{jami}"), loop)

        uz = await asyncio.to_thread(_tarjima, segmentlar, tarjima_belgisi)

        en0, bal0 = await asyncio.to_thread(_video_olchami, video_yol)
        uslub_nomi = joriy_uslub()
        fs, maks_en, yon = format_sozlamasi(en0, bal0, uslub_nomi)
        bolaklar = vaqtga_taqsimla(segmentlar, uz, uslub_ol(uslub_nomi),
                                   fs, maks_en)
        srt = srt_yasa(bolaklar)
        srt_yol = os.path.join(ish, "subtitr.srt")
        with open(srt_yol, "w", encoding="utf-8") as f:
            f.write(srt)

        await holat_yoz("🎞 Subtitr videoga kuydirilmoqda...")
        chiqish = os.path.join(ish, "natija.mp4")

        # Format va joylashuvni videoning o'ziga moslashtirmiz
        band, eng_yuqori = await asyncio.to_thread(
            mavjud_subtitr_bormi, video_yol, uzunlik)
        marginv = margin_asosi(uslub_nomi)
        izoh = ""
        if band >= 0.5:      # videoda allaqachon subtitr bor — tepasiga chiqamiz
            marginv = margin_hisobla(eng_yuqori, uslub_nomi)
            izoh = "\n\n⚠️ Videoda allaqachon subtitr bor — matn tepasiga qo'yildi."
        await asyncio.to_thread(_kuydir, video_yol, srt_yol, chiqish,
                                fs, marginv, uslub_nomi, yon)

        await holat.edit_text("📤 Yuborilmoqda...")
        with open(chiqish, "rb") as f:
            yuborilgan = await msg.reply_video(
                video=f, caption="O'zbekcha subtitr bilan")
        with open(srt_yol, "rb") as f:
            await msg.reply_document(document=f, filename="subtitr.srt",
                                     caption="Montaj uchun subtitr fayli")

        toliq = " ".join(uz)
        await holat_yoz("📰 Kanal posti tayyorlanmoqda...")
        try:
            maqola = await asyncio.to_thread(_maqola_yoz, toliq)
        except Exception as e:
            log.warning("Maqola yozilmadi: %s", e)
            maqola = ""

        file_id = None
        if yuborilgan and yuborilgan.video:
            file_id = yuborilgan.video.file_id

        if maqola and file_id:
            _navbat[0] += 1
            qid = str(_navbat[0])
            _qoralama[qid] = {"file_id": file_id, "matn": maqola, "kanal": KANAL,
                              "segmentlar": segmentlar, "tarjimalar": uz}
            await msg.reply_text(
                f"📰 KANAL POSTI ({KANAL})\n\n{maqola}{izoh}",
                reply_markup=_qoralama_tugmalari(qid))
        else:
            await msg.reply_text("📄 To'liq tarjima:\n\n" + toliq[:3800])
        await holat.delete()

    except Exception as e:
        log.exception("Subtitr xatosi")
        try:
            await holat.edit_text(f"Xato: {e}")
        except Exception:
            pass
    finally:
        shutil.rmtree(ish, ignore_errors=True)


def register(app: Application):
    """bot.py dan: subtitr.register(app)"""
    if not ADMIN_ID:
        log.warning("ADMIN_ID yo'q — subtitr moduli o'chirilgan.")
        return
    app.add_handler(MessageHandler(
        (filters.VIDEO | filters.Document.VIDEO) & filters.User(user_id=ADMIN_ID),
        on_video))
    app.add_handler(CallbackQueryHandler(
        on_video_tugma, pattern=r"^(vpub|vfikr|vtah|vno|vovoz):"))
    app.add_handler(CallbackQueryHandler(on_uslub_tugma, pattern=r"^suslub:"))
    app.add_handler(CommandHandler("uslub", cmd_uslub))
    app.add_handler(CommandHandler("bekor", cmd_bekor), group=-2)
    app.add_handler(CommandHandler("shriftlar", cmd_shriftlar))
    # group=-2 — agent.py dagi matn ishlovchisidan (group=-1) OLDIN ishlaydi.
    # Kutilmayotgan paytda hech narsaga aralashmaydi.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        on_qoralama_matn), group=-2)
    log.info("Subtitr moduli yoqildi (ffmpeg: %s)",
             "bor" if ffmpeg_bor() else "YO'Q")
