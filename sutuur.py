# -*- coding: utf-8 -*-
"""
sutuur.py — @Sutuur_uz kanali uchun adabiy kontent-agent.

Ikki rejim:
  ✍️  Satr — kanal uslubidagi qisqa lirik mushohadalar (original)
  📖 Adabiyot — jahon/o'zbek/arab/turk adabiyoti haqida mini-hikoyalar
     (adib portreti, asar tarixi, adabiy tushuncha — O'Z SO'ZI bilan)

Qat'iy chegaralar: iqtibos to'qilmaydi, asardan parcha ko'chirilmaydi,
diniy hukm-mazmun yozilmaydi (muallifning o'zi yozadi).

Sozlash: SUTUUR_CHANNEL env (standart @Sutuur_uz).
bot.py:  import sutuur  →  sutuur.register(app)
"""

import logging
import os
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

log = logging.getLogger("sutuur")

ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
SUTUUR_CHANNEL = os.environ.get("SUTUUR_CHANNEL", "@Sutuur_uz")
MODEL = os.environ.get("AI_MODEL_SMART", "gpt-5.6-luna")

_ai = None
def ai_client():
    global _ai
    if _ai is None:
        from openai import OpenAI
        _ai = OpenAI()
    return _ai


_UMUMIY = """QAT'IY TAQIQLAR (buzish mumkin emas):
- Hech kimga so'z NISBAT BERMA: "falonchi aytgan/yozgan" ko'rinishidagi \
iqtiboslar TAQIQ — chunki xato nisbat kanal obro'sini o'ldiradi.
- Asarlardan to'g'ridan-to'g'ri parcha, she'r satri, qo'shiq matni KELTIRMA — \
mazmunni faqat o'z so'zing bilan ayt.
- Diniy hukm, oyat-hadis mazmuni, ibodat mavzulariga KIRMA — bu postlarni \
muallif o'zi yozadi. (Umuminsoniy ma'naviy ohang mumkin, diniy manba emas.)
- Aniq ishonching komil bo'lmagan sana, raqam, faktni YOZMA."""

SATR_PROMPT = """Sen "Sutuur | Satrlar" (@Sutuur_uz) kanalining muallifisan. \
Kanal — shaxsiy adabiy kundalik: yurakdan chiqqan qisqa satrlar, hayot va \
inson holati haqidagi samimiy mushohadalar.

KANALNING HAQIQIY POSTLARIDAN NAMUNALAR (ohangni aynan shundan ol):
▸ Biz o'zi beg'ubor tug'ilamiz. Keyin hozirgi holatimizga kelamiz.
▸ O'zingni buncha qiynama, oddiyroq bo'laver!
▸ Ranjimasin.
▸ — Rostgo'y bo'ling.
— Sodiq bo'ling.
— Samimiy bo'ling.

USLUB: birinchi shaxsdan yoki o'quvchiga do'stona murojaat; 1-3 jumla; ba'zan \
bitta so'z ham post bo'la oladi; ohang — yumshoq, o'ychan, ozgina sog'inchli; \
emoji juda kam (ko'pi bilan bitta, ko'pincha yo'q); pand-nasihat emas — his.

""" + _UMUMIY + """

5 ta har xil kayfiyatdagi ORIGINAL satr yoz. Har birini yangi qatorda, \
raqamsiz, "###" belgisi bilan ajratib qaytar. Izoh yozma."""

ADAB_PROMPT = """Sen "Sutuur | Satrlar" (@Sutuur_uz) kanalining adabiy \
hikoyachisisan. Kanal auditoriyasi adabiyotni sevadi: o'zbek, jahon, arab, \
turk adabiyoti — hammasi qiziq.

Vazifang: {mavzu} haqida BITTA qisqa, iliq mini-hikoya yozish (400-700 belgi). \
Bu ma'ruza emas — do'stingga kechki suhbatda aytib beradigan hikoya: nega bu \
adib/asar/hodisa qalbga yaqin, qanday taqdir yoki g'oya yotibdi zamirida.

USLUB: samimiy, birinchi shaxs ohangi mumkin ("o'qiganimda...", "meni hayron \
qoldirgani..."); sodda o'zbek tili; oxirida o'quvchini o'ylantiradigan yoki \
kitobga chorlaydigan bitta yumshoq gap.

""" + _UMUMIY + """

FAQAT tayyor post matnini qaytar, sarlavhasiz, izohsiz."""

# Adabiyot mavzulari g'ildiragi — har safar boshqa yo'nalish
ADAB_MAVZULAR = [
    "o'zbek mumtoz adabiyotidagi biror buyuk siymo (Navoiy, Bobur, Ogahiy kabi) hayotidan bir ibratli lavha",
    "XX asr o'zbek adabiyotining biror yorqin vakili (Qodiriy, Cho'lpon, G'afur G'ulom, O'tkir Hoshimov kabi) taqdiri va ijodi",
    "jahon adabiyotining mashhur asari — uning yaratilish tarixi yoki bosh g'oyasi (o'z so'zing bilan)",
    "arab adabiyotining buyuk namoyandasi yoki asari (Naguib Mahfuz, Jubron Xalil Jubron, ming bir kecha an'anasi kabi)",
    "turk adabiyotining sevimli adibi yoki asari (O'rxon Pamuk, Aziz Nesin, Rashod Nuri kabi)",
    "rus yoki yevropa klassikasidan bir adib taqdiri (Dostoyevskiy, Chexov, Kafka, Ekzyuperi kabi)",
    "adabiy tushuncha yoki janr tarixi (masalan g'azal, hikoya, roman, ruboiy) — sodda va qiziqarli qilib",
    "kitobxonlik madaniyati haqida o'ylantiradigan mushohada — adabiyot insonga nima beradi",
]


def _gen(prompt):
    resp = ai_client().chat.completions.create(
        model=MODEL, max_completion_tokens=900,
        messages=[{"role": "user", "content": prompt}])
    return resp.choices[0].message.content.strip()


def _menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Satrlar (5 ta)", callback_data="st_satr:0"),
         InlineKeyboardButton("📖 Adabiyot hikoyasi", callback_data="st_adab:0")],
    ])

def _pub_kb(n, mode):
    row = [InlineKeyboardButton(str(i + 1), callback_data=f"st_pub:{i}")
           for i in range(n)]
    return InlineKeyboardMarkup([row,
        [InlineKeyboardButton("🔄 Yana", callback_data=f"st_{mode}:0")]])


async def cmd_sutuur(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"📖 Sutuur-agent ({SUTUUR_CHANNEL}).\nNima tayyorlay?",
        reply_markup=_menu_kb())


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Faqat admin uchun.", show_alert=True)
        return

    if q.data.startswith("st_satr"):
        await q.answer("Satrlar yozilmoqda... ✍️")
        try:
            raw = _gen(SATR_PROMPT)
        except Exception as e:
            await context.bot.send_message(q.message.chat_id, f"Xatolik: {e}")
            return
        cands = [c.strip() for c in raw.split("###") if len(c.strip()) > 3][:5]
        if not cands:
            cands = [l.strip() for l in raw.splitlines() if len(l.strip()) > 3][:5]
        context.user_data["sutuur"] = {"mode": "satr", "cands": cands}
        body = "\n\n".join(f"{i+1}. {c}" for i, c in enumerate(cands))
        await context.bot.send_message(
            q.message.chat_id,
            f"✍️ Satr nomzodlari:\n\n{body}\n\n👇 Raqam bosing — kanalga chiqadi.",
            reply_markup=_pub_kb(len(cands), "satr"))
        return

    if q.data.startswith("st_adab"):
        await q.answer("Hikoya yozilmoqda... 📖 (20-30 soniya)")
        mavzu = random.choice(ADAB_MAVZULAR)
        try:
            post = _gen(ADAB_PROMPT.format(mavzu=mavzu))
        except Exception as e:
            await context.bot.send_message(q.message.chat_id, f"Xatolik: {e}")
            return
        context.user_data["sutuur"] = {"mode": "adab", "cands": [post]}
        await context.bot.send_message(
            q.message.chat_id,
            f"📖 Adabiyot hikoyasi nomzodi:\n\n{post}",
            reply_markup=_pub_kb(1, "adab"))
        return

    if q.data.startswith("st_pub"):
        idx = int(q.data.split(":")[1])
        st = context.user_data.get("sutuur") or {}
        cands = st.get("cands", [])
        if idx >= len(cands):
            await q.answer("Eskirgan ro'yxat — /sutuur bilan yangilang.",
                           show_alert=True)
            return
        text = cands[idx].rstrip()
        if "@sutuur_uz" not in text.lower():
            text += "\n\n@sutuur_uz"
        try:
            await context.bot.send_message(chat_id=SUTUUR_CHANNEL, text=text)
            await q.answer(f"{SUTUUR_CHANNEL} ga chiqdi! ✅")
            await context.bot.send_message(q.message.chat_id,
                                           f"✅ Chiqdi:\n\n{text}")
        except Exception as e:
            await q.answer(f"Xato: {e}", show_alert=True)


def register(app):
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY yo'q — sutuur-agent o'chirilgan.")
        return
    app.add_handler(CommandHandler("sutuur", cmd_sutuur))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^st_"))
    log.info("Sutuur-agent ulandi: %s", SUTUUR_CHANNEL)
