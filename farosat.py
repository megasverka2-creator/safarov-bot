# -*- coding: utf-8 -*-
"""
farosat.py — @farosatdaan kanali uchun kontent-agent.

Kanalning haqiqiy eksportidan o'rganilgan uslub asosida ORIGINAL bir jumlalik
"farosat kuzatuvlari" yaratadi. Hech qanday iqtibos, atribusiya yoki diniy
mazmun YO'Q — bular admin tomonidan qo'lda yoziladi.

Oqim: /farosat → 5 ta nomzod → raqam bosiladi → kanalga chiqadi.
Sozlash: FAROSAT_CHANNEL env (standart @farosatdaan).
bot.py:  import farosat  →  farosat.register(app)
"""

import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

log = logging.getLogger("farosat")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
FAROSAT_CHANNEL = os.environ.get("FAROSAT_CHANNEL", "@farosatdaan")
MODEL = os.environ.get("AI_MODEL_SMART", "gpt-5.6-luna")

_ai = None
def ai_client():
    global _ai
    if _ai is None:
        from openai import OpenAI
        _ai = OpenAI()
    return _ai


# Kanalning haqiqiy postlaridan olingan uslub namunalari (eksportdan)
STYLE_PROMPT = """Sen "Farosatdan" (@farosatdaan) Telegram kanalining muallifisan. \
Kanal formati: kundalik hayotdagi farosat (odob, did, aql-idrok) haqidagi BIR \
JUMLALIK o'tkir kuzatuvlar. Har post "@farosatdaan" bilan tugaydi — bu imzo \
gapning tabiiy davomi bo'lib o'qiladi (go'yo "farosat" so'zining o'rnida).

KANALNING HAQIQIY POSTLARIDAN NAMUNALAR (uslubni aynan shundan ol):
• Har bir ishingiz va so'zingiz oqibatini o'ylash @farosatdaan
• Kitobga chizmaslik @farosatdaan
• Bo'lar bo'lmas narsaga kulavermaslik @farosatdaan
• Liftni chaqirgandan so'ng to u kelguncha chaqirish tugmasini yana 5-6 martalab bosib tashlamaslik @farosatdaan
• Hamma narsaniyam chatGPTdan so'rayvermaslik @farosatdaan
• Karta raqam so'rasa kartani rasmini tashlamaslik ham @farosatdaan
• Kitobni olgandan keyin uni so'ramasa ham vaqtida qaytarib berishlik @farosatdaan

QAT'IY QOIDALAR:
1. Har kuzatuv — bitta jumla, "-lik/-maslik" shaklida tugaydi, oxirida @farosatdaan.
2. Mavzular: zamonaviy kundalik hayot — telefon, transport, mehmondorchilik, \
ish, xabar yozish odobi, jamoat joylari, ijtimoiy tarmoq, navbat, qo'shnichilik.
3. FAQAT ORIGINAL fikrlar. Hech kimdan iqtibos keltirma, hech kimga so'z \
nisbat berma ("falonchi aytgan" TAQIQ).
4. Diniy mavzularga KIRMA (duo, ibodat, oyat-hadis yo'q) — bu postlarni \
muallif o'zi yozadi.
5. Emoji ishlatma. Chiroyli so'z emas, hayotiy aniqlik qadrlanadi — o'quvchi \
"voy, bu men-ku" deb kulsin yoki o'ylanib qolsin.
6. Bir-biriga o'xshamagan 5 xil vaziyat bo'lsin.

FAQAT 5 ta kuzatuvni qaytar, har biri yangi qatorda, raqamsiz, izohsiz."""


def _gen_candidates():
    resp = ai_client().chat.completions.create(
        model=MODEL, max_completion_tokens=500,
        messages=[{"role": "user", "content": STYLE_PROMPT}])
    lines = [l.strip().lstrip("•-–1234567890. ")
             for l in resp.choices[0].message.content.strip().splitlines()]
    out = []
    for l in lines:
        if len(l) > 15:
            if "@farosatdaan" not in l:
                l = l.rstrip(".") + " @farosatdaan"
            out.append(l)
    return out[:5]


def _kb(n):
    row = [InlineKeyboardButton(str(i + 1), callback_data=f"fr_pub:{i}")
           for i in range(n)]
    return InlineKeyboardMarkup([row,
        [InlineKeyboardButton("🔄 Yana 5 ta", callback_data="fr_more:0")]])


async def cmd_farosat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("🧠 Farosat kuzatuvlari tayyorlanmoqda...")
    await _send_batch(update.effective_chat.id, context)


async def _send_batch(chat_id, context):
    try:
        cands = _gen_candidates()
    except Exception as e:
        log.exception("Farosat xatosi: %s", e)
        await context.bot.send_message(chat_id, f"Xatolik: {e}")
        return
    if not cands:
        await context.bot.send_message(chat_id, "Nomzod chiqmadi, qayta urinib ko'ring.")
        return
    context.user_data["farosat"] = cands
    body = "\n\n".join(f"{i+1}. {c}" for i, c in enumerate(cands))
    await context.bot.send_message(
        chat_id,
        f"🧠 Farosat nomzodlari ({FAROSAT_CHANNEL}):\n\n{body}\n\n"
        f"👇 Yoqqanining raqamini bosing — kanalga chiqadi.",
        reply_markup=_kb(len(cands)))


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Faqat admin uchun.", show_alert=True)
        return
    if q.data.startswith("fr_more"):
        await q.answer("Tayyorlanmoqda...")
        await _send_batch(q.message.chat_id, context)
        return
    idx = int(q.data.split(":")[1])
    cands = context.user_data.get("farosat") or []
    if idx >= len(cands):
        await q.answer("Eskirgan ro'yxat — /farosat bilan yangilang.", show_alert=True)
        return
    text = cands[idx]
    try:
        await context.bot.send_message(chat_id=FAROSAT_CHANNEL, text=text)
        await q.answer(f"{FAROSAT_CHANNEL} ga chiqdi! ✅")
        await context.bot.send_message(q.message.chat_id, f"✅ Chiqdi:\n\n{text}")
    except Exception as e:
        await q.answer(f"Xato: {e}", show_alert=True)


def register(app):
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY yo'q — farosat-agent o'chirilgan.")
        return
    app.add_handler(CommandHandler("farosat", cmd_farosat))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^fr_"))
    log.info("Farosat-agent ulandi: %s", FAROSAT_CHANNEL)
