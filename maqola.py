# -*- coding: utf-8 -*-
"""
maqola.py — OVOZDAN MAQOLA (faqat ADMIN uchun).

Siz fikringizni ovozli aytasiz — bot uni maqola qilib beradi. Bu
transkripsiya EMAS va oddiy "chiroyli qilib yozish" ham emas: matn
muharrir qo'lidan o'tgandek uch bosqichdan o'tadi.

    1. TAHLIL   — aytilganlar da'volarga ajratiladi va har biri
                  baholanadi: aniq / shubhali / xato. Manba aytilmagan
                  raqam, sana, ism, iqtibos avtomatik SHUBHALI bo'ladi.
    2. YOZISH   — maqola FAQAT "aniq" deb topilgan materialdan yoziladi.
                  Shubhali va xato da'volar matnga KIRMAYDI.
    3. MUHARRIR — tayyor matn qoidalar ro'yxati bo'yicha qayta o'qiladi
                  va tuzatiladi (kanalning uslub qoidalari agent.py dan).

Nega uch bosqich: bitta so'rovda "yoz va tekshir" desak, model o'zi
to'qigan raqamni o'zi tasdiqlaydi. Alohida tahlil bosqichi esa matn
yozilishidan OLDIN nimaga ishonish mumkinligini hal qiladi.

Siz maqola bilan birga MUHARRIR HISOBOTINI ham olasiz: nima olib
tashlandi, nima tasdiq kutyapti, nima yetishmayapti. Ya'ni bot sizning
o'rningizga qaror qilmaydi — nima qilganini ko'rsatadi.

ISHLATISH:
    /maqola            → keyin ovozli xabar (yoki matn) yuborasiz
    /maqola <matn>     → to'g'ridan-to'g'ri

bot.py:  import maqola  →  maqola.register(app)
"""

import asyncio
import json
import logging
import os
import random
import re
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, ApplicationHandlerStop, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

# Kanalning uslub qoidalari, rubrikalar, rasm va kanalga chiqarish —
# hammasi agent.py da tayyor. Qaytadan yozilsa, ikkisi vaqt o'tib
# bir-biridan uzoqlashadi va postlar har xil ohangda chiqadi.
import agent
from agent import (
    MODEL_SMART, MODEL_FAST, RUBRIKA_EMOJI, RUBRIKA_NOMI, _UMUMIY_QOIDALAR,
    ai_client, make_card_variant, stt_transcribe, tg_image_url,
    _send_to_channel,
)

log = logging.getLogger(__name__)

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
AISHA_API_KEY = os.environ.get("AISHA_API_KEY", "")
# Ovozdan matnga: Aisha o'zbek tiliga moslangan, Whisper — zaxira.
WHISPER_MODEL = os.environ.get("AI_MODEL_STT", "whisper-1")
# Maqola uzunligi (belgilarda). Telegram rich xabari 4096 gacha ko'taradi.
MAQOLA_MIN = int(os.environ.get("MAQOLA_MIN", "1100"))
MAQOLA_MAKS = int(os.environ.get("MAQOLA_MAKS", "2600"))

_ishlar = {}          # {kalit: {...}}


# ======================================================================
# 1-BOSQICH: TAHLIL — nimaga ishonish mumkin?
# ======================================================================
TAHLIL_PROMPT = """Sen o'zbek nashrining MAS'UL MUHARRIRISAN. Senga muallif \
og'zaki aytgan xom fikr beriladi (ovozdan matnga o'girilgan, shuning uchun \
tugallanmagan gaplar, takrorlar, "ha", "ya'ni" kabi to'ldiruvchilar bo'lishi \
mumkin).

VAZIFANG — MAQOLA YOZISH EMAS. Vazifang: aytilganlarni tekshirish va nimaga \
ishonish mumkinligini hal qilish. Maqolani boshqa bosqich yozadi.

Har bir da'voni baholaysan:
  "aniq"     — umum ma'lum haqiqat, mantiqiy fikr, muallifning O'Z tajribasi \
yoki o'z qarashi. Bularni tekshirib o'tirish shart emas.
  "shubhali" — tekshirilishi kerak. QAT'IY QOIDA: aniq raqam, foiz, sana, \
pul miqdori, ism, kompaniya nomi, iqtibos, "tadqiqot ko'rsatdi", "olimlar \
aniqladi", "statistikaga ko'ra" kabi ifodalar — muallif manbani aytmagan \
bo'lsa DOIM shubhali. Taxminan to'g'ri ko'rinsa ham shubhali.
  "xato"     — ochiq noto'g'ri, mantiqan zid yoki matnning boshqa joyiga \
qarama-qarshi.

MUHIM: sen faktni internetdan tekshira olmaysan. Shuning uchun "menimcha \
to'g'ri" deb "aniq" qo'yma — manba ko'rsatilmagan har qanday tekshiriladigan \
raqam yoki nom shubhali bo'ladi. Kam xato qilgandan ko'ra ko'proq shubhalan.

Shuningdek ayt: maqola foydali chiqishi uchun NIMA YETISHMAYAPTI (aniq savol \
shaklida, muallif javob bersa matn kuchayadi).

Rubrikalar: ai, smm, rivojlanish, mutolaa, podcast, dunyo, uzb, sport, \
texno, islom.

JAVOB — faqat JSON, izohsiz:
{"mavzu": "...",
 "asosiy_fikr": "bitta jumla — maqolaning o'zagi",
 "rubrika": "ro'yxatdan bittasi",
 "auditoriya_foydasi": "o'quvchi bu matndan nima olib chiqadi — bitta jumla",
 "dalillar": [{"dalil": "...", "holat": "aniq|shubhali|xato", "sabab": "..."}],
 "yetishmayapti": ["savol 1", "savol 2"],
 "ogohlantirish": ["diniy, siyosiy, tibbiy yoki moliyaviy xavf bo'lsa"]}

Muallif aytmagan fikrni "dalillar"ga QO'SHMA. Sen tekshiruvchisan, \
qo'shimcha muallif emas."""


def _json_ol(matn):
    """Model javobidan JSON ajratadi (ba'zan atrofida izoh bo'ladi)."""
    matn = (matn or "").strip()
    if matn.startswith("```"):
        matn = re.sub(r"^```[a-z]*\n?|\n?```$", "", matn).strip()
    try:
        return json.loads(matn)
    except Exception:
        m = re.search(r"\{.*\}", matn, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def tahlil_qil(xom):
    r = ai_client().chat.completions.create(
        model=MODEL_SMART,
        response_format={"type": "json_object"},
        max_completion_tokens=2000,
        messages=[{"role": "system", "content": TAHLIL_PROMPT},
                  {"role": "user", "content": xom}])
    data = _json_ol(r.choices[0].message.content)
    data.setdefault("dalillar", [])
    data.setdefault("yetishmayapti", [])
    data.setdefault("ogohlantirish", [])
    rub = (data.get("rubrika") or "").strip().lower()
    data["rubrika"] = rub if rub in RUBRIKA_NOMI else "rivojlanish"
    return data


def _dalillar(tahlil, holat):
    return [d.get("dalil", "").strip()
            for d in tahlil.get("dalillar", [])
            if (d.get("holat") or "").lower() == holat and d.get("dalil")]


# ======================================================================
# 2-BOSQICH: MAQOLA YOZISH
# ======================================================================
MAQOLA_PROMPT = """Sen @safaroov_blog Telegram kanalining muharririsan. \
Kanal tili: o'zbek. Ohang: professional, jonli, "siz"lab. Auditoriya: \
O'zbekistondagi marketologlar, kichik biznes egalari, o'z ustida \
ishlaydigan yoshlar.

Muallif fikrini og'zaki aytdi. Senga xom matn va uning MUHARRIR TAHLILI \
beriladi. Sen shulardan tugallangan MAQOLA yozasan.

""" + _UMUMIY_QOIDALAR + """

MAQOLA UCHUN QO'SHIMCHA QOIDALAR (yuqoridagilardan ustun turadi):

M1. UZUNLIK: {min}-{maks} belgi. Bu post emas, maqola — fikr ochib \
berilsin. Lekin suv quyish TAQIQ: har xatboshi yangi narsa aytsin.

M2. FAQAT "aniq" deb belgilangan materialdan yoz. "shubhali" va "xato" \
da'volar matnga KIRMASIN — ularni yumshatib ham, "ba'zi ma'lumotlarga ko'ra" \
deb ham yozma. Ular butunlay tushib qoladi.

M3. O'ZINGDAN FAKT QO'SHMA. Yangi raqam, sana, ism, tadqiqot, iqtibos \
o'ylab topish — eng og'ir xato. Muallif aytmagan misolni "masalan" deb \
kiritma. Fikrni kengaytirish mumkin, DALIL to'qish mumkin emas.

M4. TUZILISH:
    Sarlavha — bitta qator, o'ziga tortadigan, lekin sensatsiyasiz.
    Kirish — 2-3 gap: o'quvchi nega bu matnni o'qishi kerak.
    2-4 ta bo'lim — har birida qalin sarlavha (**shunday**) va 1-2 xatboshi.
    Xulosa — o'quvchi ertaga qila oladigan ANIQ qadam.
    Savol — o'quvchiga qaratilgan bitta jonli savol.

M5. Og'zaki nutq izlari yo'qolsin: "ha", "ya'ni", "shundaymi", takror \
gaplar, o'ylab turish. Lekin muallifning O'Z ohangi va o'z misollari \
saqlanadi — matn begona bo'lib qolmasin.

M6. Muallif aytgan fikr zaif yoki noaniq bo'lsa — uni kuchaytirib \
ko'rsatma. Bor holicha, halol yoz.

M7. Oxirgi qatorda hashtag va kanal: "#{teg} · @safaroov_blog"

JAVOB — faqat maqola matni. Izoh, sarlavha belgisi (#), tirnoq yoki \
"mana maqola" kabi so'z YO'Q."""


def maqola_yoz(xom, tahlil):
    aniq = _dalillar(tahlil, "aniq")
    tashlangan = _dalillar(tahlil, "shubhali") + _dalillar(tahlil, "xato")
    teg = tahlil["rubrika"]
    kirish = [
        f"MAVZU: {tahlil.get('mavzu', '')}",
        f"ASOSIY FIKR: {tahlil.get('asosiy_fikr', '')}",
        f"O'QUVCHI FOYDASI: {tahlil.get('auditoriya_foydasi', '')}",
        "",
        "ISHLATISH MUMKIN BO'LGAN MATERIAL:",
        *(f"- {d}" for d in aniq),
    ]
    if tashlangan:
        kirish += ["", "MATNGA KIRITILMAYDI (tekshirilmagan yoki xato):",
                   *(f"- {d}" for d in tashlangan)]
    kirish += ["", "MUALLIFNING XOM MATNI (ohang va misollar uchun):", xom]

    r = ai_client().chat.completions.create(
        model=MODEL_SMART,
        max_completion_tokens=3000,
        messages=[
            {"role": "system",
             "content": MAQOLA_PROMPT.format(
                 min=MAQOLA_MIN, maks=MAQOLA_MAKS, teg=teg)},
            {"role": "user", "content": "\n".join(kirish)}])
    return (r.choices[0].message.content or "").strip()


# ======================================================================
# 3-BOSQICH: MUHARRIR TEKSHIRUVI
# ======================================================================
MUHARRIR_PROMPT = """Sen o'zbek nashrining BOSH MUHARRIRISAN. Senga \
hamkasbing yozgan maqola beriladi. Uni chop etishdan oldin oxirgi marta \
o'qib chiqasan va TUZATASAN.

Tekshiruv ro'yxati:
1. Idoraviy-quruq iboralar: "ushbu", "mazkur", "hisoblanadi", "amalga \
oshirmoqda", "e'tibor qaratmoq", "...bo'yicha", "...tomonidan" — hammasi \
olib tashlanadi yoki jonli muqobil bilan almashtiriladi.
2. Bir jumlada ikkita "uchun" yoki ikkita "ushbu" qolmasin.
3. Majhul nisbat ketma-ket kelmasin ("qilindi... etildi... berildi").
4. Ruscha-inglizcha kalka: "yangradi", "issiq to'lqinlar", "zarurligini \
anglatadi" — o'zbekchaga o'giriladi.
5. Uzun jumlalar bo'linadi (o'rtacha 8-14 so'z).
6. Bo'sh, hech narsa aytmaydigan jumlalar o'chiriladi ("bu juda muhim \
masala", "har bir inson buni bilishi kerak").
7. Xatboshilar 2-3 gapdan oshmasin.
8. Sarlavha matnga mos va aniqmi.
9. Xulosada ANIQ, bajarib bo'ladigan qadam bormi — bo'lmasa qo'sh (lekin \
yangi FAKT qo'shma).
10. Ohang hurmatli. Diniy va siyosiy mavzuda betaraf.

QAT'IY: yangi fakt, raqam, ism yoki iqtibos QO'SHMAYSAN. Sen faqat \
mavjud matnni tozalaysan va ravonlashtirasan. Maqola uzunligi \
{min}-{maks} belgi oralig'ida qolsin.

JAVOB — faqat JSON:
{{"maqola": "tuzatilgan to'liq matn",
  "tuzatildi": ["nima o'zgardi — qisqa, 5 tagacha"]}}"""


def muharrir_oqi(matn):
    r = ai_client().chat.completions.create(
        model=MODEL_SMART,
        response_format={"type": "json_object"},
        max_completion_tokens=3000,
        messages=[{"role": "system",
                   "content": MUHARRIR_PROMPT.format(
                       min=MAQOLA_MIN, maks=MAQOLA_MAKS)},
                  {"role": "user", "content": matn}])
    data = _json_ol(r.choices[0].message.content)
    yangi = (data.get("maqola") or "").strip()
    # Muharrir matnni buzib qo'ysa — asl variant qoladi
    if len(yangi) < MAQOLA_MIN * 0.5:
        return matn, []
    return yangi, (data.get("tuzatildi") or [])[:5]


# ======================================================================
# TAHRIR: admin izohi bo'yicha qayta yozish
# ======================================================================
TAHRIR_PROMPT = """Sen @safaroov_blog kanalining muharririsan. Quyida \
tayyor maqola va MUALLIFNING KO'RSATMASI berilgan. Maqolani ko'rsatma \
bo'yicha qayta yoz.

Muallif bergan yangi ma'lumot ISHONCHLI hisoblanadi — uni matnga kirit. \
Lekin o'zingdan yangi fakt qo'shma. Uslub, tuzilish va uzunlik o'sha-o'sha \
qoladi ({min}-{maks} belgi).

JAVOB — faqat maqola matni."""


def tahrir_qil(matn, korsatma):
    r = ai_client().chat.completions.create(
        model=MODEL_SMART,
        max_completion_tokens=3000,
        messages=[{"role": "system",
                   "content": TAHRIR_PROMPT.format(
                       min=MAQOLA_MIN, maks=MAQOLA_MAKS)},
                  {"role": "user",
                   "content": f"MAQOLA:\n{matn}\n\nMUALLIF KO'RSATMASI:\n{korsatma}"}])
    return (r.choices[0].message.content or "").strip()


# ======================================================================
# OVOZDAN MATNGA
# ======================================================================
def _whisper(audio_bytes, nom="voice.ogg"):
    """Zaxira: Aisha ishlamasa OpenAI Whisper."""
    from io import BytesIO
    fayl = BytesIO(audio_bytes)
    fayl.name = nom
    r = ai_client().audio.transcriptions.create(
        model=WHISPER_MODEL, file=fayl, language="uz")
    return (getattr(r, "text", "") or "").strip()


async def ovozdan_matn(audio_bytes, nom="voice.ogg"):
    """Aisha birinchi (o'zbek tiliga moslangan), Whisper zaxira."""
    if AISHA_API_KEY:
        try:
            matn = await stt_transcribe(audio_bytes, nom)
            if matn:
                return matn, "Aisha"
        except Exception as e:
            log.warning("Aisha STT ishlamadi, Whisper'ga o'tildi: %s", e)
    matn = await asyncio.to_thread(_whisper, audio_bytes, nom)
    return matn, "Whisper"


# ======================================================================
# HISOBOT VA TUGMALAR
# ======================================================================
def _hisobot(tahlil, tuzatildi):
    """Bot nima qilganini ochiq ko'rsatadi — qaror baribir sizniki."""
    q = ["🧾 <b>Muharrir hisoboti</b>"]
    xato = _dalillar(tahlil, "xato")
    shubha = [d for d in tahlil.get("dalillar", [])
              if (d.get("holat") or "").lower() == "shubhali"]
    if xato:
        q.append("\n❌ <b>Olib tashlandi (xato):</b>")
        q += [f"• {d}" for d in xato]
    if shubha:
        q.append("\n⚠️ <b>Tasdiq kutyapti</b> — manba aytilmagani uchun "
                 "matnga kirmadi:")
        for d in shubha[:6]:
            sabab = d.get("sabab", "")
            q.append(f"• {d.get('dalil', '')}" + (f"\n   <i>{sabab}</i>"
                                                  if sabab else ""))
    yetishmayapti = tahlil.get("yetishmayapti") or []
    if yetishmayapti:
        q.append("\n❓ <b>Shuni qo'shsangiz, kuchliroq bo'ladi:</b>")
        q += [f"• {s}" for s in yetishmayapti[:4]]
    if tahlil.get("ogohlantirish"):
        q.append("\n🔺 <b>Diqqat:</b>")
        q += [f"• {s}" for s in tahlil["ogohlantirish"][:3]]
    if tuzatildi:
        q.append("\n✍️ <b>Tahrirda tuzatildi:</b>")
        q += [f"• {s}" for s in tuzatildi]
    if len(q) == 1:
        q.append("\nHammasi joyida — tuzatish talab qilinmadi.")
    q.append("\n💡 Tasdiq kutayotgan ma'lumotni qo'shish uchun "
             "«✍️ Tahrir» tugmasini bosing va manbasi bilan ayting.")
    return "\n".join(q)


def _tugmalar(kalit, rasm_bormi):
    qatorlar = [[InlineKeyboardButton(
        "🖼 Rasm bilan" if not rasm_bormi else "🔄 Boshqa rasm",
        callback_data=f"mq_rasm|{kalit}")]]
    qatorlar.append([
        InlineKeyboardButton("✍️ Tahrir", callback_data=f"mq_tahrir|{kalit}"),
        InlineKeyboardButton("♻️ Qayta yoz", callback_data=f"mq_qayta|{kalit}"),
    ])
    qatorlar.append([
        InlineKeyboardButton("📤 Kanalga", callback_data=f"mq_pub|{kalit}"),
        InlineKeyboardButton("❌ Bekor", callback_data=f"mq_x|{kalit}"),
    ])
    return InlineKeyboardMarkup(qatorlar)


async def _korsat(context, chat_id, kalit, hisobot=True):
    ish = _ishlar.get(kalit)
    if not ish:
        return
    matn = ish["maqola"]
    bosh = (f"{RUBRIKA_EMOJI.get(ish['rubrika'], '📝')} "
            f"<b>{RUBRIKA_NOMI.get(ish['rubrika'], 'Maqola')}</b> · "
            f"{len(matn)} belgi\n\n")
    await context.bot.send_message(
        chat_id, bosh + _html_himoya(matn), parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=_tugmalar(kalit, bool(ish.get("rasm"))))
    if hisobot:
        await context.bot.send_message(
            chat_id, _hisobot(ish["tahlil"], ish.get("tuzatildi") or []),
            parse_mode="HTML")


def _html_himoya(matn):
    """Maqolada ** bilan berilgan bo'lim sarlavhalarini HTML'ga o'giradi."""
    matn = (matn.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", matn)


# ======================================================================
# ASOSIY OQIM
# ======================================================================
async def _quvur(context, chat_id, xom, holat=None):
    """Xom matn → tahlil → maqola → muharrir → ko'rsatish."""
    async def yoz(t):
        if holat:
            try:
                await holat.edit_text(t)
            except Exception:
                pass

    await yoz("🔍 Aytganlaringiz tekshirilyapti...")
    tahlil = await asyncio.to_thread(tahlil_qil, xom)

    aniq = len(_dalillar(tahlil, "aniq"))
    tashlandi = len(_dalillar(tahlil, "shubhali")) + len(_dalillar(tahlil, "xato"))
    await yoz(f"✍️ Maqola yozilyapti "
              f"({aniq} ta dalil ishlatiladi, {tashlandi} tasi tashlandi)...")
    matn = await asyncio.to_thread(maqola_yoz, xom, tahlil)
    if not matn:
        await yoz("Maqola chiqmadi — qaytadan urinib ko'ring.")
        return None

    await yoz("📖 Bosh muharrir o'qiyapti...")
    matn, tuzatildi = await asyncio.to_thread(muharrir_oqi, matn)

    kalit = f"mq{int(time.time())}{random.randint(10, 99)}"
    if len(_ishlar) > 30:
        for eski in sorted(_ishlar)[:15]:
            _ishlar.pop(eski, None)
    _ishlar[kalit] = {"xom": xom, "tahlil": tahlil, "maqola": matn,
                      "tuzatildi": tuzatildi, "rubrika": tahlil["rubrika"],
                      "chat": chat_id, "rasm": None, "variant": 0}
    if holat:
        try:
            await holat.delete()
        except Exception:
            pass
    await _korsat(context, chat_id, kalit)
    return kalit


YORDAM = (
    "📝 <b>Ovozdan maqola</b>\n\n"
    "Fikringizni ovozli xabarda ayting — bot uni maqola qilib beradi.\n\n"
    "Bu oddiy yozib olish emas:\n"
    "• aytilganlar da'volarga ajratiladi va tekshiriladi\n"
    "• manbasiz raqam, sana, ism, iqtibos matnga kiritilmaydi\n"
    "• matn kanal uslubi bo'yicha muharrir tekshiruvidan o'tadi\n"
    "• nima olib tashlangani sizga alohida ko'rsatiladi\n\n"
    "Erkin gapiravering — tugallanmagan gap, takror, o'ylab turish "
    "muammo emas. Raqam yoki tadqiqot aytsangiz, manbasini ham ayting: "
    "shunda matnga kiradi.\n\n"
    "Matn bilan ishlatish: <code>/maqola fikringiz...</code>"
)


async def cmd_maqola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    xom = re.sub(r"^/maqola(@\S+)?", "", update.message.text or "").strip()
    if not xom:
        context.user_data["maqola_kutilyapti"] = True
        await update.message.reply_text(YORDAM, parse_mode="HTML")
        return
    context.user_data.pop("maqola_kutilyapti", None)
    holat = await update.message.reply_text("🔍 Tekshirilyapti...")
    await _quvur(context, update.message.chat_id, xom, holat)


async def on_ovoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/maqola dan keyingi ovozli xabar.

    Bayroq qo'yilmagan bo'lsa hech narsa qilmaydi — ovoz agent.py dagi
    ovozli yordamchiga o'tib ketadi. Bayroq bor bo'lsa xabarni shu modul
    OLADI va ApplicationHandlerStop bilan boshqa ushlovchilarni to'xtatadi,
    aks holda agent uni savol deb javob bergan bo'lardi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    if not context.user_data.get("maqola_kutilyapti"):
        return
    context.user_data.pop("maqola_kutilyapti", None)

    holat = await update.message.reply_text("🎧 Eshityapman...")
    try:
        ovoz = update.message.voice or update.message.audio
        tg_file = await ovoz.get_file()
        audio = bytes(await tg_file.download_as_bytearray())
        xom, manba = await ovozdan_matn(audio)
        if not xom:
            await holat.edit_text(
                "Ovozdan matn chiqmadi — yaqinroqdan, ravshanroq gapiring.")
            raise ApplicationHandlerStop
        await update.message.reply_text(
            f"🗣 <b>Eshitilgan matn</b> ({manba}, {len(xom)} belgi):\n\n"
            f"<i>{_html_himoya(xom)[:3000]}</i>", parse_mode="HTML")
        await _quvur(context, update.message.chat_id, xom, holat)
    except ApplicationHandlerStop:
        raise
    except Exception as e:
        log.exception("Ovozdan maqola xatosi")
        try:
            await holat.edit_text(f"Xato: {e}")
        except Exception:
            pass
    raise ApplicationHandlerStop


async def on_matn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/maqola dan keyingi matn yoki «Tahrir» ko'rsatmasi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    matn = (update.message.text or "").strip()
    if not matn:
        return

    kalit = context.user_data.get("maqola_tahrir")
    if kalit:
        context.user_data.pop("maqola_tahrir", None)
        ish = _ishlar.get(kalit)
        if not ish:
            await update.message.reply_text("Bu maqola eskirgan — /maqola.")
            return
        holat = await update.message.reply_text("✍️ Tahrir qilinyapti...")
        yangi = await asyncio.to_thread(tahrir_qil, ish["maqola"], matn)
        if yangi:
            ish["maqola"] = yangi
            ish["tuzatildi"] = ["Muallif ko'rsatmasi bo'yicha qayta yozildi"]
        try:
            await holat.delete()
        except Exception:
            pass
        await _korsat(context, ish["chat"], kalit, hisobot=False)
        return

    if not context.user_data.get("maqola_kutilyapti"):
        return
    context.user_data.pop("maqola_kutilyapti", None)
    holat = await update.message.reply_text("🔍 Tekshirilyapti...")
    await _quvur(context, update.message.chat_id, matn, holat)


# ======================================================================
# TUGMALAR
# ======================================================================
async def on_tugma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Faqat admin uchun.", show_alert=True)
        return
    amal, kalit = q.data.split("|", 1)
    ish = _ishlar.get(kalit)
    if not ish:
        await q.answer("Bu maqola eskirgan — /maqola bilan qaytadan boshlang.",
                       show_alert=True)
        return

    if amal == "mq_x":
        _ishlar.pop(kalit, None)
        await q.answer("Bekor qilindi")
        try:
            await q.delete_message()
        except Exception:
            pass
        return

    if amal == "mq_tahrir":
        context.user_data["maqola_tahrir"] = kalit
        await q.answer()
        await context.bot.send_message(
            ish["chat"],
            "✍️ Nimani o'zgartiray? Yozing.\n\n"
            "Tasdiq kutayotgan ma'lumotni qo'shmoqchi bo'lsangiz — manbasi "
            "bilan ayting, o'shanda matnga kiradi.")
        return

    if amal == "mq_qayta":
        await q.answer("Qaytadan yozilyapti...")
        holat = await context.bot.send_message(ish["chat"], "♻️ Qayta yozilyapti...")
        matn = await asyncio.to_thread(maqola_yoz, ish["xom"], ish["tahlil"])
        if matn:
            matn, tuzatildi = await asyncio.to_thread(muharrir_oqi, matn)
            ish["maqola"], ish["tuzatildi"] = matn, tuzatildi
        try:
            await holat.delete()
        except Exception:
            pass
        await _korsat(context, ish["chat"], kalit, hisobot=False)
        return

    if amal == "mq_rasm":
        await q.answer("Rasm tayyorlanyapti...")
        holat = await context.bot.send_message(ish["chat"], "🖼 Rasm yasalyapti...")
        try:
            variant = ish["variant"]
            rasm = await make_card_variant(kalit, ish["maqola"],
                                           ish["rubrika"], variant)
            ish["variant"] = (variant + 1) % agent.CARD_VARIANTS
            if not rasm:
                await holat.edit_text("Rasm chiqmadi — matn holicha qoladi.")
                return
            ish["rasm"] = rasm
            await holat.delete()
            await context.bot.send_photo(
                ish["chat"], photo=rasm,
                caption=f"Variant {variant + 1}/{agent.CARD_VARIANTS}",
                reply_markup=_tugmalar(kalit, True))
        except Exception as e:
            log.warning("Maqola rasmi chiqmadi: %s", e)
            try:
                await holat.edit_text(f"Rasm chiqmadi: {e}")
            except Exception:
                pass
        return

    if amal == "mq_pub":
        await q.answer("Chiqarilyapti...")
        try:
            rasm_url = None
            if ish.get("rasm"):
                # Rich (maqola) formatida rasm HTTPS havola bo'lishi kerak
                try:
                    rasm_url = await tg_image_url(context, ish["rasm"])
                except Exception as e:
                    log.warning("Rasm havolasi olinmadi: %s", e)
            await _send_to_channel(context, ish["maqola"],
                                   image_bytes=ish.get("rasm"),
                                   rubrika=ish["rubrika"],
                                   image_url=rasm_url)
            await context.bot.send_message(
                ish["chat"], f"✅ Kanalga chiqdi ({RUBRIKA_NOMI[ish['rubrika']]})")
            _ishlar.pop(kalit, None)
        except Exception as e:
            log.exception("Maqola kanalga chiqmadi")
            await context.bot.send_message(ish["chat"], f"Chiqmadi: {e}")
        return


def register(app: Application):
    """bot.py dan: maqola.register(app)"""
    if not ADMIN_ID:
        log.warning("ADMIN_ID yo'q — maqola moduli o'chirilgan.")
        return
    app.add_handler(CommandHandler("maqola", cmd_maqola))
    # Ovoz -3 guruhda: agent.py dagi ovozli yordamchidan (0-guruh) OLDIN
    # ko'riladi. Bayroq bo'lmasa tegmaydi, bo'lsa ApplicationHandlerStop
    # bilan to'xtatadi.
    app.add_handler(MessageHandler(
        (filters.VOICE | filters.AUDIO) & filters.User(user_id=ADMIN_ID),
        on_ovoz), group=-3)
    # Matn 4-guruhda: har modulning matn ushlovchisi o'z guruhida bo'lishi
    # shart (PTB bir guruhdan faqat bittasini chaqiradi).
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        on_matn), group=4)
    app.add_handler(CallbackQueryHandler(
        on_tugma, pattern=r"^mq_(rasm|tahrir|qayta|pub|x)\|"))
    log.info("Maqola moduli yoqildi (STT: %s)",
             "Aisha + Whisper" if AISHA_API_KEY else "Whisper")
