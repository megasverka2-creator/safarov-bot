# -*- coding: utf-8 -*-
"""
SUBTITR MODULI — video uchun o'zbekcha subtitr  (faqat ADMIN uchun)
===================================================================
Ishlash tartibi:
  1. Admin botga video tashlaydi
  2. ffmpeg videodan ovozni ajratadi (kichik mono mp3)
  3. Whisper (whisper-1) matnga o'giradi — VAQT BELGILARI bilan
     (diqqat: gpt-4o transkripsiya modellari vaqt belgisi bermaydi)
  4. AI segmentlarni o'zbekchaga o'giradi — bitta so'rovda, kontekst saqlanadi
  5. .srt yasaladi va videoga kuyiladi
  6. Admin oladi: subtitrli video + .srt fayl + to'liq tarjima matni

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

try:  # Pillow — mavjud subtitrni aniqlash uchun
    from PIL import Image
except Exception:
    Image = None

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
MODEL_SMART = os.environ.get("AI_MODEL_SMART", "gpt-5.6-terra")
STT_MODEL = os.environ.get("AI_MODEL_STT", "whisper-1")   # vaqt belgisi beradi

MAX_SECONDS = int(os.environ.get("SUBTITR_MAX_SEC", "300"))  # 5 daqiqa
# Bo'sh qoldirilsa — video formatiga qarab AVTOMATIK tanlanadi.
# Qiymat berilsa — o'sha ustuvor (shrift almashganda qo'l bilan sozlash uchun).
_LINE_ENV = os.environ.get("SUBTITR_LINE", "").strip()
_FS_ENV = os.environ.get("SUBTITR_FONT_SIZE", "").strip()
MAX_LINE = int(_LINE_ENV) if _LINE_ENV.isdigit() else 24
FONT_SIZE = int(_FS_ENV) if _FS_ENV.isdigit() else 12
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
BRAND = os.environ.get("SUBTITR_BRAND", "@safaroov_blog")   # videodagi yozuv
BRAND_OLCHAM = int(os.environ.get("SUBTITR_BRAND_OLCHAM", "28"))  # h/28 — kichikroq son = kattaroq yozuv
BRAND_ORQA = os.environ.get("SUBTITR_BRAND_ORQA", "0.92")         # matn shaffofligi
BRAND_QUTI = os.environ.get("SUBTITR_BRAND_QUTI", "0.35")         # orqa quti (0 = quti yo'q)
BRAND_JOY = os.environ.get("SUBTITR_BRAND_JOY", "tepa_chap")      # tepa_chap/tepa_ong/past_chap/past_ong
KANAL = os.environ.get("CHANNEL_ID", "@safaroov_blog")      # qaysi kanalga
FONT_NAME = os.environ.get("SUBTITR_FONT", "Liberation Sans")

_FONT_YOLLARI = [
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


def _satrlarga_bol(matn, eni=MAX_LINE):
    """Uzun matnni ko'pi bilan 2 qatorga bo'ladi — subtitr o'qishli bo'lsin.
    So'z o'rtasidan kesilmaydi: sig'masa, matn so'z chegarasida qisqartiriladi."""
    matn = " ".join(matn.split())
    if len(matn) <= eni:
        return matn
    # bo'shliqsiz juda uzun bo'lak (havola va h.k.) — majburan bo'lamiz
    sozlar = []
    for s in matn.split(" "):
        while len(s) > eni:
            sozlar.append(s[:eni - 1] + "-")
            s = s[eni - 1:]
        sozlar.append(s)
    qator, natija = "", []
    for s in sozlar:
        nomzod = (qator + " " + s).strip()
        if len(nomzod) <= eni:
            qator = nomzod
        elif qator:              # joriy qator to'ldi — yangisiga o'tamiz
            natija.append(qator)
            qator = s
        else:                    # qator bo'sh, lekin so'z baribir sig'maydi
            natija.append(s)
            qator = ""
    if qator:
        natija.append(qator)
    if len(natija) <= 2:
        return "\n".join(natija)
    # 2 qatordan oshsa — ikkinchi qatorni so'z chegarasida to'xtatamiz
    ikki = natija[1]
    for s in natija[2:]:
        if len(ikki) + len(s) + 1 <= eni - 1:
            ikki += " " + s
        else:
            ikki += "…"
            break
    return natija[0] + "\n" + ikki


def _bolaklarga(matn, eni):
    """Matnni qisqa bo'laklarga bo'ladi (so'z chegarasida)."""
    matn = " ".join(matn.split())
    if not matn:
        return []
    if len(matn) <= eni:
        return [matn]
    natija, joriy = [], ""
    for s in matn.split(" "):
        while len(s) > eni:                    # bo'shliqsiz uzun bo'lak
            if joriy:
                natija.append(joriy)
                joriy = ""
            natija.append(s[:eni - 1] + "-")
            s = s[eni - 1:]
        nomzod = (joriy + " " + s).strip()
        if len(nomzod) <= eni:
            joriy = nomzod
        else:
            if joriy:
                natija.append(joriy)
            joriy = s
    if joriy:
        natija.append(joriy)
    return natija


def vaqtga_taqsimla(segmentlar, tarjimalar, eni=None):
    """Har segmentni qisqa bo'laklarga bo'lib, vaqtini proporsional taqsimlaydi.
    Natija: professional subtitr kabi — ekranda bir vaqtda BITTA qisqa qator.
    Uzun segment ekranni to'ldirib, videoni yopib qo'ymaydi."""
    eni = eni or MAX_LINE
    natija = []
    for (b, o, _), matn in zip(segmentlar, tarjimalar):
        bolaklar = _bolaklarga(matn, eni)
        if not bolaklar:
            continue
        davom = max(float(o) - float(b), 0.8)
        jami = sum(len(x) for x in bolaklar) or 1
        t = float(b)
        for i, bo in enumerate(bolaklar):
            ulush = davom * (len(bo) / jami)
            oxiri = float(o) if i == len(bolaklar) - 1 else t + ulush
            natija.append((t, oxiri, bo))
            t += ulush
    return natija


def srt_yasa(segmentlar):
    """[(bosh, oxir, matn), ...] -> .srt matni"""
    qismlar = []
    for i, (b, o, m) in enumerate(segmentlar, 1):
        if o <= b:
            o = b + 1.2
        qismlar.append(f"{i}\n{_vaqt(b)} --> {_vaqt(o)}\n{m.strip()}\n")
    return "\n".join(qismlar)


# ======================================================================
# USLUB TO'PLAMLARI
# ======================================================================
# Har uslub: ASS force_style bo'lagi. FontSize va MarginV kod tomonidan
# qo'shiladi (video formatiga va mavjud subtitrga qarab).
USLUBLAR = {
    "klassik": ("Oq qalin, ingichka kontur — universal",
                "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=0.8,Shadow=1.2,Bold=1,Spacing=0.2"),
    "qutili": ("Yarim shaffof qora qutida — har qanday fonda o'qiladi",
               "PrimaryColour=&HFFFFFF,BackColour=&HA0000000,"
               "BorderStyle=3,Outline=0.6,Shadow=0,Bold=1,Spacing=0.2"),
    "kontrast": ("Qalin qora kontur — sershovqin videolar uchun",
                 "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                 "BorderStyle=1,Outline=2.2,Shadow=0,Bold=1,Spacing=0.1"),
    "oltin": ("Sariq-oltin urg'u — reels uslubi",
              "PrimaryColour=&H4FD7FF,OutlineColour=&H000000,"
              "BorderStyle=1,Outline=1.4,Shadow=0.8,Bold=1,Spacing=0.2"),
    "yumshoq": ("Konturisiz, faqat soya — tinch videolar uchun",
                "PrimaryColour=&HFFFFFF,OutlineColour=&H000000,"
                "BorderStyle=1,Outline=0,Shadow=2,Bold=1,Spacing=0.3"),
}
USLUB = os.environ.get("SUBTITR_USLUB", "klassik")
MARGIN_ODDIY = int(os.environ.get("SUBTITR_MARGIN", "70"))    # pastdan masofa
MARGIN_YUQORI = int(os.environ.get("SUBTITR_MARGIN2", "150"))  # mavjud subtitr bo'lsa


def format_sozlamasi(en, balandlik):
    """Video nisbatiga qarab shrift o'lchami va qator enini tanlaydi.
    O'lchovlar amaliy sinovdan olingan (matn eni 60-85% bo'lishi maqsad).
    Env orqali qiymat berilgan bo'lsa — O'SHA ustuvor."""
    if _FS_ENV.isdigit() and _LINE_ENV.isdigit():
        return FONT_SIZE, MAX_LINE
    if balandlik <= 0:
        return FONT_SIZE, MAX_LINE
    nisbat = en / balandlik
    if nisbat < 0.70:            # 9:16 — Reels, TikTok, Shorts
        return (FONT_SIZE if _FS_ENV.isdigit() else 12,
                MAX_LINE if _LINE_ENV.isdigit() else 24)
    if nisbat < 0.95:            # 4:5 — Instagram
        return 13, 27
    if nisbat < 1.30:            # 1:1 — kvadrat
        return 14, 30
    return 17, 36                # 16:9 — YouTube, gorizontal


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


def margin_hisobla(eng_yuqori):
    """Mavjud subtitr tepasiga bizning matnni joylash uchun MarginV.
    ASS o'lchovi 288 birlik balandlikka nisbatan hisoblanadi."""
    pastdan = (1.0 - eng_yuqori) * 288       # mavjud matn qayerdan boshlanadi
    kerak = int(pastdan + 26)                # + o'z matnimiz balandligi va bo'shliq
    return max(MARGIN_ODDIY, min(kerak, 100))
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


def _transkripsiya(ovoz_yol):
    """Whisper — segment darajasidagi vaqt belgilari bilan."""
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
            natija.append((float(b or 0), float(o or 0), t))
    til = getattr(r, "language", "") or ""
    return natija, til


def _tarjima(segmentlar):
    """Hamma segmentni BITTA so'rovda o'giradi — arzon va kontekst saqlanadi."""
    kirish = "\n".join(f"[{i}] {t}" for i, (_, _, t) in enumerate(segmentlar, 1))
    r = ai().chat.completions.create(
        model=MODEL_SMART,
        response_format={"type": "json_object"},
        max_completion_tokens=120 * len(segmentlar) + 400,
        messages=[{"role": "system", "content": TARJIMA_PROMPT},
                  {"role": "user", "content": kirish}])
    data = json.loads(r.choices[0].message.content)
    xarita = {}
    for el in (data.get("lines") or []):
        try:
            xarita[int(el.get("n"))] = (el.get("uz") or "").strip()
        except (TypeError, ValueError):
            continue
    # tushib qolgan segment bo'lsa — asl matn qoladi (bo'sh qolmasin)
    return [xarita.get(i) or segmentlar[i - 1][2]
            for i in range(1, len(segmentlar) + 1)]


def _kuydir(video_yol, srt_yol, chiqish_yol, fs=None, marginv=None,
            uslub_nomi=None):
    """Subtitrni videoga kuydiradi.
    fs        — shrift o'lchami (video formatiga qarab tanlanadi)
    marginv   — pastdan masofa (mavjud subtitr bo'lsa oshiriladi)
    uslub_nomi— USLUBLAR dan biri

    DIQQAT: libass shriftni video o'lchamiga O'ZI masshtablaydi (384px etalon).
    Shuning uchun fs video eniga qarab kattalashtirilmaydi."""
    fs = fs or FONT_SIZE
    marginv = marginv if marginv is not None else 70
    _, uslub_qismi = USLUBLAR.get(uslub_nomi or USLUB, USLUBLAR["klassik"])
    uslub = (f"FontName={FONT_NAME},FontSize={fs},{uslub_qismi},"
             f"Alignment=2,MarginV={marginv},MarginL=20,MarginR=20")

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
        f"\n\nHozirgi SUBTITR_FONT: {FONT_NAME}\n"
        "Railway Variables'da SUBTITR_FONT ga yuqoridagi nomlardan birini yozing.")


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

        uzunlik = await asyncio.to_thread(_davomiylik, video_yol)
        if uzunlik > MAX_SECONDS:
            await holat.edit_text(
                f"Video juda uzun: {int(uzunlik)} soniya "
                f"(chegara {MAX_SECONDS}).")
            return

        await holat.edit_text("🎧 Ovoz ajratilmoqda...")
        ovoz_yol = os.path.join(ish, "ovoz.mp3")
        await asyncio.to_thread(_ovoz_ajrat, video_yol, ovoz_yol)

        await holat.edit_text("📝 Nutq matnga o'girilmoqda...")
        segmentlar, til = await asyncio.to_thread(_transkripsiya, ovoz_yol)
        if not segmentlar:
            await holat.edit_text("Nutq topilmadi — videoda ovoz bormi?")
            return

        await holat.edit_text(
            f"🌐 Tarjima qilinmoqda ({len(segmentlar)} segment, manba: {til})...")
        uz = await asyncio.to_thread(_tarjima, segmentlar)

        en0, bal0 = await asyncio.to_thread(_video_olchami, video_yol)
        _, qator_eni = format_sozlamasi(en0, bal0)
        bolaklar = vaqtga_taqsimla(segmentlar, uz, qator_eni)
        srt = srt_yasa(bolaklar)
        srt_yol = os.path.join(ish, "subtitr.srt")
        with open(srt_yol, "w", encoding="utf-8") as f:
            f.write(srt)

        await holat.edit_text("🎞 Subtitr videoga kuydirilmoqda...")
        chiqish = os.path.join(ish, "natija.mp4")

        # Format va joylashuvni videoning o'ziga moslashtirmiz
        en, bal = await asyncio.to_thread(_video_olchami, video_yol)
        fs, _ = format_sozlamasi(en, bal)
        band, eng_yuqori = await asyncio.to_thread(
            mavjud_subtitr_bormi, video_yol, uzunlik)
        marginv = MARGIN_ODDIY
        izoh = ""
        if band >= 0.5:      # videoda allaqachon subtitr bor — tepasiga chiqamiz
            marginv = margin_hisobla(eng_yuqori)
            izoh = "\n\n⚠️ Videoda allaqachon subtitr bor — matn tepasiga qo'yildi."
        await asyncio.to_thread(_kuydir, video_yol, srt_yol, chiqish,
                                fs, marginv, USLUB)

        await holat.edit_text("📤 Yuborilmoqda...")
        with open(chiqish, "rb") as f:
            yuborilgan = await msg.reply_video(
                video=f, caption="O'zbekcha subtitr bilan")
        with open(srt_yol, "rb") as f:
            await msg.reply_document(document=f, filename="subtitr.srt",
                                     caption="Montaj uchun subtitr fayli")

        toliq = " ".join(uz)
        await holat.edit_text("📰 Kanal posti tayyorlanmoqda...")
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
    app.add_handler(CommandHandler("bekor", cmd_bekor), group=-2)
    app.add_handler(CommandHandler("shriftlar", cmd_shriftlar))
    # group=-2 — agent.py dagi matn ishlovchisidan (group=-1) OLDIN ishlaydi.
    # Kutilmayotgan paytda hech narsaga aralashmaydi.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        on_qoralama_matn), group=-2)
    log.info("Subtitr moduli yoqildi (ffmpeg: %s)",
             "bor" if ffmpeg_bor() else "YO'Q")
