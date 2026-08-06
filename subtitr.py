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

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
MODEL_SMART = os.environ.get("AI_MODEL_SMART", "gpt-5.6-terra")
STT_MODEL = os.environ.get("AI_MODEL_STT", "whisper-1")   # vaqt belgisi beradi

MAX_SECONDS = int(os.environ.get("SUBTITR_MAX_SEC", "300"))  # 5 daqiqa
MAX_LINE = int(os.environ.get("SUBTITR_LINE", "24"))  # bir ko'rinishdagi belgi
FONT_SIZE = int(os.environ.get("SUBTITR_FONT_SIZE", "12"))  # qat'iy, masshtablanmaydi
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_NAME = os.environ.get("SUBTITR_FONT", "Liberation Sans")

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
TARJIMA_PROMPT = """Sen professional subtitr tarjimonisan. Senga video \
nutqining segmentlari beriladi. Ularni O'ZBEK TILIGA (lotin yozuvida) o'gir.

SUBTITR QOIDALARI:
1. QISQA yoz — subtitr ekranda 2-4 soniya turadi. Uzun jumlani qisqart, \
lekin ma'noni yo'qotma.
2. Har segment ALOHIDA tarjima qilinadi, lekin oldingi segment bilan \
mazmunan bog'lansin. Segmentlarni birlashtirma yoki bo'lma.
3. Jonli, tabiiy o'zbek tili. Kitobiy va idoraviy iboralar taqiq: \
"ushbu", "mazkur", "amalga oshirmoqda", "hisoblanadi".
4. Atamalarni o'zbek auditoriyasi tushunadigan qilib ber. Kompaniya, \
mahsulot va odam nomlari MANBADAGIDEK qoladi (OpenAI, Whisper, Mark Dowd).
5. Manbada YO'Q narsani qo'shma. Nutqda bo'lmagan izoh yozma.
6. So'zlovchi ikkilanib gapirsa ("uh", "you know", takrorlar) — ularni \
tushirib qoldir, toza jumla yoz.
7. Ma'noni yumshatma: "dangerous" -> "xavfli", "muhim emas" emas.

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


def _kuydir(video_yol, srt_yol, chiqish_yol):
    """Subtitrni videoga kuydiradi.
    DIQQAT: libass shriftni video o'lchamiga O'ZI masshtablaydi (384px etalon).
    Shuning uchun FontSize QAT'IY qoladi — video eniga qarab kattalashtirilsa,
    ikki marta masshtablanib, matn ekrandan chiqib ketadi."""
    uslub = (f"FontName={FONT_NAME},FontSize={FONT_SIZE},PrimaryColour=&HFFFFFF,"
             f"OutlineColour=&H000000,BackColour=&H80000000,BorderStyle=1,"
             f"Outline=0.8,Shadow=1.2,MarginV=70,MarginL=20,MarginR=20,"
             f"Bold=1,Spacing=0.2")
    papka = os.path.dirname(srt_yol) or "."
    nom = os.path.basename(srt_yol)
    filtr = f"subtitles={nom}:force_style='{uslub}'"
    if os.path.isdir(FONTS_DIR):      # repodagi fonts/ papkasidan shrift olinadi
        filtr += f":fontsdir={FONTS_DIR}"
    r = subprocess.run(
        ["ffmpeg", "-i", video_yol, "-vf", filtr,
         "-c:a", "copy", "-preset", "veryfast", "-y", chiqish_yol],
        capture_output=True, text=True, cwd=papka)
    if r.returncode != 0:
        raise RuntimeError(f"Subtitr kuydirilmadi: {r.stderr[-300:]}")


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

        bolaklar = vaqtga_taqsimla(segmentlar, uz)
        srt = srt_yasa(bolaklar)
        srt_yol = os.path.join(ish, "subtitr.srt")
        with open(srt_yol, "w", encoding="utf-8") as f:
            f.write(srt)

        await holat.edit_text("🎞 Subtitr videoga kuydirilmoqda...")
        chiqish = os.path.join(ish, "natija.mp4")
        await asyncio.to_thread(_kuydir, video_yol, srt_yol, chiqish)

        await holat.edit_text("📤 Yuborilmoqda...")
        with open(chiqish, "rb") as f:
            await msg.reply_video(video=f, caption="O'zbekcha subtitr bilan")
        with open(srt_yol, "rb") as f:
            await msg.reply_document(document=f, filename="subtitr.srt",
                                     caption="Montaj uchun subtitr fayli")

        toliq = " ".join(uz)
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
    log.info("Subtitr moduli yoqildi (ffmpeg: %s)",
             "bor" if ffmpeg_bor() else "YO'Q")
