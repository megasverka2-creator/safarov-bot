# -*- coding: utf-8 -*-
"""
TALAFFUZ — diktorga beriladigan matnni o'zbekcha o'qilishiga moslash
====================================================================
Ovoz modeli (VoiceStudio/OmniVoice, OpenAI, Aisha) matnni QANDAY
yozilgan bo'lsa, shunday o'qiydi. O'zbekcha o'qish qoidasi bilan
"Google" — "go-o-gle", "2025" — raqamlarni tanimay qoqilish, "40%" —
belgini tashlab ketish. Modelning o'zini qayta o'qitish (fine-tune) GPU
va yuzlab soat yozuv talab qiladi; lekin xatolarning ko'pchiligi matnni
modelga to'g'ri berish bilan yo'qoladi. Shu modul aynan shuni qiladi:

  1. Apostrof: o' g' va tutuq belgisining barcha shakllari (‘ ’ ʻ ʼ `)
     bitta shaklga keltiriladi — model bir so'zni ikki xil ko'rmasin.
  2. LUG'AT: "Google" -> "gugl", "ChatGPT" -> "chat ji-pi-ti".
     Tayyor ro'yxat bor; admin o'zi to'ldiradi: /talaffuz So'z = aytilishi
     Qo'shimchalar saqlanadi: "Google'ning" -> "guglning", "GPTni" -> "ji-pi-tini".
  3. RAQAMLAR so'zga: "2025" -> "ikki ming yigirma besh",
     "2025-yilda" -> "ikki ming yigirma beshinchi yilda", "40%" -> "qirq foiz",
     "$20 mln" -> "yigirma million dollar", "10:30" -> "o'n o'ttiz".

Hammasi QOIDA asosida, AI ishtirokisiz — bir xil matn doim bir xil
o'qiladi. Faqat OVOZ uchun ishlatiladi: subtitr va ovoz_matni.txt asl
yozilishida qoladi.
"""

import json
import logging
import os
import re
import threading

log = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", ".")
LUGAT_FAYL = os.path.join(DATA_DIR, "talaffuz.json")

# o' / g' va tutuq belgisi qaysi shaklda berilsin. Standart — oddiy "'":
# o'zbekcha internet matnlarining aksariyati shunday yozilgan. Rasmiy
# imlo shakli (oʻ gʻ) ni sinab ko'rish uchun: TALAFFUZ_APOSTROF=ʻ
APOSTROF = os.environ.get("TALAFFUZ_APOSTROF", "'")[:1] or "'"
_APOSTROFLAR = "'‘’ʻʼ`´"

# Tayyor lug'at: AI yangiliklari va podkastlarda tez-tez uchraydigan nomlar.
# Admin /talaffuz_ochir bilan istalganini o'chira oladi yoki o'z variantini
# yozadi — admin qoidasi doim ustun.
STANDART = {
    "AI": "ey-ay",
    "OpenAI": "open ey-ay",
    "xAI": "iks ey-ay",
    "ChatGPT": "chat ji-pi-ti",
    "GPT-4o": "ji-pi-ti for o",
    "GPT": "ji-pi-ti",
    "LLM": "el-el-em",
    "API": "ey-pi-ay",
    "GPU": "ji-pi-yu",
    "CPU": "si-pi-yu",
    "CEO": "si-i-o",
    "USB": "yu-es-bi",
    "VR": "vi-ar",
    "4K": "for-key",
    "iPhone": "ayfon",
    "iPad": "aypad",
    "iOS": "ay-o-es",
    "Wi-Fi": "vay-fay",
    "Google": "gugl",
    "YouTube": "yutub",
    "Facebook": "feysbuk",
    "WhatsApp": "vatsap",
    "Microsoft": "maykrosoft",
    "Apple": "eppl",
    "Nvidia": "envidia",
    "Anthropic": "entropik",
    "Claude": "klod",
    "Gemini": "jemini",
    "DeepMind": "dipmaynd",
    "Copilot": "kopaylot",
    "Midjourney": "midjorni",
    "startup": "startap",
    "online": "onlayn",
}

_qulf = threading.RLock()
_kesh = {"mtime": None, "admin": {}, "qoidalar": None}


# ======================================================================
# LUG'AT
# ======================================================================
def _apostrof(matn):
    return re.sub("[" + _APOSTROFLAR + "]", APOSTROF, matn)


def _admin_lugat():
    """Admin qoidalari: {so'z: aytilishi}. "" — standart qoida o'chirilgan."""
    with _qulf:
        try:
            mtime = os.path.getmtime(LUGAT_FAYL)
        except OSError:
            mtime = None
        if mtime != _kesh["mtime"]:
            data = {}
            if mtime is not None:
                try:
                    with open(LUGAT_FAYL, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
                except Exception as e:
                    log.warning("talaffuz.json o'qilmadi: %s", e)
                    data = {}
            _kesh.update(mtime=mtime, admin=data, qoidalar=None)
        return _kesh["admin"]


def _saqla(data):
    with _qulf:
        os.makedirs(os.path.dirname(LUGAT_FAYL) or ".", exist_ok=True)
        vaqtincha = LUGAT_FAYL + ".tmp"
        with open(vaqtincha, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(vaqtincha, LUGAT_FAYL)
        _kesh.update(mtime=None, qoidalar=None)


def _kalit(soz):
    return _apostrof(" ".join(soz.split()))


def lugat():
    """Amaldagi lug'at: {so'z: aytilishi} — standart + admin (admin ustun)."""
    admin = _admin_lugat()
    natija = {_kalit(k): v for k, v in STANDART.items()}
    for k, v in admin.items():
        k = _kalit(k)
        # admin kaliti standartdan faqat harf katta-kichikligi bilan farq
        # qilsa ham, standartni almashtiradi
        for sk in [s for s in natija if s.lower() == k.lower()]:
            del natija[sk]
        if v:
            natija[k] = v
    return natija


def admin_qoidalari():
    return {k: v for k, v in _admin_lugat().items() if v}


def ochirilgan_standartlar():
    return sorted(k for k, v in _admin_lugat().items() if not v)


def qosh(soz, aytilish):
    """Qoida qo'shadi yoki almashtiradi. Qaytadi: saqlangan kalit."""
    soz, aytilish = _kalit(soz), " ".join(aytilish.split())
    if not soz or not aytilish:
        raise ValueError("so'z ham, aytilishi ham bo'sh bo'lmasin")
    if len(soz) > 60 or len(aytilish) > 120:
        raise ValueError("juda uzun (so'z ≤ 60, aytilishi ≤ 120 belgi)")
    with _qulf:
        data = dict(_admin_lugat())
        for k in [k for k in data if k.lower() == soz.lower()]:
            del data[k]
        data[soz] = aytilish
        _saqla(data)
    return soz


def ochir(soz):
    """Qoidani o'chiradi. Qaytadi: True — o'chirildi, False — topilmadi."""
    soz = _kalit(soz)
    with _qulf:
        data = dict(_admin_lugat())
        topildi = False
        for k in [k for k in data if k.lower() == soz.lower()]:
            topildi = topildi or bool(data[k])
            del data[k]
        standart = [k for k in STANDART if k.lower() == soz.lower()]
        if standart:
            # standart qoida kod ichida — o'chirish belgisini saqlaymiz
            data[standart[0]] = ""
            topildi = True
        if topildi:
            _saqla(data)
        return topildi


_HARF = r"[^\W\d_]"


def _qoidalar():
    """Kompilyatsiya qilingan qoidalar, uzuni oldin (ChatGPT, keyin GPT)."""
    with _qulf:
        lug = lugat()
        if _kesh["qoidalar"] is not None and _kesh.get("lug") == lug:
            return _kesh["qoidalar"]
        ap = re.escape(_APOSTROFLAR)
        qoidalar = []
        for soz in sorted(lug, key=len, reverse=True):
            qisqartma = soz.upper() == soz and re.search(_HARF, soz)
            # Qisqartma (GPT, AI) — faqat katta harfda; "GPTni" kabi
            # qo'shimcha to'g'ridan-to'g'ri ulanishi mumkin.
            # Oddiy so'z (Google) — katta-kichik harf farqsiz; qo'shimcha
            # faqat apostrof yoki chiziqcha orqali: Google'ning, Google-ga.
            oxiri = r"(?![A-Z0-9])" if qisqartma else r"(?!\w)"
            naqsh = (r"(?<![\w" + ap + r"])" + re.escape(soz)
                     + r"(?:([" + ap + r"])(?=" + _HARF + r")|" + oxiri + r")")
            qoidalar.append((re.compile(naqsh, 0 if qisqartma else re.I),
                             lug[soz]))
        _kesh["qoidalar"], _kesh["lug"] = qoidalar, lug
        return qoidalar


def _lugat_qoll(matn):
    for naqsh, aytilish in _qoidalar():
        matn = naqsh.sub(lambda m, a=aytilish: a, matn)
    return matn


# ======================================================================
# RAQAMLAR
# ======================================================================
_BIRLAR = ["", "bir", "ikki", "uch", "to'rt", "besh", "olti", "yetti",
           "sakkiz", "to'qqiz"]
_ONLAR = ["", "o'n", "yigirma", "o'ttiz", "qirq", "ellik", "oltmish",
          "yetmish", "sakson", "to'qson"]
_DARAJA = ["", "ming", "million", "milliard", "trillion", "kvadrillion"]


def _uchlik(n):
    """1..999 -> so'z."""
    qism = []
    yuz, qoldiq = divmod(n, 100)
    if yuz:
        qism.append("yuz" if yuz == 1 else _BIRLAR[yuz] + " yuz")
    on, bir = divmod(qoldiq, 10)
    if on:
        qism.append(_ONLAR[on])
    if bir:
        qism.append(_BIRLAR[bir])
    return " ".join(qism)


def son_soz(n):
    """Butun son -> o'zbekcha so'z. 1000 -> "ming", 2025 -> "ikki ming yigirma besh"."""
    n = int(n)
    if n == 0:
        return "nol"
    if n < 0:
        return "minus " + son_soz(-n)
    guruhlar = []
    while n:
        n, g = divmod(n, 1000)
        guruhlar.append(g)
    if len(guruhlar) > len(_DARAJA):          # juda katta — raqamma-raqam
        return " ".join(_BIRLAR[int(r)] or "nol" for r in str(n))
    qism = []
    for i in range(len(guruhlar) - 1, -1, -1):
        g = guruhlar[i]
        if not g:
            continue
        if i == 1 and g == 1:
            qism.append("ming")               # "bir ming" emas — "ming"
        else:
            qism.append(_uchlik(g) + (" " + _DARAJA[i] if i else ""))
    return " ".join(qism)


def tartib_soz(n):
    """Tartib son: 1 -> "birinchi", 2025 -> "ikki ming yigirma beshinchi"."""
    s = son_soz(n)
    return s + ("nchi" if s[-1] in "aeiou" else "inchi")


def _raqam_satr(raqamlar):
    """Boshida nol bo'lgan raqamlar (007) — bittalab."""
    if len(raqamlar) > 1 and raqamlar[0] == "0":
        return " ".join(_BIRLAR[int(r)] or "nol" for r in raqamlar)
    return son_soz(int(raqamlar))


def _kasr(butun, kasr, vergul):
    """3,5 -> "uch butun o'ndan besh"; 5.5 (versiya, inglizcha) -> "besh nuqta besh"."""
    if vergul and len(kasr) <= 3:
        maxraj = {1: "o'ndan", 2: "yuzdan", 3: "mingdan"}[len(kasr)]
        return f"{son_soz(int(butun))} butun {maxraj} {son_soz(int(kasr))}"
    return f"{son_soz(int(butun))} nuqta {_raqam_satr(kasr)}"


_VALYUTA = {"$": "dollar", "€": "yevro", "£": "funt sterling", "₽": "rubl",
            "¥": "yen"}
_KOPAYTMA = {"k": "ming", "ming": "ming", "m": "million", "mln": "million",
             "million": "million", "b": "milliard", "bn": "milliard",
             "mlrd": "milliard", "milliard": "milliard", "billion": "milliard",
             "t": "trillion", "trln": "trillion", "trillion": "trillion"}

# 1,000,000 / 1 000 000 / 3,5 / 5.5 / 42
_SON = r"(\d{1,3}(?:[,   ]\d{3})+(?![\d.,]\d)|\d+(?:[.,]\d+)?)"
_KOP = r"(?:\s?(k|K|M|B|bn|mln|mlrd|trln|ming|million|milliard|billion|trillion)\b)?"


def _son_matn(s):
    """Topilgan son satri -> so'z (guruhlash va kasrni hisobga olib)."""
    if re.fullmatch(r"\d{1,3}(?:[,   ]\d{3})+", s):
        return son_soz(int(re.sub(r"\D", "", s)))
    m = re.fullmatch(r"(\d+)([.,])(\d+)", s)
    if m:
        return _kasr(m.group(1), m.group(3), m.group(2) == ",")
    return _raqam_satr(s)


def _valyuta_old(m):              # $20, $1.5 mln, € 30
    kop = _KOPAYTMA.get((m.group(3) or "").lower(), "")
    return " ".join(x for x in (_son_matn(m.group(2)), kop,
                                _VALYUTA[m.group(1)]) if x)


def _valyuta_keyin(m):            # 20$, 30 €
    kop = _KOPAYTMA.get((m.group(2) or "").lower(), "")
    return " ".join(x for x in (_son_matn(m.group(1)), kop,
                                _VALYUTA[m.group(3)]) if x)


def _raqamlar(matn):
    vb = "[" + re.escape("".join(_VALYUTA)) + "]"
    # valyuta: $20 mln / 20 mln $  (K/M/B faqat valyuta bilan — "4K video" buzilmasin)
    matn = re.sub(r"(" + vb + r")\s?" + _SON + _KOP, _valyuta_old, matn)
    matn = re.sub(_SON + _KOP + r"\s?(" + vb + r")", _valyuta_keyin, matn)
    # foiz
    matn = re.sub(_SON + r"\s?%", lambda m: _son_matn(m.group(1)) + " foiz", matn)
    # vaqt: 10:30
    matn = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b",
                  lambda m: son_soz(int(m.group(1)))
                  + ("" if m.group(2) == "00" else " " + _raqam_satr(m.group(2))),
                  matn)
    # GPT-5, Llama-3 -> "GPT 5": chiziqcha minus yoki tartib deb o'qilmasin
    matn = re.sub(r"(?<=" + _HARF + r")-(?=\d)", " ", matn)
    # tartib son: 2025-yil, 3-o'rin, 1990-yillarda
    matn = re.sub(r"(?<![\d.,])(\d+)-(?=" + _HARF + r")",
                  lambda m: tartib_soz(int(m.group(1))) + " ", matn)
    # oraliq: 5-6 ta, 2020–2024
    matn = re.sub(r"(?<=\d)\s?[-–—]\s?(?=\d)", " - ", matn)
    # ko'paytma so'z bilan: 117 mln, 2 mlrd (valyutasiz)
    matn = re.sub(_SON + r"\s?(mln|mlrd|trln)\b",
                  lambda m: _son_matn(m.group(1)) + " " + _KOPAYTMA[m.group(2)],
                  matn)
    # 10K obunachi (4K lug'atda — undan oldin almashtiriladi)
    matn = re.sub(r"(?<![\w.,])(\d+)[kK]\b",
                  lambda m: son_soz(int(m.group(1))) + " ming", matn)
    # qolgan hamma son; qo'shimcha ulanib qoladi: 5ta -> beshta, 2025da
    matn = re.sub(_SON, lambda m: _son_matn(m.group(1)), matn)
    return matn


_BELGILAR = [
    (re.compile(r"\s*&\s*"), " va "),
    (re.compile(r"%"), " foiz"),
    (re.compile(r"№\s*"), "raqam "),
    (re.compile(r"°\s*C\b"), " daraja"),
    (re.compile(r"[*_#~^|<>\[\]{}]"), " "),   # markdown qoldiqlari
]


def _belgilar(matn):
    for naqsh, almashtir in _BELGILAR:
        matn = naqsh.sub(almashtir, matn)
    return re.sub(r"[ \t]{2,}", " ", matn).strip()


def ozgartir(matn):
    """Diktorga beriladigan yakuniy matn."""
    if not matn:
        return matn
    try:
        matn = _apostrof(matn)
        matn = _lugat_qoll(matn)
        matn = _raqamlar(matn)
        return _belgilar(matn)
    except Exception as e:           # talaffuz hech qachon ovozni to'xtatmasin
        log.warning("talaffuz xatosi: %s", e)
        return matn
