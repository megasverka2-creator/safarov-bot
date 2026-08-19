# -*- coding: utf-8 -*-
"""
reels.py — Stories/Reels generatori (faqat ADMIN uchun).

Matndan 1080x1920 tik video yasaydi: brendli fon, matn bo'lak-bo'lak
paydo bo'ladi, tepada jarayon chizig'i, pastda kanal nomi. Tayyor fayl
Instagram Stories/Reels va TikTok'ka to'g'ridan-to'g'ri yuklanadi.

ISHLATISH:
    /reels Matn shu yerda. Ikkinchi jumla ham bo'lishi mumkin.
yoki shunchaki /reels — keyin matnni alohida xabarda yuborasiz.

QANDAY ISHLAYDI: har bo'lak uchun PNG kadr chiziladi (Pillow), kadrlar
ffmpeg'ning concat demuxer'i orqali videoga yig'iladi. Matn ffmpeg'ning
drawtext'i bilan emas, Pillow bilan chiziladi — shunda shrift, urg'u
rangi va qator bo'linishi kartalardagidek nazorat ostida bo'ladi
(drawtext'da o'zbekcha apostrof va tinish belgilarini qochirish ham
alohida muammo bo'lardi).

bot.py:  import reels  →  reels.register(app)
"""

import asyncio
import logging
import os
import random
import re
import shutil
import subprocess
import tempfile
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

# Karta dizayni bilan bir xil tilda gapirish uchun agent'dagi chizish
# yordamchilari qayta ishlatiladi — ikkalasi bir brend, ikki marta
# yozilgan kod esa vaqt o'tib bir-biridan uzoqlashadi.
from agent import (
    CARD_PALETTES, _card_font, _don_qosh, _hex_rgb, _mesh_fon,
    _qator_chiz, _urgu_indeksi, _wrap_sozlar,
)

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = ImageDraw = None

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
KANAL = os.environ.get("REELS_CHANNEL",
                       os.environ.get("CHANNEL_ID", "@safaroov_blog"))
BREND = os.environ.get("REELS_BREND", KANAL)

W, H = 1080, 1920
FPS = 30
MAKS_BELGI = int(os.environ.get("REELS_MAX_BELGI", "420"))
# Bo'lak ekranda qancha turadi (soniya)
MIN_DAVOM = float(os.environ.get("REELS_MIN_DAVOM", "1.7"))
MAKS_DAVOM = float(os.environ.get("REELS_MAKS_DAVOM", "4.5"))
BELGI_VAQTI = float(os.environ.get("REELS_BELGI_VAQTI", "0.055"))  # har belgiga
# Orqa fon musiqasi: repodagi fayl yo'li yoki mutlaq yo'l. Bo'sh — musiqasiz.
MUSIQA = os.environ.get("REELS_MUSIC", "").strip()

# Fon variantlari: (rubrika, palitra raqami). Rubrikalar CARD_PALETTES dan.
FONLAR = [("ai", 0), ("dunyo", 0), ("islom", 0), ("mutolaa", 0),
          ("texno", 1), ("rivojlanish", 0), ("ai", 3), ("dunyo", 3)]

_ishlar = {}          # {kalit: {"matn": ..., "fon": int, "chat": int}}


def ffmpeg_bor():
    return shutil.which("ffmpeg") is not None


# ======================================================================
# MATNNI BO'LAKLARGA BO'LISH
# ======================================================================
_OLCHAM_ZINASI = (104, 94, 84, 76, 68, 60, 54, 48)


def _shrift_tanla(d, matn, maks_en, maks_qator):
    """Eng yirik shrift: har JUMLA bitta ekranga sig'sin.

    Uzunligiga qarab taxminan tanlasak, jumla ikki ekranga bo'linib
    ketadi va fikr yarmida uziladi. Shuning uchun shriftni o'lchab
    tanlaymiz — matn qanchalik uzun bo'lsa, shuncha kichrayadi."""
    jumlalar = _jumlalarga(matn)
    for olcham in _OLCHAM_ZINASI:
        font = _card_font(olcham)
        if all(len(_wrap_sozlar(d, j, font, maks_en)) <= maks_qator
               for j in jumlalar):
            return font
    return _card_font(_OLCHAM_ZINASI[-1])


def _jumlalarga(matn):
    """Matnni jumlalarga bo'ladi."""
    jumlalar, joriy = [], []
    for soz in matn.split():
        joriy.append(soz)
        if soz[-1:] in ".!?…":
            jumlalar.append(joriy)
            joriy = []
    if joriy:
        jumlalar.append(joriy)
    return jumlalar


def _muvozanat(d, sozlar, font, maks_en):
    """Qatorlarni muvozanatli joylaydi.

    Ochko'z bo'lish "Muhimi tezlik / emas, / muntazamlik." kabi bir so'zlik
    yetim qator qoldiradi. Qatorlar soni o'sha-o'sha, lekin eng uzun qator
    enini minimallashtirsak — matn blok bo'lib, tekis ko'rinadi."""
    qatorlar = _wrap_sozlar(d, sozlar, font, maks_en)
    n_qator, n = len(qatorlar), len(sozlar)
    if n_qator < 2:
        return qatorlar
    CHEK = float("inf")
    en = [[CHEK] * (n + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(i + 1, n + 1):
            e = d.textlength(" ".join(sozlar[i:j]), font=font)
            if e > maks_en and j > i + 1:
                break
            en[i][j] = e
    dp = [[None] * (n + 1) for _ in range(n_qator + 1)]
    dp[0][0] = (0.0, [])
    for k in range(1, n_qator + 1):
        for j in range(1, n + 1):
            eng = None
            for i in range(j):
                if dp[k - 1][i] is None or en[i][j] == CHEK:
                    continue
                qiymat = max(dp[k - 1][i][0], en[i][j])
                if eng is None or qiymat < eng[0]:
                    eng = (qiymat, dp[k - 1][i][1] + [sozlar[i:j]])
            dp[k][j] = eng
    return dp[n_qator][n][1] if dp[n_qator][n] else qatorlar


def _bolaklar(d, matn, font, maks_en, maks_qator=3):
    """Matnni ekranga chiqadigan bo'laklarga bo'ladi.

    Bo'lish JUMLA bo'yicha: tomoshabin har ekranda tugallangan fikrni
    o'qiydi. Qisqa jumlalar sig'sa — birlashtiriladi (bitta so'z uchun
    alohida ekran sekin va zerikarli chiqadi)."""
    guruhlar, joriy = [], []
    for jumla in _jumlalarga(matn):
        nomzod = joriy + jumla
        if joriy and len(_wrap_sozlar(d, nomzod, font, maks_en)) > maks_qator:
            guruhlar.append(joriy)
            joriy = jumla
        else:
            joriy = nomzod
    if joriy:
        guruhlar.append(joriy)

    natija = []
    for guruh in guruhlar:
        qatorlar = _muvozanat(d, guruh, font, maks_en)
        # Jumlaning o'zi uzun bo'lsa — bir necha ekranga bo'linadi
        for i in range(0, len(qatorlar), maks_qator):
            natija.append(qatorlar[i:i + maks_qator])
    return natija


def _davomiylik(bolak):
    belgilar = sum(len(" ".join(q)) for q in bolak)
    return max(MIN_DAVOM, min(belgilar * BELGI_VAQTI, MAKS_DAVOM))


# ======================================================================
# KADRLARNI CHIZISH
# ======================================================================
def _fon_yasa(fon_no):
    """Brendli fon: mesh gradient + don + pastda kanal nomi."""
    rubrika, variant = FONLAR[fon_no % len(FONLAR)]
    pal = CARD_PALETTES.get(rubrika, CARD_PALETTES["ai"])
    top, bottom, accent = (_hex_rgb(c) for c in pal[variant % len(pal)])
    uchinchi = tuple(int(b * 0.62 + a * 0.38) for b, a in zip(bottom, accent))
    img = _don_qosh(_mesh_fon(W, H, (top, bottom, uchinchi))).convert("RGB")

    d = ImageDraw.Draw(img, "RGBA")
    # Instagram Stories interfeysi pastki ~13% ni yopadi — brend shundan
    # yuqorida turishi kerak, aks holda "javob yozish" paneli ustiga tushadi.
    f_brend = _card_font(40)
    bw = d.textlength(BREND, font=f_brend)
    d.text(((W - bw) / 2, H - 285), BREND, font=f_brend,
           fill=(255, 255, 255, 225))
    return img, accent


def _kadr(fon, accent, bolak, font, shaffof, siljish, jarayon):
    """Bitta kadr: fon ustiga bo'lak matni.
    shaffof — 0..255 (paydo bo'lish), siljish — pastdan yuqoriga surilish,
    jarayon — 0..1, tepadagi chiziq."""
    img = fon.copy()
    d = ImageDraw.Draw(img, "RGBA")

    # Tepadagi jarayon chizig'i — video qancha qolganini ko'rsatadi
    d.rectangle([0, 0, W, 8], fill=(255, 255, 255, 45))
    d.rectangle([0, 0, int(W * max(0.0, min(jarayon, 1.0))), 8],
                fill=accent + (235,))

    lh = int(font.size * 1.22)
    jami_h = lh * len(bolak)
    y = (H - jami_h) // 2 + siljish
    sozlar = [s for qator in bolak for s in qator]
    urgu = _urgu_indeksi(sozlar)
    sanalgan = 0
    for qator in bolak:
        matn = " ".join(qator)
        x = (W - d.textlength(matn, font=font)) / 2
        d.text((x + 4, y + 4), matn, font=font, fill=(0, 0, 0, shaffof // 2))
        urgu_no = urgu - sanalgan if 0 <= urgu - sanalgan < len(qator) else -1
        _qator_chiz(d, x, y, qator, font, (255, 255, 255, shaffof),
                    accent + (shaffof,), urgu_no)
        sanalgan += len(qator)
        y += lh
    return img


# Paydo bo'lish: shaffoflik oshadi, matn birozdan yuqoriga suriladi
_PAYDO = [(70, 26), (130, 18), (180, 11), (215, 6), (240, 2), (255, 0)]
_PAYDO_KADR = 0.045          # har bir paydo bo'lish kadri necha soniya


def _kadrlarni_yoz(matn, fon_no, papka):
    """Barcha kadrlarni PNG qilib yozadi. Qaytaradi: concat ro'yxati yo'li."""
    fon, accent = _fon_yasa(fon_no)
    d0 = ImageDraw.Draw(fon)
    maks_en = W - 150
    maks_qator = 3
    font = _shrift_tanla(d0, matn, maks_en, maks_qator)
    if font.size < 60:
        # Uch qatorga sig'dirish uchun shrift juda kichrayib ketdi —
        # to'rtinchi qatorga ruxsat berib, matnni yiriklashtiramiz.
        maks_qator = 4
        font = _shrift_tanla(d0, matn, maks_en, maks_qator)
    bolaklar = _bolaklar(d0, matn, font, maks_en, maks_qator)
    if not bolaklar:
        raise RuntimeError("Matn bo'sh")

    davomlar = [_davomiylik(b) for b in bolaklar]
    jami_vaqt = sum(davomlar) or 1.0

    qatorlar, no, otgan = [], 0, 0.0
    for i, bolak in enumerate(bolaklar):
        paydo_vaqti = _PAYDO_KADR * len(_PAYDO)
        ushlash = max(davomlar[i] - paydo_vaqti, 0.5)
        for j, (shaffof, siljish) in enumerate(_PAYDO):
            yol = os.path.join(papka, f"k{no:04d}.png")
            _kadr(fon, accent, bolak, font, shaffof, siljish,
                  (otgan + j * _PAYDO_KADR) / jami_vaqt).save(yol)
            qatorlar.append((yol, _PAYDO_KADR))
            no += 1
        otgan += paydo_vaqti
        yol = os.path.join(papka, f"k{no:04d}.png")
        _kadr(fon, accent, bolak, font, 255, 0,
              (otgan + ushlash) / jami_vaqt).save(yol)
        qatorlar.append((yol, ushlash))
        no += 1
        otgan += ushlash

    royxat = os.path.join(papka, "kadrlar.txt")
    with open(royxat, "w", encoding="utf-8") as f:
        for yol, davom in qatorlar:
            f.write(f"file '{os.path.basename(yol)}'\nduration {davom:.3f}\n")
        # concat demuxer oxirgi kadrni yana bir marta talab qiladi,
        # aks holda u ko'rinmay qoladi
        f.write(f"file '{os.path.basename(qatorlar[-1][0])}'\n")
    return royxat, jami_vaqt


def _musiqa_yoli():
    if not MUSIQA:
        return None
    yol = MUSIQA if os.path.isabs(MUSIQA) else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), MUSIQA)
    return yol if os.path.exists(yol) else None


def _video_yig(royxat, chiqish, davomiylik):
    papka = os.path.dirname(royxat)
    buyruq = ["ffmpeg", "-hide_banner", "-loglevel", "error",
              "-f", "concat", "-safe", "0", "-i", os.path.basename(royxat)]
    musiqa = _musiqa_yoli()
    if musiqa:
        buyruq += ["-stream_loop", "-1", "-i", musiqa]
    buyruq += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
               "-preset", "veryfast", "-movflags", "+faststart"]
    if musiqa:
        # Musiqa cheksiz aylanadi, "-shortest" uni video tugagan joyda kesadi
        sonish = max(davomiylik - 1.2, 0.1)
        buyruq += ["-c:a", "aac", "-b:a", "128k", "-shortest",
                   "-af", f"volume=0.35,afade=t=out:st={sonish:.2f}:d=1.2"]
    # DIQQAT: bu yerda "-t" ISHLATILMAYDI. concat demuxer'da kadrlar
    # takrorlanib CFR ga keltirilgani uchun "-t" videoni vaqtidan oldin
    # kesib qo'yadi (5.4 s o'rniga 4.0 s). Uzunlikni kadrlar ro'yxatining
    # o'zi belgilaydi.
    buyruq += ["-y", chiqish]

    r = subprocess.run(buyruq, capture_output=True, text=True, cwd=papka)
    if r.returncode != 0 and musiqa:
        # Musiqa fayli buzuq bo'lsa ham video chiqsin
        log.warning("Musiqa bilan yig'ilmadi, musiqasiz: %s", r.stderr[-800:])
        return _video_yig_musiqasiz(royxat, chiqish, davomiylik)
    if r.returncode != 0:
        raise RuntimeError(f"Video yig'ilmadi: {r.stderr[-800:]}")


def _video_yig_musiqasiz(royxat, chiqish, davomiylik):
    papka = os.path.dirname(royxat)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", os.path.basename(royxat),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
         "-preset", "veryfast", "-movflags", "+faststart", "-y", chiqish],
        capture_output=True, text=True, cwd=papka)
    if r.returncode != 0:
        raise RuntimeError(f"Video yig'ilmadi: {r.stderr[-800:]}")


def yasa(matn, fon_no, chiqish):
    """Bloklovchi ish — asyncio.to_thread orqali chaqiriladi."""
    papka = tempfile.mkdtemp(prefix="reels_")
    try:
        royxat, davomiylik = _kadrlarni_yoz(matn, fon_no, papka)
        _video_yig(royxat, chiqish, davomiylik)
        return davomiylik
    finally:
        shutil.rmtree(papka, ignore_errors=True)


# ======================================================================
# TELEGRAM
# ======================================================================
YORDAM = (
    "🎬 <b>Stories/Reels</b>\n\n"
    "Matnni yuboring — 1080x1920 tik video qilib beraman.\n\n"
    "<code>/reels Kitob o'qish miyani o'zgartiradi. "
    "Kuniga 20 daqiqa — yiliga 12 ta kitob.</code>\n\n"
    f"Matn {MAKS_BELGI} belgigacha. Qisqa matn kuchliroq chiqadi."
)


def _tugmalar(kalit):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎨 Boshqa fon", callback_data=f"rl_fon|{kalit}")],
        [InlineKeyboardButton("📤 Kanalga", callback_data=f"rl_ok|{kalit}"),
         InlineKeyboardButton("❌ Bekor", callback_data=f"rl_x|{kalit}")],
    ])


async def _yasab_yubor(context, chat_id, kalit, holat=None):
    ish = _ishlar.get(kalit)
    if not ish:
        return
    chiqish = os.path.join(tempfile.gettempdir(), f"reels_{kalit}.mp4")
    try:
        davomiylik = await asyncio.to_thread(
            yasa, ish["matn"], ish["fon"], chiqish)
    except Exception as e:
        log.exception("Reels yasalmadi")
        if holat:
            await holat.edit_text(f"Xato: {e}")
        else:
            await context.bot.send_message(chat_id, f"Xato: {e}")
        return
    try:
        with open(chiqish, "rb") as f:
            yuborilgan = await context.bot.send_video(
                chat_id, video=f, width=W, height=H,
                caption=f"🎬 {davomiylik:.0f} soniya · fon #{ish['fon'] + 1}",
                reply_markup=_tugmalar(kalit))
        if yuborilgan and yuborilgan.video:
            ish["file_id"] = yuborilgan.video.file_id
        if holat:
            await holat.delete()
    finally:
        if os.path.exists(chiqish):
            os.remove(chiqish)


async def _boshla(update, context, matn):
    if len(matn) > MAKS_BELGI:
        await update.message.reply_text(
            f"Matn {len(matn)} belgi — videoga sig'maydi.\n"
            f"{MAKS_BELGI} belgigacha qisqartiring.")
        return
    if not ffmpeg_bor():
        await update.message.reply_text(
            "ffmpeg topilmadi — server sozlanmagan (nixpacks.toml).")
        return

    kalit = f"rl{int(time.time())}{random.randint(10, 99)}"
    if len(_ishlar) > 40:            # eski qoralamalar to'planib qolmasin
        for eski in sorted(_ishlar)[:20]:
            _ishlar.pop(eski, None)
    _ishlar[kalit] = {"matn": matn, "fon": random.randrange(len(FONLAR)),
                      "chat": update.message.chat_id}
    holat = await update.message.reply_text("🎬 Video yasalmoqda...")
    await _yasab_yubor(context, update.message.chat_id, kalit, holat)


async def cmd_reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    matn = re.sub(r"^/reels(@\S+)?", "", update.message.text or "").strip()
    if not matn:
        context.user_data["reels_kutilyapti"] = True
        await update.message.reply_text(YORDAM, parse_mode="HTML")
        return
    context.user_data.pop("reels_kutilyapti", None)
    await _boshla(update, context, matn)


async def on_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reels dan keyingi matn. Bayroq qo'yilmagan bo'lsa — tegmaydi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    if not context.user_data.get("reels_kutilyapti"):
        return
    matn = (update.message.text or "").strip()
    if not matn:
        return
    context.user_data.pop("reels_kutilyapti", None)
    await _boshla(update, context, matn)


async def on_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Faqat admin uchun.", show_alert=True)
        return
    amal, kalit = q.data.split("|", 1)
    ish = _ishlar.get(kalit)
    if not ish:
        await q.answer("Bu video eskirgan — /reels bilan qaytadan boshlang.",
                       show_alert=True)
        return

    if amal == "rl_x":
        _ishlar.pop(kalit, None)
        await q.answer("Bekor qilindi")
        try:
            await q.delete_message()
        except Exception:
            pass
        return

    if amal == "rl_fon":
        ish["fon"] = (ish["fon"] + 1) % len(FONLAR)
        await q.answer(f"Fon #{ish['fon'] + 1}")
        try:
            await q.delete_message()
        except Exception:
            pass
        holat = await context.bot.send_message(ish["chat"],
                                               "🎨 Yangi fon bilan yasalmoqda...")
        await _yasab_yubor(context, ish["chat"], kalit, holat)
        return

    if amal == "rl_ok":
        if not ish.get("file_id"):
            await q.answer("Video topilmadi — qaytadan yasang.", show_alert=True)
            return
        await q.answer("Yuborilmoqda...")
        try:
            await context.bot.send_video(KANAL, video=ish["file_id"],
                                         width=W, height=H)
            await q.edit_message_caption(caption=f"✅ {KANAL} ga chiqdi")
        except Exception as e:
            log.warning("Reels kanalga chiqmadi: %s", e)
            await context.bot.send_message(ish["chat"], f"Chiqmadi: {e}")
        _ishlar.pop(kalit, None)


def register(app: Application):
    """bot.py dan: reels.register(app)"""
    if not ADMIN_ID:
        log.warning("ADMIN_ID yo'q — reels moduli o'chirilgan.")
        return
    if Image is None:
        log.warning("Pillow yo'q — reels moduli o'chirilgan.")
        return
    app.add_handler(CommandHandler("reels", cmd_reels))
    # DIQQAT: python-telegram-bot har GURUHDAN faqat BITTA mos ushlovchini
    # ishga tushiradi. Shuning uchun har modulning matn ushlovchisi o'z
    # guruhida bo'lishi shart — bir guruhda ikkitasi bo'lsa, ikkinchisi
    # hech qachon chaqirilmaydi. 1-guruh — iqtibos, 3-guruh — ustoz.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        on_matn), group=2)
    app.add_handler(CallbackQueryHandler(on_tugma, pattern=r"^rl_(fon|ok|x)\|"))
    log.info("Reels moduli yoqildi (kanal: %s, musiqa: %s)",
             KANAL, _musiqa_yoli() or "yo'q")
