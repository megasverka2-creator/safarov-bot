# -*- coding: utf-8 -*-
"""
DUBLYAJ — video uchun o'zbekcha OVOZLI tarjima (voice-over)
===========================================================
subtitr.py videoni matnga o'girib bo'lgach, "🔊 Ovozli" tugmasi shu
modulni chaqiradi. Natija — asl video, ustida o'zbekcha ovoz; asl ovoz
gapirilayotganda pasayadi, pauzalarda (musiqa, kulgi) yana eshitiladi.

NIMA UCHUN ESKI USUL ALMASHTIRILDI (hammasi haqiqiy videoda ko'ringan):
  1. Ovozlar USTMA-UST tushardi. O'zbekcha matn inglizchadan uzunroq;
     tezlik 1.6 bilan cheklangani uchun undan uzun bo'lak keyingisining
     ustiga chiqib ketardi — ikki ovoz bir vaqtda gapirardi.
  2. 1.6x tezlik — "sincap ovozi". Tabiiy chegara ~1.25x.
  3. Har Whisper segmenti (2-3 soniya) alohida o'qilardi — intonatsiya
     har jumla o'rtasida uzilardi.
  4. Ovoz uchun SUBTITR tarjimasi ishlatilardi. Subtitr ko'z uchun
     ataylab qisqartiriladi; quloq uchun boshqa matn kerak: vaqtga
     sig'adigan, raqam va qisqartmalari o'qiladigan.
  5. Yuzlab bo'lak ketma-ket so'ralardi va bitta ffmpeg'ga yuzlab kirish
     sifatida berilardi — uzun podkastda sekin va mo'rt.

YANGI TARTIB:
  1. Segmentlar IBORALARGA birlashtiriladi (jumla oxirigacha, 12 s gacha)
  2. Har iboraga VAQT BYUDJETI bilan og'zaki tarjima so'raladi
  3. Ovoz PARALLEL yasaladi, boshi-oxiridagi jimlik kesiladi
  4. Sig'masa: avval 1.25x gacha tezlatiladi, baribir sig'masa — o'sha
     qatorlar BITTA so'rovda qisqartirib qayta o'qitiladi
  5. Ovoz yo'lagi ketma-ket yoziladi: keyingi ibora oldingisi tugamasdan
     BOSHLANMAYDI — ustma-ust tushish printsipial jihatdan imkonsiz.
     Kechikish yig'ilsa, birinchi pauzada o'zi yo'qoladi.
  6. Aralashtirish: asl ovoz "sidechain" bilan — o'zbekcha gapirilganda
     pasayadi, jim joylarda qaytadi. Kirish atigi IKKITA.

OVOZ MANBAI (Railway → DUBLYAJ_TTS):
  openai       — standart, gpt-4o-mini-tts (OPENAI_API_KEY bor bo'lsa ishlaydi)
  aisha        — o'zbek tiliga maxsus; AISHA_API_KEY kerak
  voicestudio  — TEKIN: VoiceStudio sizning Mac'ingizda ishlaydi.
                 Ikki usul:
                 (a) VOICESTUDIO_URL berilMAGAN — TAVSIYA: Mac'dagi
                     ovoz_ishchi.py botdan ish so'rab turadi (ovoz_navbat.py).
                     Mac'da port ochilmaydi, VoiceStudio internetga
                     chiqmaydi. Railway: OVOZ_ISHCHI_KALIT.
                 (b) VOICESTUDIO_URL berilgan — bot to'g'ridan-to'g'ri
                     chaqiradi. Faqat xususiy tarmoq (Tailscale) va
                     OMNIVOICE_API_KEY bilan; hech qachon ochiq tunnel
                     orqali emas.
                 VOICESTUDIO_VOICE = klonlangan ovozning NOMI (masalan
                 "Muslim"); Mac ishchisi uni ID'ga o'zi aylantiradi.
                 Berilmasa — standart ovoz.
                 DIQQAT: VoiceStudio'ning standart modeli (OmniVoice)
                 og'irliklari CC-BY-NC — tijorat kanalida ishlatishdan
                 oldin litsenziyasini tekshiring.
"""

import concurrent.futures as cf
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import wave

import httpx

import ovoz_navbat

log = logging.getLogger(__name__)

# --- sozlamalar --------------------------------------------------------
DUB_TTS = os.environ.get("DUBLYAJ_TTS", "openai").strip().lower()

# OpenAI TTS. Eski SUBTITR_TTS_* nomlari ham o'qiladi — Railway'dagi
# mavjud sozlamalar buzilmasin.
TTS_MODEL = (os.environ.get("DUBLYAJ_TTS_MODEL")
             or os.environ.get("SUBTITR_TTS_MODEL", "gpt-4o-mini-tts"))
TTS_VOICE = (os.environ.get("DUBLYAJ_TTS_VOICE")
             or os.environ.get("SUBTITR_TTS_VOICE", "onyx"))
TTS_INSTR = (os.environ.get("DUBLYAJ_TTS_INSTR")
             or os.environ.get(
                 "SUBTITR_TTS_INSTR",
                 "Speak in Uzbek with natural Uzbek pronunciation. "
                 "Calm, clear, confident podcast narrator. "
                 "Do not add an English accent."))

AISHA_API_KEY = os.environ.get("AISHA_API_KEY", "")
AISHA_BASE = "https://back.aisha.group"
AISHA_OVOZ = os.environ.get("DUBLYAJ_AISHA_OVOZ", "Gulnoza")

VS_URL = os.environ.get("VOICESTUDIO_URL", "").rstrip("/")
VS_VOICE = os.environ.get("VOICESTUDIO_VOICE", "default")
VS_KEY = os.environ.get("VOICESTUDIO_KEY", "") or "yoq"
VS_MODEL = os.environ.get("VOICESTUDIO_MODEL", "omnivoice")

# Vaqtga moslash
MAX_TEMPO = float(os.environ.get("DUBLYAJ_MAX_TEMPO", "1.25"))
# O'zbekcha og'zaki nutq tezligi (belgi/soniya, bo'shliq bilan). Tarjima
# uzunligini shu bilan cheklaymiz. Ovoz sekin chiqsa — kamaytiring.
BELGI_SEK = float(os.environ.get("DUBLYAJ_BELGI_SEK", "14"))
IBORA_MAKS_SEK = float(os.environ.get("DUBLYAJ_IBORA_SEK", "12"))
TANAFFUS_SEK = 0.45            # shundan qisqa pauza — bitta ibora hisoblanadi

# Aralashtirish: asl ovoz pauzalarda shu darajada, gapirilganda yana pastroq
FON = float(os.environ.get("DUBLYAJ_FON", "0.35"))
PARALLEL = int(os.environ.get("DUBLYAJ_PARALLEL", "4"))
# Mac'dagi VoiceStudio baribir bittadan yasaydi (MPS'da bitta ishchi).
# Ko'p parallel so'rov faqat navbatda turib qoladi va vaqti o'tadi —
# ikkitasi yetarli: biri yasalayotganda ikkinchisi yuklanadi.
MAC_PARALLEL = int(os.environ.get("DUBLYAJ_MAC_PARALLEL", "2"))
MAC_KUTISH = int(os.environ.get("DUBLYAJ_MAC_KUTISH", "300"))    # soniya/ibora
TOPLAM = int(os.environ.get("DUBLYAJ_TOPLAM", "40"))   # tarjima to'plami

SR = 24000                     # ichki format: 24 kHz, mono, 16 bit


# ======================================================================
# 1. SEGMENT -> IBORA
# ======================================================================
_TUGADI = (".", "?", "!", "…", '."', '?"', '!"')


def iboralarga(segmentlar, maks_sek=None, tanaffus=TANAFFUS_SEK):
    """Whisper segmentlarini (bosh, oxir, matn) iboralarga birlashtiradi.

    Qo'shni segment QO'SHILADI, agar: oradagi pauza qisqa, oldingisi
    jumlani tugatmagan va birga maks_sek dan oshmasa. Ya'ni "and then
    we" + "went home." bitta ibora bo'ladi — intonatsiya uzilmaydi."""
    maks_sek = maks_sek or IBORA_MAKS_SEK
    natija, joriy = [], None
    for b, o, t in segmentlar:
        t = (t or "").strip()
        if not t:
            continue
        b, o = float(b), float(o)
        if (joriy is not None
                and b - joriy["oxir"] < tanaffus
                and o - joriy["bosh"] <= maks_sek
                and not joriy["matn"].rstrip().endswith(_TUGADI)):
            joriy["oxir"] = o
            joriy["matn"] += " " + t
        else:
            if joriy is not None:
                natija.append(joriy)
            joriy = {"bosh": b, "oxir": o, "matn": t}
    if joriy is not None:
        natija.append(joriy)

    # Har iboraga "joy" — keyingisi boshlanguncha bo'lgan vaqt
    for i, ib in enumerate(natija):
        keyingi = natija[i + 1]["bosh"] if i + 1 < len(natija) else ib["oxir"] + 2.0
        ib["joy"] = max(keyingi - ib["bosh"], 0.5)
        # Tarjima byudjeti: asl nutq davomiyligi + ozgina nafas, lekin
        # keyingi iboraning joyiga kirmaydi
        ib["byudjet"] = max(min(ib["joy"], (ib["oxir"] - ib["bosh"]) + 0.6), 0.8)
        ib["maks_belgi"] = max(12, int(ib["byudjet"] * BELGI_SEK))
    return natija


# ======================================================================
# 2. OG'ZAKI TARJIMA — vaqt byudjeti bilan
# ======================================================================
DUBLYAJ_PROMPT = """Sen video va podkastlarni O'ZBEK TILIGA (lotin) \
OVOZLI tarjima qiladigan tajribali dublyaj muharririsan. Sen yozgan matnni \
diktor o'qiydi va u videodagi nutq bilan BIR VAQTDA eshitiladi.

A. VAQTGA SIG'ISH — eng muhim qoida:
1. Har qator yonida vaqt va belgi chegarasi bor: [n] (≈S s, ≤M belgi). \
Tarjima M belgidan OSHMASIN. Oshsa, diktor ulgurmaydi va ovoz videodan \
orqada qoladi.
2. Qisqartirish kerak bo'lsa — takror, kirish so'zlari, ikkinchi darajali \
tafsilotni tashla. Asosiy fikr, raqam, ism va xulosa QOLSIN.
3. Qatorlarni birlashtirma, bo'lma, tartibini o'zgartirma.

B. QULOQ UCHUN YOZ (ko'z uchun emas):
4. Tabiiy og'zaki-adabiy o'zbek tili: jonli, ravon, bir nafasda o'qiladigan \
jumlalar. Kitobiy va idoraviy iboralar taqiq: "ushbu", "mazkur", \
"hisoblanadi", "amalga oshirmoqda", "...tomonidan", "...bo'yicha".
5. Iboralarni so'zma-so'z o'girma — o'zbekcha muqobilini top. \
"game changer" -> "hammasini o'zgartiradigan narsa".
6. RAQAM va BELGILARNI so'z bilan yoz — diktor ularni to'g'ri o'qisin: \
"3" -> "uch", "2025" -> "ikki ming yigirma beshinchi yil", "40%" -> \
"qirq foiz", "$20" -> "yigirma dollar". Juda katta sonlar: "117 mln" -> \
"bir yuz o'n yetti million".
7. Qisqartmalarni o'qilishicha yoz: "AI" -> "sun'iy intellekt" (yoki qator \
qisqa bo'lsa "ey-ay"), "GPT" -> "ji-pi-ti", "CEO" -> "bosh direktor".
8. Ism, kompaniya, mahsulot nomlari — lotin yozuvida, o'qilishiga yaqin: \
"OpenAI", "Google", "Sam Altman".
9. So'zlashuvdagi "uh", "you know", "I mean", ikkilanish, takror — TASHLA.

C. MA'NO VA OHANG:
10. Ohangni saqla: hazil — hazil, ishonchsizlik — "balki", "menimcha".
11. Manbada YO'Q narsani QO'SHMA. O'z izohing, xulosang — taqiq.
12. Quyidagi BRIF berilgan bo'lsa — undagi atamalar tarjimasi va ohangga \
QAT'IY amal qil: butun video bo'ylab bir xil atama ishlatilsin.

JAVOB — faqat JSON:
{"lines": [{"n": 1, "uz": "..."}, {"n": 2, "uz": "..."}]}
Har kirish qatori uchun bittadan javob SHART."""


QISQARTIR_PROMPT = """Quyidagi o'zbekcha dublyaj qatorlari diktor uchun \
uzun chiqdi — belgilangan vaqtga sig'maydi. Har birini ≤M belgigacha \
QISQARTIR. Asosiy fikr, raqam va ismlar qolsin; takror va ikkinchi darajali \
so'zlar ketsin. Tabiiy og'zaki o'zbek tilida bo'lsin, yangi ma'no qo'shma.

JAVOB — faqat JSON: {"lines": [{"n": 1, "uz": "..."}]}"""


def _json_qatorlar(javob, soni):
    """LLM javobidan {n: matn} xaritasi. Buzuq bo'lsa — bo'sh."""
    try:
        data = json.loads(javob)
    except Exception:
        m = re.search(r"\{.*\}", javob or "", re.S)
        try:
            data = json.loads(m.group(0)) if m else {}
        except Exception:
            data = {}
    xarita = {}
    for el in (data.get("lines") or []):
        try:
            n = int(el.get("n"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 1 <= n <= soni:
            xarita[n] = (el.get("uz") or "").strip()
    return xarita


def ogzaki_tarjima(iboralar, llm, brif="", holat=None):
    """Har iboraga vaqtga sig'adigan og'zaki tarjima yozadi (joyida).

    llm(messages, max_tokens) -> str. To'plamlab so'raladi, har
    to'plamga oldingisining oxiri kontekst sifatida beriladi."""
    kontekst = ""
    jami = (len(iboralar) + TOPLAM - 1) // TOPLAM
    for k in range(jami):
        bolak = iboralar[k * TOPLAM:(k + 1) * TOPLAM]
        if holat and jami > 1:
            holat(f"🌐 Ovoz uchun tarjima... {k + 1}/{jami}")
        kirish = "\n".join(
            f"[{i}] (≈{ib['byudjet']:.1f} s, ≤{ib['maks_belgi']} belgi) {ib['matn']}"
            for i, ib in enumerate(bolak, 1))
        xabarlar = [{"role": "system", "content": DUBLYAJ_PROMPT}]
        if brif:
            xabarlar.append({"role": "user", "content": "BRIF:\n" + brif})
        if kontekst:
            xabarlar.append({"role": "user", "content":
                             "OLDINGI QATORLAR (faqat kontekst, tarjima QILINMAYDI):\n"
                             + kontekst})
        xabarlar.append({"role": "user", "content": kirish})
        xarita = _json_qatorlar(llm(xabarlar, 90 * len(bolak) + 400), len(bolak))
        for i, ib in enumerate(bolak, 1):
            # tushib qolgan qator — ovozsiz qoladi (inglizcha o'qitilmaydi)
            ib["uz"] = xarita.get(i, "")
        kontekst = " ".join(ib["uz"] for ib in bolak[-3:] if ib["uz"])


def _qisqartir(nomzodlar, llm):
    """[(ibora, maks_belgi)] -> joyida ib["uz"] yangilanadi. Bitta so'rov."""
    if not nomzodlar:
        return
    kirish = "\n".join(f"[{i}] (≤{m} belgi) {ib['uz']}"
                       for i, (ib, m) in enumerate(nomzodlar, 1))
    xarita = _json_qatorlar(
        llm([{"role": "system", "content": QISQARTIR_PROMPT},
             {"role": "user", "content": kirish}],
            70 * len(nomzodlar) + 300),
        len(nomzodlar))
    for i, (ib, _) in enumerate(nomzodlar, 1):
        yangi = xarita.get(i)
        if yangi and len(yangi) < len(ib["uz"]):
            ib["uz"] = yangi


# ======================================================================
# 3. OVOZ (TTS)
# ======================================================================
_openai = None
_vs = None


def _openai_klient():
    global _openai
    if _openai is None:
        from openai import OpenAI
        _openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _openai


def _vs_klient():
    global _vs
    if _vs is None:
        from openai import OpenAI
        _vs = OpenAI(base_url=VS_URL, api_key=VS_KEY, timeout=180)
    return _vs


def tts_manba():
    """Haqiqatda ishlatiladigan manba.

    voicestudio tanlangan bo'lsa, URL bo'lmasa ham OpenAI'ga TUSHMAYDI:
    siz tekin variantni tanlagansiz — Mac o'chiq bo'lsa jimgina pul
    sarflash o'rniga, bot ochiq aytadi (tayyormi() ga qarang)."""
    if DUB_TTS == "aisha" and AISHA_API_KEY:
        return "aisha"
    if DUB_TTS == "voicestudio":
        return "voicestudio" if VS_URL else "mac"
    return "openai"


MANBA_NOMI = {"openai": "OpenAI", "aisha": "Aisha",
              "voicestudio": "VoiceStudio (server)",
              "mac": "VoiceStudio (Mac)"}


def tayyormi():
    """Dublyajni boshlashdan OLDIN tekshiruv. Qaytadi: (ha/yo'q, sabab).

    Asosan Mac rejimi uchun: ishchi ulanmagan bo'lsa, videoni yuklab,
    tarjima qilib, keyin 5 daqiqa kutib xato olishdan ko'ra — darrov
    aytgan yaxshi."""
    manba = tts_manba()
    if manba == "mac":
        if not ovoz_navbat.ishchi_tirikmi(90):
            return False, ("Mac'dagi ovoz ishchisi ulanmagan.\n\n"
                           "Tekshiring: Mac yoqiqmi, VoiceStudio ochiqmi va "
                           "ovoz_ishchi.py ishlab turibdimi?\n"
                           "Holat va ko'rsatma: /ovoz_ishchi")
    if DUB_TTS == "aisha" and not AISHA_API_KEY:
        return False, "DUBLYAJ_TTS=aisha, lekin AISHA_API_KEY berilmagan."
    return True, ""


def parallel_soni():
    return MAC_PARALLEL if tts_manba() == "mac" else PARALLEL


def tts(matn):
    """Bitta ibora uchun ovoz. Qaytadi: (baytlar, kengaytma)."""
    manba = tts_manba()
    if manba == "aisha":
        with httpx.Client(timeout=90) as cl:
            r = cl.post(AISHA_BASE + "/api/v1/tts/post/",
                        headers={"X-Api-Key": AISHA_API_KEY},
                        data={"transcript": matn[:990], "language": "uz",
                              "model": AISHA_OVOZ, "mood": "Neutral",
                              "speed": "1.0"})
            if r.status_code == 402:
                raise RuntimeError("Aisha balansi tugagan (402)")
            if r.status_code != 201:
                raise RuntimeError(f"Aisha TTS {r.status_code}: {r.text[:120]}")
            yol = r.json().get("audio_path", "")
            if not yol:
                raise RuntimeError("Aisha javobida audio_path yo'q")
            a = cl.get(yol if yol.startswith("http") else AISHA_BASE + yol)
            a.raise_for_status()
            return a.content, "wav"
    if manba == "mac":
        ish_id = ovoz_navbat.qosh(matn[:1800], VS_VOICE, "uz", VS_MODEL)
        return ovoz_navbat.kut(ish_id, MAC_KUTISH), "wav"
    if manba == "voicestudio":
        r = _vs_klient().audio.speech.create(
            model=VS_MODEL, voice=VS_VOICE, input=matn[:1800],
            response_format="wav", extra_body={"language": "uz"})
        return r.content, "wav"
    kw = {"model": TTS_MODEL, "voice": TTS_VOICE, "input": matn[:1800],
          "response_format": "mp3"}
    if TTS_MODEL.startswith("gpt-"):        # yangi modellar yo'riqnoma oladi
        kw["instructions"] = TTS_INSTR
    return _openai_klient().audio.speech.create(**kw).content, "mp3"


# Boshidagi va oxiridagi jimlikni kesish. TTS har bo'lak atrofida 0.2-0.5 s
# jimlik qoldiradi — 300 iborada bu daqiqalab "havo" va kechikish degani.
_KES = ("silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-45dB,"
        "areverse")


def _wavga(kirish_yol, chiqish_yol, tempo=1.0):
    """Istalgan audio -> 24 kHz mono 16-bit WAV, jimligi kesilgan."""
    filtr = _KES
    if tempo > 1.01:
        filtr += f",atempo={tempo:.3f}"
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", kirish_yol,
         "-af", filtr, "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le",
         "-y", chiqish_yol],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Audio o'zgartirilmadi: {r.stderr[-200:]}")


def wav_davomiylik(yol):
    with wave.open(yol, "rb") as w:
        return w.getnframes() / float(w.getframerate() or SR)


def _ovozlat(ib, papka, i):
    """Bitta iborani ovozlaydi: xom fayl + kesilgan WAV. Joyida yozadi."""
    xom, ext = None, "mp3"
    for urinish in range(2):                     # bitta qayta urinish
        try:
            xom, ext = tts(ib["uz"])
            break
        except Exception as e:
            if urinish:
                raise
            log.warning("TTS qayta urinilmoqda (%d): %s", i, e)
    xom_yol = os.path.join(papka, f"x{i}.{ext}")
    with open(xom_yol, "wb") as f:
        f.write(xom)
    wav_yol = os.path.join(papka, f"w{i}.wav")
    _wavga(xom_yol, wav_yol)
    ib["xom"], ib["wav"] = xom_yol, wav_yol
    ib["d"] = wav_davomiylik(wav_yol)


def _hammasini_ovozlat(iboralar, papka, holat=None):
    """PARALLEL ovozlash. Qaytadi: xato bo'lgan iboralar soni."""
    ishlar = [(i, ib) for i, ib in enumerate(iboralar) if ib.get("uz")]
    xato = 0
    tayyor = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, parallel_soni())) as ex:
        kelajak = {ex.submit(_ovozlat, ib, papka, i): ib for i, ib in ishlar}
        for f in cf.as_completed(kelajak):
            tayyor += 1
            try:
                f.result()
            except Exception as e:
                xato += 1
                kelajak[f]["wav"] = None
                log.warning("TTS xatosi: %s", e)
            if holat and (tayyor % 20 == 0 or tayyor == len(ishlar)):
                holat(f"🔊 Ovoz yasalmoqda... {tayyor}/{len(ishlar)}")
    return xato


# ======================================================================
# 4. VAQTGA MOSLASH
# ======================================================================
def _moslash(iboralar, papka, llm, holat=None):
    """Sig'maganlarini tezlatadi yoki qisqartiradi.

    Qaytadi: (tezlatilgan, qisqartirilgan) sonlari. SEKINLATILMAYDI:
    qisqa ovozdan keyin jimlik tabiiy, cho'zilgan ovoz esa g'alati."""
    uzun = [ib for ib in iboralar if ib.get("wav") and ib["d"] > ib["joy"] * MAX_TEMPO]
    qisqartirildi = 0
    if uzun:
        if holat:
            holat(f"✂️ {len(uzun)} ta uzun qator qisqartirilmoqda...")
        nomzodlar = []
        for ib in uzun:
            # kerakli ulush + ozgina zaxira
            ulush = (ib["joy"] * MAX_TEMPO) / ib["d"] * 0.92
            nomzodlar.append((ib, max(8, int(len(ib["uz"]) * ulush))))
        eski = {id(ib): ib["uz"] for ib, _ in nomzodlar}
        try:
            _qisqartir(nomzodlar, llm)
        except Exception as e:
            log.warning("Qisqartirish ishlamadi: %s", e)
        qayta = [ib for ib, _ in nomzodlar if ib["uz"] != eski[id(ib)]]
        qisqartirildi = len(qayta)

        def _qayta_ovozlat(juft):
            # Qayta ovozlash ishlamasa — eski (uzun) ovoz qoladi va pastda
            # tezlatiladi. Bitta qator butun dublyajni to'xtatmasin.
            k, ib = juft
            try:
                _ovozlat(ib, papka, f"q{k}")
            except Exception as e:
                log.warning("Qisqa qatorni ovozlab bo'lmadi: %s", e)

        with cf.ThreadPoolExecutor(max_workers=max(1, parallel_soni())) as ex:
            list(ex.map(_qayta_ovozlat, enumerate(qayta)))

    tezlatildi = 0
    for i, ib in enumerate(iboralar):
        if not ib.get("wav") or ib["d"] <= ib["joy"]:
            continue
        tempo = min(ib["d"] / ib["joy"], MAX_TEMPO)
        yangi = os.path.join(papka, f"t{i}.wav")
        try:
            _wavga(ib["xom"], yangi, tempo)
            ib["wav"], ib["d"] = yangi, wav_davomiylik(yangi)
            tezlatildi += 1
        except Exception as e:
            log.warning("Tezlatish ishlamadi (%d): %s", i, e)
    return tezlatildi, qisqartirildi


# ======================================================================
# 5. OVOZ YO'LAGI — ketma-ket, ustma-ust tushmaydi
# ======================================================================
def ovoz_yolagi(iboralar, chiqish_yol):
    """Barcha iboralarni bitta WAV ga ketma-ket yozadi.

    Har ibora O'Z VAQTIDA boshlanadi — agar oldingisi hali tugamagan
    bo'lsa, u tugashini kutadi. Shu sababli ikki ovoz hech qachon bir
    vaqtda eshitilmaydi. Kechikish yig'ilsa, birinchi uzunroq pauzada
    o'zi yo'qoladi. Qaytadi: eng katta kechikish (soniya)."""
    kechikish = 0.0
    pozitsiya = 0                            # namunalarda
    bosh_jim = b"\x00\x00" * 4096
    with wave.open(chiqish_yol, "wb") as chiq:
        chiq.setnchannels(1)
        chiq.setsampwidth(2)
        chiq.setframerate(SR)
        for ib in iboralar:
            if not ib.get("wav"):
                continue
            kerak = int(ib["bosh"] * SR)
            boshlanish = max(kerak, pozitsiya)
            kechikish = max(kechikish, (boshlanish - kerak) / SR)
            jim = boshlanish - pozitsiya
            while jim > 0:
                n = min(jim, 4096)
                chiq.writeframes(bosh_jim[:n * 2])
                jim -= n
            with wave.open(ib["wav"], "rb") as w:
                kadrlar = w.readframes(w.getnframes())
            chiq.writeframes(kadrlar)
            pozitsiya = boshlanish + len(kadrlar) // 2
    return kechikish


# ======================================================================
# 6. ARALASHTIRISH
# ======================================================================
def aralashtir(video_yol, ovoz_yol, chiqish_yol):
    """Asl ovoz "sidechain" bilan pasaytiriladi: o'zbekcha gapirilganda
    ~8 barobar pastroq, jim joylarda FON darajasida (musiqa, kulgi
    eshitiladi). Kirish atigi ikkita — uzun podkastda ham tez."""
    filtr = (
        "[1:a]aresample=48000,asplit=2[kalit][ovoz];"
        f"[0:a]aresample=48000,volume={FON}[fon];"
        "[fon][kalit]sidechaincompress=threshold=0.02:ratio=8"
        ":attack=15:release=350[past];"
        "[past][ovoz]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[a]")
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-i", video_yol, "-i", ovoz_yol, "-filter_complex", filtr,
         "-map", "0:v?", "-map", "[a]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
         "-y", chiqish_yol],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Aralashtirishda xato: {r.stderr[-300:]}")


def faqat_audio(video_yol, chiqish_yol):
    """Tayyor videodan mp3 — Telegram 50 MB chegarasiga sig'masa kerak."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video_yol,
         "-vn", "-ac", "1", "-b:a", "96k", "-y", chiqish_yol],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Audio ajratilmadi: {r.stderr[-200:]}")


# ======================================================================
# ASOSIY
# ======================================================================
def dublyaj_qil(video_yol, segmentlar, chiqish_yol, llm, brif="", holat=None):
    """Butun quvur. Qaytadi: hisobot dict.

    segmentlar — Whisper'dan [(bosh, oxir, inglizcha_matn), ...]
    llm        — llm(messages, max_tokens) -> str (JSON javob)
    holat      — ixtiyoriy holat(matn), jarayonni ko'rsatish uchun"""
    iboralar = iboralarga(segmentlar)
    if not iboralar:
        raise RuntimeError("Nutq topilmadi")

    papka = tempfile.mkdtemp(prefix="dub_")
    try:
        ogzaki_tarjima(iboralar, llm, brif, holat)
        if not any(ib.get("uz") for ib in iboralar):
            raise RuntimeError("Tarjima bo'sh qaytdi")

        xato = _hammasini_ovozlat(iboralar, papka, holat)
        ovozlanadigan = sum(1 for ib in iboralar if ib.get("uz"))
        if ovozlanadigan and xato > ovozlanadigan * 0.3:
            raise RuntimeError(
                f"Ovoz yasalmadi: {xato}/{ovozlanadigan} ibora xato berdi "
                f"(manba: {MANBA_NOMI.get(tts_manba(), tts_manba())})")

        tezlatildi, qisqartirildi = _moslash(iboralar, papka, llm, holat)

        if holat:
            holat("🎚 Ovoz aralashtirilmoqda...")
        yolak = os.path.join(papka, "ovoz.wav")
        kechikish = ovoz_yolagi(iboralar, yolak)
        aralashtir(video_yol, yolak, chiqish_yol)

        return {"iboralar": len(iboralar),
                "ovozlandi": sum(1 for ib in iboralar if ib.get("wav")),
                "xato": xato,
                "tezlatildi": tezlatildi,
                "qisqartirildi": qisqartirildi,
                "kechikish": round(kechikish, 1),
                "manba": MANBA_NOMI.get(tts_manba(), tts_manba()),
                "matn": "\n".join(ib["uz"] for ib in iboralar if ib.get("uz"))}
    finally:
        shutil.rmtree(papka, ignore_errors=True)
