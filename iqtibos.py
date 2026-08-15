# -*- coding: utf-8 -*-
"""
IQTIBOS KARTALARI MODULI  (@safarovblog_bot)
============================================
Kitobdan olingan iqtibosni 3 xil uslubda chiroyli kartaga aylantiradi
va kanalga joylaydi. Faqat ADMIN uchun.

ISHLATISH:
    /iqtibos
    Iqtibos matni, *urg'u beriladigan joy* yulduzcha ichida.
    — Muallif ismi, "Kitob nomi"

OQIM:
  1. Bot 3 uslubni ham chizadi (Pillow, xarajat $0) va albom qilib yuboradi
  2. Siz 1 / 2 / 3 dan birini tanlaysiz
  3. Xohlasangiz "AI rasm" bosasiz — GPT Image o'sha uslubga mos
     illustratsiya chizadi va kartaga qo'shiladi (~0.5 sent)
  4. "Kanalga" bosilsa — post chiqadi

MUHIM QOIDALAR:
  • MUALLIF ISMINI AI QIDIRMAYDI. Siz kiritasiz, xolos.
    Sabab: "iqtibos to'qilmaydi" kelishuvi. AI muallifni ishonch bilan
    xato aytishi mumkin, bu esa kanal obro'siga eng katta zarar.
  • AI faqat ILLUSTRATSIYA chizadi — matn, ism, raqam yozmaydi.
  • Rasmda odam yuzi, mashhur shaxs, diniy timsol chizilmaydi.
"""

import asyncio
import base64
import io
import logging
import os
import random
import re
import time

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      InputMediaPhoto)
from telegram.ext import (Application, CommandHandler,
                          CallbackQueryHandler, MessageHandler,
                          ContextTypes, filters)

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import kirill   # kirill -> lotin o'giruvchi (AI emas, qat'iy jadval)

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
CHANNEL_ID = os.environ.get("IQTIBOS_CHANNEL",
                            os.environ.get("CHANNEL_ID", "@safaroov_blog"))
BRAND = os.environ.get("IQTIBOS_BRAND", CHANNEL_ID)
EGA_NOMI = os.environ.get("IQTIBOS_EGA", "Safarov")

MODEL_IMAGE = os.environ.get("AI_MODEL_IMAGE", "gpt-image-2")
MODEL_FAST = os.environ.get("AI_MODEL_FAST", "gpt-5.4-nano")
# Low sifat yetarli — bizga chiziqli chizma kerak, fotorealizm emas.
# Low ~$0.005, Medium ~$0.04, High ~$0.165 bitta rasm uchun.
IMAGE_QUALITY = os.environ.get("IQTIBOS_IMAGE_QUALITY", "low")

MAX_BELGI = int(os.environ.get("IQTIBOS_MAX", "320"))
# rasmdan o'qishda ishlatiladigan ko'ruvchi model
MODEL_VISION = os.environ.get("AI_MODEL_VISION",
                              os.environ.get("AI_MODEL_SMART",
                                             "gpt-5.6-terra"))

W = H = 1080

# ======================================================================
# SHRIFTLAR
# ======================================================================
_QIDIRUV = [
    "fonts", "/usr/share/fonts/truetype/google-fonts",
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
]


def _shrift_yoli(*nomlar):
    for papka in _QIDIRUV:
        for nom in nomlar:
            yol = os.path.join(papka, nom)
            if os.path.exists(yol):
                return yol
    return None


def fnt(tur, size):
    """tur: serif / serif_i / sans / sans_b / sans_l"""
    jadval = {
        "serif":   ("Lora-Variable.ttf", "Lora-Regular.ttf",
                    "DejaVuSerif.ttf", "LiberationSerif-Regular.ttf"),
        "serif_i": ("Lora-Italic-Variable.ttf", "Lora-Italic.ttf",
                    "DejaVuSerif-Italic.ttf", "LiberationSerif-Italic.ttf"),
        "sans":    ("Poppins-Regular.ttf", "DejaVuSans.ttf",
                    "LiberationSans-Regular.ttf"),
        "sans_m":  ("Poppins-Medium.ttf", "DejaVuSans.ttf",
                    "LiberationSans-Regular.ttf"),
        "sans_b":  ("Poppins-Bold.ttf", "DejaVuSans-Bold.ttf",
                    "LiberationSans-Bold.ttf"),
        "sans_l":  ("Poppins-Light.ttf", "DejaVuSans-ExtraLight.ttf",
                    "DejaVuSans.ttf"),
    }
    yol = _shrift_yoli(*jadval.get(tur, jadval["sans"]))
    if yol:
        return ImageFont.truetype(yol, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# ======================================================================
# MATN JOYLASH
# ======================================================================
def _joyla(d, matn, font, maxw):
    """Matnni so'zlarga bo'lib qatorlarga taqsimlaydi."""
    bosh = d.textlength(" ", font=font)
    qatorlar, joriy, x = [], [], 0.0
    for soz in matn.split():
        w = d.textlength(soz, font=font)
        if joriy and x + w > maxw:
            qatorlar.append(joriy)
            joriy, x = [], 0.0
        joriy.append((soz, x, w))
        x += w + bosh
    if joriy:
        qatorlar.append(joriy)
    return qatorlar


def _joyla_aylanma(d, matn, font, keng, tor, y0, bal, chegara_y):
    """Matnni joylaydi, lekin chegara_y dan pastga tushgan qatorlar
    TORROQ bo'ladi — o'ng tomondagi chizmaga joy qoladi.
    Jurnallardagi "matn rasmni aylanib o'tishi" shu."""
    bosh = d.textlength(" ", font=font)
    qatorlar, joriy, x = [], [], 0.0
    y = y0

    def maxw():
        return tor if (y + font.size) > chegara_y else keng

    for soz in matn.split():
        w = d.textlength(soz, font=font)
        if joriy and x + w > maxw():
            qatorlar.append(joriy)
            joriy, x = [], 0.0
            y += bal
        joriy.append((soz, x, w))
        x += w + bosh
    if joriy:
        qatorlar.append(joriy)
    return qatorlar


def _urgu_indeks(matn, urgu):
    """Urg'ulanadigan so'zlarning tartib raqamlari."""
    if not urgu:
        return set()
    tozala = lambda s: s.strip(".,!?;:«»“”—-")
    sozlar = [tozala(s) for s in matn.split()]
    u = [tozala(s) for s in urgu.split()]
    for i in range(len(sozlar) - len(u) + 1):
        if sozlar[i:i + len(u)] == u:
            return set(range(i, i + len(u)))
    return set()


def _chiz(d, qatorlar, x0, y0, font, rang, bal, urgu_idx=None,
          urgu_rang=None, markaz=None):
    urgu_idx = urgu_idx or set()
    n, y = 0, y0
    for qator in qatorlar:
        siljish = 0
        if markaz:
            oxiri = qator[-1][1] + qator[-1][2]
            siljish = (markaz - oxiri) / 2
        if urgu_rang:
            bolak = [(x0 + x + siljish, w)
                     for i, (s, x, w) in enumerate(qator) if n + i in urgu_idx]
            if bolak:
                a = bolak[0][0]
                b = bolak[-1][0] + bolak[-1][1]
                d.rounded_rectangle([a - 8, y + font.size * 0.20,
                                     b + 8, y + font.size * 1.10],
                                    radius=8, fill=urgu_rang)
        for soz, x, w in qator:
            d.text((x0 + x + siljish, y), soz, font=font, fill=rang)
            n += 1
        y += bal
    return y


def _sig(d, matn, tur, keng, maxh, olchamlar):
    """Berilgan balandlikka SIG'ADIGAN eng katta shriftni tanlaydi.
    Qat'iy o'lcham ishlatilsa uzun matn ost yozuv ustiga chiqib ketardi —
    shuning uchun shrift matnga qarab moslashadi."""
    oxirgi = None
    for o in olchamlar:
        f = fnt(tur, o)
        q = _joyla(d, matn, f, keng)
        bal = int(o * 1.45 if tur.startswith("sans") else o * 1.48)
        oxirgi = (f, q, bal)
        if len(q) * bal <= maxh:
            return oxirgi
    return oxirgi          # eng kichigi ham sig'masa — shuni beramiz


# ======================================================================
# YORDAMCHI BELGILAR (1-uslub uchun)
# ======================================================================
def _belgilar(d, x, y, rang):
    d.ellipse([x, y + 4, x + 15, y + 19], outline=rang, width=3)
    d.ellipse([x + 13, y + 4, x + 28, y + 19], outline=rang, width=3)
    d.polygon([(x + 1, y + 13), (x + 14, y + 30), (x + 27, y + 13)], fill=rang)
    d.polygon([(x + 3, y + 12), (x + 14, y + 26), (x + 25, y + 12)],
              fill=(255, 255, 255))
    d.ellipse([x + 62, y + 2, x + 92, y + 28], outline=rang, width=3)
    d.polygon([(x + 70, y + 26), (x + 70, y + 36), (x + 80, y + 27)], fill=rang)
    d.polygon([(x + 124, y + 15), (x + 156, y + 2), (x + 143, y + 32)],
              outline=rang, width=3)
    d.line([(x + 190, y + 2), (x + 190, y + 32), (x + 203, y + 21),
            (x + 216, y + 32), (x + 216, y + 2), (x + 190, y + 2)],
           fill=rang, width=3)


# ======================================================================
# AI RASMNI TAYYORLASH
# ======================================================================
def oq_shaffof(img, ostona=238):
    """Oq fonni shaffofga aylantiradi (chiziqli chizma uchun).
    API'dan shaffof fon SO'RALMAYDI — parametrga bog'liq bo'lmaslik uchun
    shu yerda o'zimiz qilamiz."""
    img = img.convert("RGBA")
    px = img.getdata()
    yangi = []
    for r, g, b, a in px:
        if r >= ostona and g >= ostona and b >= ostona:
            yangi.append((r, g, b, 0))
        else:
            # kulrang joylar yarim shaffof — chekkalar yumshoq bo'ladi
            yorqin = (r + g + b) / 3
            alpha = int(max(0, min(255, (ostona - yorqin) * 255 / ostona)))
            yangi.append((r, g, b, max(alpha, a if a < 255 else alpha)))
    img.putdata(yangi)
    return img


def _rangla(img, rang):
    """Chizmani bitta rangga bo'yaydi (alfa saqlanadi)."""
    img = img.convert("RGBA")
    alfa = img.split()[3]
    boyoq = Image.new("RGBA", img.size, rang + (255,))
    boyoq.putalpha(alfa)
    return boyoq


# ======================================================================
# USLUB 1 — IJTIMOIY KARTA
# ======================================================================
def karta_ijtimoiy(matn, muallif, kitob, urgu=None, rasm=None):
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([90, 150, 190, 250], fill=(236, 232, 245))
    d.text((140, 200), EGA_NOMI[:1].upper(), font=fnt("sans_b", 44),
           fill=(90, 70, 140), anchor="mm")
    d.text((210, 158), EGA_NOMI, font=fnt("sans_b", 46), fill=(17, 17, 17))
    kx = 210 + d.textlength(EGA_NOMI, font=fnt("sans_b", 46)) + 14
    d.ellipse([kx, 168, kx + 34, 202], fill=(29, 155, 240))
    d.line([(kx + 8, 185), (kx + 15, 193), (kx + 27, 176)],
           fill="white", width=4)
    d.text((212, 212), BRAND, font=fnt("sans", 30), fill=(120, 120, 128))

    # AI chizmasi — pastki o'ng burchakda, matn uni aylanib o'tadi
    RASM_OLCHAM, RASM_YUQORI = 360, 520
    if rasm is not None:
        ch = oq_shaffof(rasm).resize((RASM_OLCHAM, RASM_OLCHAM), Image.LANCZOS)
        ch = _rangla(ch, (152, 152, 160))
        ch.putalpha(ch.split()[3].point(lambda a: int(a * 0.8)))
        img.paste(ch, (W - 110 - RASM_OLCHAM, RASM_YUQORI), ch)
        d = ImageDraw.Draw(img)

    OLCHAMLAR = (54, 50, 46, 42, 38, 34)
    f, qatorlar, bal = _sig(d, matn, "sans_m", 880, 452, OLCHAMLAR)
    if rasm is not None:
        # rasm bo'lsa matn uni aylanib o'tadi — qayta hisoblaymiz
        for o in OLCHAMLAR:
            f2 = fnt("sans_m", o)
            b2 = int(o * 1.45)
            q2 = _joyla_aylanma(d, matn, f2, 880, 560, 380, b2,
                                RASM_YUQORI + 20)
            f, qatorlar, bal = f2, q2, b2
            if len(q2) * b2 <= 452:
                break
    _chiz(d, qatorlar, 92, 380, f, (24, 24, 27), bal,
          _urgu_indeks(matn, urgu), (253, 224, 71))

    ost = " · ".join([x for x in (muallif, kitob) if x])
    d.text((92, 852), ost, font=fnt("sans", 30), fill=(130, 130, 138))
    _belgilar(d, 92, 936, (176, 176, 184))
    return img


# ======================================================================
# USLUB 2 — BINAFSHA (Mini App uslubi)
# ======================================================================
def karta_binafsha(matn, muallif, kitob, urgu=None, rasm=None):
    img = Image.new("RGB", (W, H), (15, 10, 28))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H * 0.8
        d.line([(0, y), (W, y)],
               fill=(int(15 + 36 * t), int(10 + 27 * t), int(28 + 64 * t)))

    if rasm is not None:
        # AI fon — to'liq, xiralashtirilgan va qoraytirilgan
        fon = rasm.convert("RGB").resize((W, H), Image.LANCZOS)
        fon = fon.filter(ImageFilter.GaussianBlur(14))
        img = Image.blend(img, fon, 0.42)
        qora = Image.new("RGB", (W, H), (12, 8, 24))
        img = Image.blend(img, qora, 0.34)
    else:
        glow = Image.new("RGB", (W, H), (0, 0, 0))
        g = ImageDraw.Draw(glow)
        g.ellipse([W * .45, -H * .3, W * 1.2, H * .6], fill=(78, 53, 138))
        g.ellipse([-W * .2, H * .55, W * .4, H * 1.3], fill=(54, 37, 92))
        img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(170)), .55)

    d = ImageDraw.Draw(img)
    LAV, DIM = (210, 195, 246), (152, 140, 186)
    d.text((100, 150), "“", font=fnt("serif", 190), fill=(105, 84, 158))

    f, qatorlar, bal = _sig(d, matn, "serif", 860, 430,
                            (60, 55, 50, 46, 42, 38))
    y = _chiz(d, qatorlar, 104, 360, f, LAV, bal)

    d.line([(104, y + 50), (260, y + 50)], fill=(120, 100, 170), width=2)
    if muallif:
        d.text((104, y + 80), muallif, font=fnt("sans_m", 34), fill=LAV)
    if kitob:
        d.text((104, y + 130), kitob, font=fnt("sans_l", 30), fill=DIM)
    d.text((104, 960), BRAND, font=fnt("sans", 28), fill=(120, 104, 162))
    return img


# ======================================================================
# USLUB 3 — QOG'OZ
# ======================================================================
def karta_qogoz(matn, muallif, kitob, urgu=None, rasm=None):
    """Barcha qismlar bitta blok qilib hisoblanadi va vertikal o'rtaga
    joylashtiriladi — shuning uchun rasmli/rasmsiz holatda ham
    hech narsa ramkaga tegib ketmaydi."""
    img = Image.new("RGB", (W, H), (246, 242, 233))
    d = ImageDraw.Draw(img)
    d.rectangle([54, 54, W - 54, H - 54], outline=(214, 204, 186), width=2)

    ICH_YUQORI, ICH_PAST = 96, H - 210      # ramka ichidagi ish maydoni
    # (pastda kanal yozuviga bo'sh joy qoladi)
    RASM = 300
    ORA_RASM, ORA_CHIZIQ, ORA_MUALLIF, ORA_KITOB = 46, 54, 42, 44

    f, qatorlar, bal = _sig(d, matn, "serif_i", 800, 470,
                            (58, 53, 48, 44, 40, 36))

    # --- blok balandligini oldindan hisoblaymiz ---
    qolgan = len(qatorlar) * bal + ORA_CHIZIQ
    if muallif:
        qolgan += ORA_MUALLIF
    if kitob:
        qolgan += ORA_KITOB

    maydon = ICH_PAST - ICH_YUQORI
    if rasm is not None:
        # rasm qolgan joyga moslashadi — blok hech qachon toshib ketmaydi
        RASM = int(max(120, min(RASM, maydon - qolgan - ORA_RASM)))
        balandlik = qolgan + RASM + ORA_RASM
    else:
        balandlik = qolgan

    y = ICH_YUQORI + max(0, (maydon - balandlik) / 2)

    if rasm is not None:
        ch = oq_shaffof(rasm).resize((RASM, RASM), Image.LANCZOS)
        ch = _rangla(ch, (108, 92, 68))
        ch.putalpha(ch.split()[3].point(lambda a: int(a * 0.85)))
        img.paste(ch, ((W - RASM) // 2, int(y)), ch)
        d = ImageDraw.Draw(img)
        y += RASM + ORA_RASM

    y = _chiz(d, qatorlar, 140, y, f, (44, 38, 30), bal, markaz=800)

    y += ORA_CHIZIQ
    d.line([(W / 2 - 40, y), (W / 2 + 40, y)], fill=(180, 165, 140), width=2)
    if muallif:
        y += ORA_MUALLIF
        d.text((W / 2, y), muallif.upper(), font=fnt("sans_m", 30),
               fill=(96, 84, 68), anchor="ma")
    if kitob:
        y += ORA_KITOB
        d.text((W / 2, y), kitob, font=fnt("serif_i", 30),
               fill=(140, 126, 106), anchor="ma")

    d.text((W / 2, H - 108), BRAND, font=fnt("sans_l", 26),
           fill=(168, 156, 138), anchor="ma")
    return img


USLUBLAR = {
    "1": ("Ijtimoiy", karta_ijtimoiy),
    "2": ("Binafsha", karta_binafsha),
    "3": ("Qog'oz", karta_qogoz),
}

# Har uslubga MOS rasm buyrug'i. Matn/harf chizish qat'iy taqiqlangan —
# AI harflarni buzib chizadi va kartani xunuk qiladi.
RASM_USLUBI = {
    "1": ("single continuous one-line drawing, minimalist line art, "
          "thin uniform black ink line, plain pure white background, "
          "lots of empty space, simple and calm"),
    "2": ("abstract atmospheric background, soft flowing organic shapes, "
          "deep violet and lavender, dark moody gradient, subtle film grain, "
          "no objects, no figures, blurred and dreamy"),
    "3": ("vintage book engraving, fine hatching and etching lines, "
          "dark sepia ink on plain white background, "
          "small centered motif, classic and restrained"),
}

TAQIQ = ("Strictly no text, no letters, no words, no numbers, no signature, "
         "no watermark, no logo. No human faces, no recognizable people, "
         "no religious symbols or figures, no brands.")


# ======================================================================
# AI CHAQIRUVLARI
# ======================================================================
def _mijoz():
    from openai import OpenAI
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def _mavzu_sinxron(matn):
    """Iqtibosdan rasm uchun QISQA ingliz mavzusi chiqaradi.
    Matnning o'zi rasm buyrug'iga QO'YILMAYDI — AI uni rasmga yozib
    qo'yishga urinadi."""
    try:
        r = _mijoz().chat.completions.create(
            model=MODEL_FAST,
            messages=[
                {"role": "system", "content":
                    "You turn a quote into a SHORT visual subject for an "
                    "illustration. Answer with 2-6 English words naming one "
                    "simple concrete object or scene. No sentences, no "
                    "quotes, no people's faces, no text elements. "
                    "Example: 'an open book on a windowsill'."},
                {"role": "user", "content": matn[:400]},
            ],
            max_completion_tokens=40,
        )
        mavzu = (r.choices[0].message.content or "").strip().strip('."“”')
        return mavzu[:80] or "an open book"
    except Exception as e:
        log.warning("Iqtibos: mavzu chiqarib bo'lmadi: %s", e)
        return "an open book"


def _rasm_sinxron(uslub, mavzu):
    """GPT Image chaqiruvi. quality parametri qabul qilinmasa —
    parametrsiz qayta uriniladi (taxminga tayanmaslik uchun)."""
    buyruq = f"{RASM_USLUBI[uslub]}. Subject: {mavzu}. {TAQIQ}"
    mijoz = _mijoz()
    urinishlar = [
        dict(model=MODEL_IMAGE, prompt=buyruq, size="1024x1024",
             quality=IMAGE_QUALITY, n=1),
        dict(model=MODEL_IMAGE, prompt=buyruq, size="1024x1024", n=1),
    ]
    oxirgi = None
    for kw in urinishlar:
        try:
            r = mijoz.images.generate(**kw)
            d0 = r.data[0]
            b64 = getattr(d0, "b64_json", None)
            if b64:
                return Image.open(io.BytesIO(base64.b64decode(b64)))
            url = getattr(d0, "url", None)
            if url:
                import urllib.request
                with urllib.request.urlopen(url, timeout=60) as f:
                    return Image.open(io.BytesIO(f.read()))
            raise RuntimeError("rasm ma'lumoti bo'sh")
        except TypeError as e:
            oxirgi = e
            continue
        except Exception as e:
            oxirgi = e
            if "quality" in str(e).lower():
                continue
            break
    log.warning("Iqtibos: rasm chizilmadi: %s", oxirgi)
    return None


# ======================================================================
# MATNNI O'QISH
# ======================================================================
def parse_iqtibos(xom):
    """Matn, urg'u, muallif va kitobni ajratadi.
    Kutilgan ko'rinish:
        Iqtibos matni, *urg'u* bilan.
        — Muallif ismi, "Kitob nomi"
    """
    xom = (xom or "").strip()
    muallif = kitob = ""
    qatorlar = [q.strip() for q in xom.split("\n") if q.strip()]
    if qatorlar and re.match(r"^[—–-]{1,2}\s*\S", qatorlar[-1]):
        ost = re.sub(r"^[—–-]{1,2}\s*", "", qatorlar.pop())
        kitob_m = re.search(r"[\"“«]([^\"”»]+)[\"”»]", ost)
        if kitob_m:
            kitob = kitob_m.group(1).strip()
            ost = ost[:kitob_m.start()]
        muallif = ost.strip().strip(",·").strip()
    matn = " ".join(qatorlar).strip()

    urgu = None
    m = re.search(r"\*([^*]+)\*", matn)
    if m:
        urgu = m.group(1).strip()
        matn = matn.replace("*", "")
    matn = re.sub(r"\s+", " ", matn).strip()
    return matn, urgu, muallif, kitob


def _png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _post_matni(d):
    qismlar = [d["matn"]]
    ost = " · ".join([x for x in (d["muallif"], d["kitob"]) if x])
    if ost:
        qismlar.append(ost)
    return "\n\n".join(qismlar)


# ======================================================================
# BUYRUQ
# ======================================================================
YORDAM = (
    "Iqtibos kartasi\n\n"
    "Shu ko'rinishda yuboring:\n\n"
    "/iqtibos\n"
    "Iqtibos matni, *urg'u beriladigan joy* yulduzcha ichida.\n"
    "— Muallif ismi, \"Kitob nomi\"\n\n"
    "Bot 3 uslubda chizib beradi. Muallif ismini AI qidirmaydi — "
    "siz kiritganingiz qo'yiladi."
)


async def _albom_va_tanlov(context, chat_id, kalit):
    """Uch uslubni ham chizib albom qilib yuboradi va tanlov tugmalarini
    ko'rsatadi. Qo'lda kiritilgan iqtibos ham, rasmdan o'qilgani ham
    shu yerdan o'tadi."""
    d = context.bot_data.get("iqtibos", {}).get(kalit)
    if not d:
        return
    kutish = await context.bot.send_message(chat_id, "Chizilmoqda...")
    albom = []
    for nom in ("1", "2", "3"):
        _, chizuvchi = USLUBLAR[nom]
        img = await asyncio.to_thread(
            chizuvchi, d["matn"], d["muallif"], d["kitob"], d["urgu"], None)
        albom.append(InputMediaPhoto(media=_png(img)))
    await context.bot.send_media_group(chat_id, albom)
    await kutish.delete()

    ogoh = ""
    if not d["muallif"]:
        ogoh = ("\n\n⚠️ Muallif ko'rsatilmagan. Iqtibosni muallifsiz "
                "joylash tavsiya etilmaydi.")
    await context.bot.send_message(
        chat_id, f"Qaysi uslub?{ogoh}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1⃣ Ijtimoiy", callback_data=f"iq_u|{kalit}|1"),
             InlineKeyboardButton("2⃣ Binafsha", callback_data=f"iq_u|{kalit}|2"),
             InlineKeyboardButton("3⃣ Qog'oz", callback_data=f"iq_u|{kalit}|3")],
            [InlineKeyboardButton("❌ Bekor", callback_data=f"iq_x|{kalit}|0")],
        ]))


async def cmd_iqtibos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    xom = re.sub(r"^/iqtibos(@\S+)?", "", update.message.text or "").strip()
    if not xom:
        await update.message.reply_text(YORDAM)
        return

    matn, urgu, muallif, kitob = parse_iqtibos(xom)
    if not matn:
        await update.message.reply_text(YORDAM)
        return
    if len(matn) > MAX_BELGI:
        await update.message.reply_text(
            f"Matn {len(matn)} belgi — kartaga sig'maydi.\n"
            f"{MAX_BELGI} belgigacha qisqartiring, shunda karta kuchli chiqadi.")
        return

    kalit = f"iq{int(time.time())}{random.randint(10, 99)}"
    context.bot_data.setdefault("iqtibos", {})[kalit] = {
        "matn": matn, "urgu": urgu, "muallif": muallif,
        "kitob": kitob, "rasm": None, "uslub": None,
    }

    await _albom_va_tanlov(context, update.message.chat_id, kalit)


# ======================================================================
# TUGMALAR
# ======================================================================
def _tugmalar(kalit, uslub, rasm_bormi):
    qator1 = [InlineKeyboardButton("✅ Kanalga",
                                   callback_data=f"iq_ok|{kalit}|{uslub}")]
    qator2 = [InlineKeyboardButton(
        "\U0001f504 Boshqa rasm" if rasm_bormi else "\U0001f3a8 AI rasm qo'shish",
        callback_data=f"iq_r|{kalit}|{uslub}")]
    if rasm_bormi:
        qator2.append(InlineKeyboardButton(
            "↩️ Rasmsiz", callback_data=f"iq_nr|{kalit}|{uslub}"))
    qator3 = [InlineKeyboardButton("❌ Bekor",
                                   callback_data=f"iq_x|{kalit}|0")]
    return InlineKeyboardMarkup([qator1, qator2, qator3])


async def _korsat(context, chat_id, kalit, uslub, xabar_id=None):
    d = context.bot_data.get("iqtibos", {}).get(kalit)
    if not d:
        return
    nom, chizuvchi = USLUBLAR[uslub]
    img = await asyncio.to_thread(
        chizuvchi, d["matn"], d["muallif"], d["kitob"], d["urgu"], d["rasm"])
    izoh = f"{nom} uslubi" + (" · AI rasm bilan" if d["rasm"] else "")
    media = InputMediaPhoto(media=_png(img), caption=izoh)
    if xabar_id:
        await context.bot.edit_message_media(
            chat_id=chat_id, message_id=xabar_id, media=media,
            reply_markup=_tugmalar(kalit, uslub, d["rasm"] is not None))
    else:
        await context.bot.send_photo(
            chat_id=chat_id, photo=_png(img), caption=izoh,
            reply_markup=_tugmalar(kalit, uslub, d["rasm"] is not None))


async def on_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer()
        return
    try:
        amal, kalit, uslub = (q.data or "").split("|")
    except ValueError:
        await q.answer()
        return

    d = context.bot_data.get("iqtibos", {}).get(kalit)
    if not d and amal != "iq_x":
        await q.answer("Bu iqtibos eskirgan — qaytadan yuboring.",
                       show_alert=True)
        return

    if amal == "iq_x":
        await q.answer()
        context.bot_data.get("iqtibos", {}).pop(kalit, None)
        if q.message.photo:
            await q.edit_message_caption("Bekor qilindi.")
        else:
            await q.edit_message_text("Bekor qilindi.")
        return

    if amal == "iq_ed":
        await q.answer()
        context.user_data["iq_tahrir"] = kalit
        await q.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            q.message.chat_id,
            "To'g'rilangan matnni shu yerga yuboring.\n\n"
            "Muallifni ham o'zgartirmoqchi bo'lsangiz, oxiriga qo'shing:\n"
            "\u2014 Muallif ismi, \"Kitob nomi\"\n\n"
            "Urg'u berish uchun *yulduzcha ichiga* oling.")
        return

    if amal == "iq_ocr":
        await q.answer()
        await q.edit_message_reply_markup(reply_markup=None)
        await _albom_va_tanlov(context, q.message.chat_id, kalit)
        return

    if amal == "iq_u":
        await q.answer()
        d["uslub"] = uslub
        await q.edit_message_text(f"{USLUBLAR[uslub][0]} tanlandi.")
        await _korsat(context, q.message.chat_id, kalit, uslub)
        return

    if amal == "iq_nr":
        await q.answer()
        d["rasm"] = None
        await _korsat(context, q.message.chat_id, kalit, uslub,
                      q.message.message_id)
        return

    if amal == "iq_r":
        await q.answer("Rasm chizilmoqda, 20-40 soniya...")
        mavzu = await asyncio.to_thread(_mavzu_sinxron, d["matn"])
        rasm = await asyncio.to_thread(_rasm_sinxron, uslub, mavzu)
        if rasm is None:
            await context.bot.send_message(
                q.message.chat_id,
                "Rasm chizilmadi. Balans yoki API kalitni tekshiring — "
                "karta rasmsiz ham tayyor.")
            return
        d["rasm"] = rasm
        d["mavzu"] = mavzu
        await _korsat(context, q.message.chat_id, kalit, uslub,
                      q.message.message_id)
        return

    if amal == "iq_ok":
        await q.answer("Yuborilmoqda...")
        nom, chizuvchi = USLUBLAR[uslub]
        img = await asyncio.to_thread(
            chizuvchi, d["matn"], d["muallif"], d["kitob"], d["urgu"],
            d["rasm"])
        try:
            await context.bot.send_photo(
                chat_id=CHANNEL_ID, photo=_png(img),
                caption=_post_matni(d))
            await q.edit_message_caption(f"✅ {CHANNEL_ID} ga joylandi.")
            context.bot_data.get("iqtibos", {}).pop(kalit, None)
        except Exception as e:
            await context.bot.send_message(
                q.message.chat_id,
                f"Joylab bo'lmadi: {e}\n\n"
                f"Bot {CHANNEL_ID} da admin ekanini tekshiring.")
        return


# ======================================================================
# RO'YXATGA OLISH
# ======================================================================
# ======================================================================
# RASMDAN O'QISH (OCR)
# ======================================================================
OCR_KORSATMA = (
    "You read text from photos of printed book pages.\n"
    "Rules:\n"
    "1. Copy the text EXACTLY as printed. Do not translate. Do not fix "
    "spelling. Do not modernise the alphabet. If the page is in Cyrillic, "
    "answer in Cyrillic. If Latin, answer in Latin.\n"
    "2. If several images are given, they are CONSECUTIVE pages of the "
    "same passage, in order. Join them into ONE continuous text. A "
    "sentence cut off at the end of one image continues in the next.\n"
    "3. If a word is split by a hyphen at a line or page break, join it "
    "back into one word.\n"
    "4. If one passage is underlined, highlighted or marked, return ONLY "
    "that passage. Otherwise return the main paragraph(s).\n"
    "5. Never invent words. If a word is unreadable, write it as [?].\n"
    "6. If the author name or book title is visible, report them "
    "separately. If not visible, leave them empty. NEVER guess them.\n"
    "Answer with JSON only, no markdown, no commentary:\n"
    '{"matn": "...", "muallif": "", "kitob": ""}'
)


def _ocr_sinxron(rasmlar):
    """Bir yoki bir nechta rasmdagi matnni o'qiydi.
    Bir nechta sahifa BITTA so'rovda yuboriladi — shunda model gap
    qayerda uzilib, qayerda davom etganini ko'radi va to'g'ri ulaydi.
    Alifbo O'ZGARTIRILMAYDI: o'girish keyin, kirill.py da bajariladi."""
    import json
    if isinstance(rasmlar, (bytes, bytearray)):
        rasmlar = [rasmlar]
    bolaklar = []
    for b in rasmlar[:6]:            # 6 sahifadan ortig'i qabul qilinmaydi
        b64 = base64.b64encode(b).decode()
        bolaklar.append({"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
    try:
        r = _mijoz().chat.completions.create(
            model=MODEL_VISION,
            messages=[
                {"role": "system", "content": OCR_KORSATMA},
                {"role": "user", "content": bolaklar},
            ],
            max_completion_tokens=2000,
        )
        javob = (r.choices[0].message.content or "").strip()
        javob = re.sub(r"^```(json)?|```$", "", javob, flags=re.M).strip()
        m = re.search(r"\{.*\}", javob, re.S)
        if m:
            javob = m.group(0)
        ma = json.loads(javob)
        return (str(ma.get("matn", "")).strip(),
                str(ma.get("muallif", "")).strip(),
                str(ma.get("kitob", "")).strip(), None)
    except Exception as e:
        log.warning("Iqtibos OCR xatosi: %s", e)
        return "", "", "", str(e)


def _tasdiq_tugma(kalit, sigadi=True):
    qatorlar = []
    if sigadi:
        qatorlar.append([InlineKeyboardButton(
            "\u2705 To'g'ri, kartaga", callback_data=f"iq_ocr|{kalit}|0")])
    qatorlar.append([InlineKeyboardButton(
        "\u270f\ufe0f Matnni tahrirlash", callback_data=f"iq_ed|{kalit}|0")])
    qatorlar.append([InlineKeyboardButton(
        "\u274c Bekor", callback_data=f"iq_x|{kalit}|0")])
    return InlineKeyboardMarkup(qatorlar)


async def _rasmni_oqi(context, chat_id, file_idlar):
    """Bir yoki bir nechta sahifani o'qib, matnni TASDIQ uchun ko'rsatadi.
    Karta darrov chizilmaydi — OCR xato qilsa iqtibos buzilgan holda
    kanalga chiqib ketardi."""
    nechta = len(file_idlar)
    kutish = await context.bot.send_message(
        chat_id, f"{nechta} ta sahifa o'qilmoqda..." if nechta > 1
        else "Rasm o'qilmoqda...")

    baytlar = []
    for fid in file_idlar:
        fayl = await context.bot.get_file(fid)
        baytlar.append(bytes(await fayl.download_as_bytearray()))

    matn, muallif, kitob, xato = await asyncio.to_thread(_ocr_sinxron, baytlar)
    try:
        await kutish.delete()
    except Exception:
        pass

    if xato or not matn:
        await context.bot.send_message(
            chat_id,
            "Matnni o'qib bo'lmadi.\n\n"
            "Rasm aniqroq, matn to'g'ri burchakdan tushgan bo'lsa yaxshi "
            "natija beradi. Yoki matnni /iqtibos bilan qo'lda yuboring.")
        return

    kirill_edi = kirill.kirill_bormi(matn)
    matn = kirill.tozala(kirill.kirill_lotin(matn))
    muallif = kirill.kirill_lotin(muallif)
    kitob = kirill.kirill_lotin(kitob)

    kalit = f"iq{int(time.time())}{random.randint(10, 99)}"
    context.bot_data.setdefault("iqtibos", {})[kalit] = {
        "matn": matn, "urgu": None, "muallif": muallif,
        "kitob": kitob, "rasm": None, "uslub": None,
    }
    await _tasdiq_korsat(context, chat_id, kalit,
                         qoshimcha=(nechta, kirill_edi))


async def _tasdiq_korsat(context, chat_id, kalit, qoshimcha=None):
    """Matnni tugmalar bilan tasdiqqa qo'yadi."""
    d = context.bot_data.get("iqtibos", {}).get(kalit)
    if not d:
        return
    matn = d["matn"]
    qatorlar = [matn]
    ost = " \u00b7 ".join([x for x in (d["muallif"], d["kitob"]) if x])
    if ost:
        qatorlar.append(ost)

    belgi = f"{len(matn)} belgi"
    if qoshimcha:
        nechta, kirill_edi = qoshimcha
        if nechta > 1:
            belgi += f" \u00b7 {nechta} sahifa"
        if kirill_edi:
            belgi += " \u00b7 kirilldan o'girildi"
    qatorlar.append("\u2500\u2500\u2500\n" + belgi)

    sigadi = len(matn) <= MAX_BELGI
    if not sigadi:
        qatorlar.append(
            f"\u26a0\ufe0f Kartaga sig'maydi \u2014 chegara {MAX_BELGI} belgi.\n"
            f"\u270f\ufe0f Tahrirlash tugmasi bilan qisqartiring.")
    qatorlar.append("\nMatnni o'qib chiqing.")

    await context.bot.send_message(
        chat_id, "\n\n".join(qatorlar),
        reply_markup=_tasdiq_tugma(kalit, sigadi))


# --- ALBOM: bir necha sahifa birdaniga ------------------------------
# Telegram albomdagi har rasmni ALOHIDA xabar qilib yuboradi va sarlavha
# faqat BIRINCHISIDA bo'ladi. Shuning uchun rasmlar yig'iladi, oxirgisidan
# keyin ALBOM_KUTISH soniya kutiladi va hammasi birga o'qiladi.
ALBOM_KUTISH = 3.0


async def _albom_ishla(context: ContextTypes.DEFAULT_TYPE):
    """Kutish tugagach ishga tushadi."""
    ma = context.job.data
    yigma = context.bot_data.get("iq_yigma", {}).pop(ma["kalit"], None)
    if not yigma or not yigma["fayllar"]:
        return
    await _rasmni_oqi(context, ma["chat_id"], yigma["fayllar"])


def _albom_qoshi(context, chat_id, guruh_id, file_id):
    """Rasmni yig'maga qo'shadi va taymerni qaytadan qo'yadi."""
    yigmalar = context.bot_data.setdefault("iq_yigma", {})
    yigma = yigmalar.setdefault(guruh_id, {"fayllar": [], "job": None})
    yigma["fayllar"].append(file_id)
    if yigma["job"]:
        try:
            yigma["job"].schedule_removal()
        except Exception:
            pass
    jq = getattr(context, "job_queue", None)
    if jq is None:
        return False
    yigma["job"] = jq.run_once(
        _albom_ishla, when=ALBOM_KUTISH,
        data={"kalit": guruh_id, "chat_id": chat_id},
        name=f"iq_albom_{guruh_id}")
    return True


async def on_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha rasmlar shu yerga tushadi. Uch holatda ishlaydi:
       1) sarlavhasi /iqtibos bo'lsa
       2) /iqtibos_rasm bosilgan bo'lsa
       3) allaqachon yig'ilayotgan albomning davomi bo'lsa
    Boshqa hollarda hech narsa qilmaydi (boshqa modullarga xalal bermaydi).
    """
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    msg = update.message
    if not msg or not msg.photo:
        return

    guruh = msg.media_group_id
    yigilayotgan = guruh and guruh in context.bot_data.get("iq_yigma", {})
    sarlavha = bool(msg.caption and re.match(r"(?i)^/iqtibos", msg.caption))
    kutilgan = context.user_data.get("iqtibos_rasm_kutilyapti", False)

    if not (yigilayotgan or sarlavha or kutilgan):
        return

    file_id = msg.photo[-1].file_id

    if guruh:
        # albomning birinchi rasmi bayroqni o'chiradi, qolganlari
        # "yigilayotgan" sifatida kiradi
        context.user_data.pop("iqtibos_rasm_kutilyapti", None)
        if _albom_qoshi(context, msg.chat_id, guruh, file_id):
            return
        # job_queue yo'q bo'lsa \u2014 bittalab ishlaymiz
    else:
        context.user_data.pop("iqtibos_rasm_kutilyapti", None)

    await _rasmni_oqi(context, msg.chat_id, [file_id])


async def cmd_iqtibos_rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    context.user_data["iqtibos_rasm_kutilyapti"] = True
    await update.message.reply_text(
        "Kitob sahifasining rasmini yuboring.\n\n"
        "Iqtibos ikki sahifada bo'lsa \u2014 ikkalasini BIRGA, bitta albom "
        "qilib yuboring. Tartib muhim: avval oldingi sahifa.\n\n"
        "Kerakli joyni chizib yoki belgilab qo'ysangiz \u2014 faqat o'sha "
        "qism olinadi. Kirillcha kitob lotinchaga o'giriladi.")


# --- MATNNI SHU YERNING O'ZIDA TAHRIRLASH ---------------------------
async def on_tahrir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tahrirlash tugmasidan keyin kelgan matn eskisining o'rniga qo'yiladi.
    /iqtibos ni qayta yozish shart emas."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    kalit = context.user_data.get("iq_tahrir")
    if not kalit:
        return
    d = context.bot_data.get("iqtibos", {}).get(kalit)
    if not d:
        context.user_data.pop("iq_tahrir", None)
        return
    xom = (update.message.text or "").strip()
    if not xom:
        return
    context.user_data.pop("iq_tahrir", None)

    matn, urgu, muallif, kitob = parse_iqtibos(xom)
    d["matn"] = kirill.tozala(kirill.kirill_lotin(matn))
    d["urgu"] = urgu
    # muallif/kitob yangi matnda ko'rsatilmagan bo'lsa \u2014 eskisi qoladi
    if muallif:
        d["muallif"] = kirill.kirill_lotin(muallif)
    if kitob:
        d["kitob"] = kirill.kirill_lotin(kitob)
    await _tasdiq_korsat(context, update.message.chat_id, kalit)


def register(app: Application):
    """bot.py dan chaqiriladi: iqtibos.register(app)"""
    app.add_handler(CommandHandler("iqtibos", cmd_iqtibos))
    app.add_handler(CommandHandler("iqtibos_rasm", cmd_iqtibos_rasm))
    # sarlavhasi /iqtibos bo'lgan rasm
    # Rasm va tahrir ushlovchilari 1-guruhda — bot.py va boshqa modullar
    # 0-guruhda ishlaydi, shuning uchun xalal bermaydi. Bayroq qo'yilmagan
    # bo'lsa bu ushlovchilar hech narsa qilmasdan qaytadi.
    app.add_handler(MessageHandler(filters.PHOTO, on_rasm), group=1)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, on_tahrir), group=1)
    app.add_handler(CallbackQueryHandler(
        on_tugma, pattern=r"^iq_(u|r|nr|ok|x|ocr|ed)\|"))
    log.info("Iqtibos moduli yoqildi (kanal: %s, rasm sifati: %s)",
             CHANNEL_ID, IMAGE_QUALITY)
