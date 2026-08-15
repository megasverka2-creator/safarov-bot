# -*- coding: utf-8 -*-
"""
KIRILL → LOTIN o'giruvchi (o'zbek tili, 1995 yilgi alifbo)
==========================================================
AI'ga tegishli EMAS — qat'iy jadval bo'yicha ishlaydi.

Nega shunday: kitobdan olingan iqtibos aynan muallif yozganidek qolishi
kerak. AI o'girsa, so'zni "tuzatib" yoki almashtirib yuborishi mumkin.
Jadval esa har safar bir xil natija beradi va tekshirib bo'ladi.

Aralash matn (bir qismi lotin, bir qismi kirill) ham to'g'ri ishlaydi:
lotin harflar teginilmaydi.
"""

import re

# --- oddiy harflar ---
JADVAL = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ғ': "g'", 'д': 'd',
    'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'қ': 'q',
    'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'т': 't', 'у': 'u', 'ў': "o'", 'ф': 'f', 'х': 'x',
    'ҳ': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sh',
    'ъ': '\x01', 'ы': 'i', 'ь': '', 'э': 'e',   # \x01 — vaqtinchalik belgi
    'ё': 'yo', 'ю': 'yu', 'я': 'ya',
}

UNLILAR = set("аеёиоуўэюяыAEIOUaeiou")


def _katta(lotin, harf_katta, keyingi_ham_katta):
    """Bosh harfni to'g'ri qo'yadi.
    'Ш' → 'Sh',  lekin BUTUN SO'Z KATTA bo'lsa → 'SH'."""
    if not lotin:
        return lotin
    if not harf_katta:
        return lotin
    if keyingi_ham_katta and len(lotin) > 1:
        return lotin.upper()
    return lotin[0].upper() + lotin[1:]


def _e_yoki_ye(oldingi):
    """'е' harfi: so'z boshida yoki unlidan keyin → 'ye', aks holda 'e'."""
    if oldingi is None or not oldingi.isalpha():
        return 'ye'
    if oldingi.lower() in UNLILAR or oldingi.lower() in ('ъ', 'ь'):
        return 'ye'
    return 'e'


def kirill_bormi(matn):
    return bool(re.search(r'[\u0400-\u04FF]', matn or ''))


def kirill_lotin(matn):
    """Kirill harflarni lotinga o'giradi. Lotin harflar teginilmaydi."""
    if not matn:
        return matn
    natija = []
    n = len(matn)
    for i, ch in enumerate(matn):
        past = ch.lower()
        katta = ch != past and ch.upper() == ch

        # keyingi harf ham katta bo'lsa — so'z butunlay katta yozilgan
        keyingi_katta = False
        if katta:
            for j in range(i + 1, n):
                if matn[j].isalpha():
                    keyingi_katta = matn[j].isupper()
                    break

        if past == 'е':
            lotin = _e_yoki_ye(matn[i - 1] if i > 0 else None)
            natija.append(_katta(lotin, katta, keyingi_katta))
            continue

        if past in JADVAL:
            natija.append(_katta(JADVAL[past], katta, keyingi_katta))
            continue

        natija.append(ch)

    matn = ''.join(natija)
    # 'ъ' dan kelgan tutuq belgisi so'z OXIRIDA keraksiz — olib tashlanadi.
    # Bu faqat \x01 ga tegishli: g' va o' dagi apostrofga TEGILMAYDI
    # (avval oddiy apostrof ishlatilib, "Tog'" -> "Tog" xatosi chiqqan edi).
    matn = re.sub(r'\x01(?=[\s.,!?;:»”)\]]|$)', '', matn)
    matn = matn.replace('\x01', "'")
    matn = re.sub(r"\s+", ' ', matn).strip()
    return matn


# ======================================================================
# QATORDAN KO'CHIRISH CHIZIG'INI TOZALASH
# ======================================================================
def defis_biriktir(matn):
    """Kitobda qator oxirida so'z bo'linadi: "fe'l-atvori- ga".
    Bunday chiziqcha OLIB TASHLANADI va so'z birlashtiriladi.

    DIQQAT: chiziqchadan keyin BO'SH JOY bo'lsagina birlashtiriladi.
    Haqiqiy qo'shma so'zlar ("fe'l-atvor", "bir-birini") teginilmaydi,
    chunki ularda chiziqchadan keyin bo'shliq yo'q.
    """
    if not matn:
        return matn
    matn = re.sub(r"(\w)[-\u2010\u2011]\s+(\w)", r"\1\2", matn)
    return matn


def tozala(matn):
    """Rasmdan o'qilgan matnni tartibga soladi."""
    if not matn:
        return matn
    matn = defis_biriktir(matn)
    matn = re.sub(r"\s+", " ", matn).strip()
    return matn
