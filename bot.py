# -*- coding: utf-8 -*-
"""
SAFAROV — Hayot G'ildiragi Interaktiv Tizimi (Telegram bot).

Foydalanuvchi yo'li:
  1) Web-sayt   — foydalanuvchi 10 ta yo'nalishni baholaydi (Mini App).
  2) Bot tahlil — natija + grafik shu botga keladi.
  3) Tavsiyalar — past ball olgan soha uchun mos KANAL tavsiya qilinadi.

Buyruqlar:
  /start     — g'ildirakni to'ldirish tugmasi
  /kanallar  — barcha kanallar ro'yxati

O'rnatish:   pip install "python-telegram-bot>=21,<22"
Ishga tushirish: BOT_TOKEN ni qo'yib  ->  python bot.py
"""

import json
import os
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
)

# ----------------------------------------------------------------------
# 1) @BotFather bergan token. Serverda BOT_TOKEN env-variable orqali qo'yiladi.
TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_BOT_TOKENINGIZNI_QOYING")

# 2) Mini App manzili (Netlify).
TOOLS = {
    "🎯 Hayot g'ildiragi": "https://starlit-arithmetic-7b0c9e.netlify.app/",
}

# 3) BARCHA KANALLAR — /kanallar buyrug'ida ko'rsatiladi.
#    (sarlavha, username)  — username @ belgisisiz.
CHANNELS = [
    ("✍️ Shaxsiy blog — Safarov",     "safaroov_blog"),
    ("📚 Fikr, adabiyot va hayot",     "Sutuur_uz"),
    ("🤲 Ruhiy va ma'naviy yo'l",      "Nurulyaqin_uz"),
    ("🧠 Fikr va farosat maydoni",     "farosatdaan"),
    ("📖 Kitoblar va mutolaa olami",   "mutolaachidan"),
    ("📕 Manfaatli kitoblar tavsiyasi","sutuur_kitoblari"),
    ("🌙 She'r va tafakkur oqshomlari","devonaiy_bedor"),
    ("🎼 Satrlar ohangi",              "satrlar_ohangi"),
    ("💭 Xayol olami",                 "Xayol_Olamim"),
    ("🤍 Samimiylik istab",            "samimiylik_istab"),
]

# 4) TAVSIYALAR: har bir yo'nalish -> mos kanal (mavzuga yaqin).
#    (ko'rinadigan matn, username)
REC = {
    "Sog'liq va Energiya": ("Hayotdan lavhalar va ilhom", "safaroov_blog"),
    "Karyera va O'sish":   ("O'sish va shaxsiy yo'l",       "safaroov_blog"),
    "Moliyaviy Erkinlik":  ("Fikr va farosat maydoni",      "farosatdaan"),
    "Oila va Yaqinlar":    ("Samimiylik va munosabatlar",   "samimiylik_istab"),
    "Do'stlar va Muhit":   ("Fikr, adabiyot va hayot",      "Sutuur_uz"),
    "Shaxsiy Rivojlanish": ("Kitoblar va mutolaa olami",    "mutolaachidan"),
    "Dam olish":           ("Xayol olami",                  "Xayol_Olamim"),
    "Ma'naviyat":          ("Ruhiy va ma'naviy yo'l",       "Nurulyaqin_uz"),
    "Xobbi":               ("She'r va tafakkur oqshomlari", "devonaiy_bedor"),
    "Atrof-muhit":         ("Satrlar ohangi",               "satrlar_ohangi"),
}
LOW_THRESHOLD = 5  # shu ball yoki past bo'lsa, kanal tavsiya qilinadi
# ----------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = [[KeyboardButton(text=name, web_app=WebAppInfo(url=url))]
            for name, url in TOOLS.items()]
    keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Bu — *Hayot G'ildiragi*. Quyidagi tugmani bosing va hayotingizni "
        "10 ta yo'nalish bo'yicha baholang. Natija va shaxsiy tavsiyalar shu yerga keladi.\n\n"
        "Barcha kanallarimiz uchun: /kanallar\n\n"
        "_Halol javob bering — natija faqat o'zingiz uchun._",
        reply_markup=keyboard, parse_mode="Markdown",
    )


async def kanallar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Barcha kanallar — ikki ustunli inline tugmalar. """
    buttons, row = [], []
    for i, (title, user) in enumerate(CHANNELS, 1):
        row.append(InlineKeyboardButton(title, url=f"https://t.me/{user}"))
        if i % 2 == 0:
            buttons.append(row); row = []
    if row:
        buttons.append(row)
    await update.message.reply_text(
        "📣 *Bizning kanallarimiz* — qiziqishingizga mos birini tanlang:",
        reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown",
    )


def format_result(data: dict) -> str:
    lines = ["🎯 *Hayot G'ildiragi — natija*", f"📅 {data.get('date', '')}", ""]
    for a in data.get("areas", []):
        lines.append(f"{a['n']}. {a['name']} — *{a['score']}/10* ({a['level']})")
    lines += [
        "",
        "———————————————",
        f"📊 Umumiy ball: *{data.get('average')}/10* — *{data.get('verdict')}*",
    ]
    return "\n".join(lines)


def build_advice(data: dict):
    """ Past ball olingan eng zaif 3 ta soha uchun matn + kanal tugmalari. """
    low = [a for a in data.get("areas", []) if a["score"] <= LOW_THRESHOLD]
    low.sort(key=lambda a: a["score"])
    if not low:
        return ("✨ Barakalla! Hech bir yo'nalish past emas — muvozanatni shu tarzda saqlang.", None)

    lines = ["💡 *Avval shu yo'nalishlardan boshlang:*", ""]
    buttons = []
    for a in low[:3]:
        rec = REC.get(a["name"])
        if rec:
            label, user = rec
            lines.append(f"• *{a['name']}* ({a['score']}/10) — {label}")
            buttons.append([InlineKeyboardButton(f"📂 {label}", url=f"https://t.me/{user}")])
        else:
            lines.append(f"• *{a['name']}* ({a['score']}/10)")
    lines += ["", "📣 Barcha kanallar: /kanallar"]
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    return ("\n".join(lines), markup)


async def on_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.effective_message.web_app_data.data
    try:
        data = json.loads(raw)
    except Exception:
        await update.message.reply_text("Ma'lumotni o'qib bo'lmadi.")
        return

    await update.message.reply_text(format_result(data), parse_mode="Markdown")
    text, markup = build_advice(data)
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kanallar", kanallar))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
