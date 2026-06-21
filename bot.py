# -*- coding: utf-8 -*-
"""
SAFAROV — shaxsiy blog boti (hub).

Tuzilma:
  /start (yoki /menu) -> asosiy menyu (inline tugmalar)
    🎯 Hayot G'ildiragi  -> pastdan web-app tugmasi chiqadi (Mini App)
    🌙 Kun hikmati        -> tez orada
    🧠 Testlar            -> tez orada
    📖 Kitob tanlash      -> tez orada
    📣 Kanallar           -> barcha kanallar
    💬 Fikr bildirish     -> tez orada

Yangi bo'lim qo'shish oson: COMING lug'atiga yoki yangi callback qo'shing.

O'rnatish: pip install "python-telegram-bot>=21,<22"
Ishga tushirish: BOT_TOKEN ni qo'yib -> python bot.py
"""

import json
import os
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

# ----------------------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_BOT_TOKENINGIZNI_QOYING")

# Mini App manzili (Netlify)
WEBAPP_URL = "https://starlit-arithmetic-7b0c9e.netlify.app/"

# Barcha kanallar (sarlavha, username)
CHANNELS = [
    ("✍️ Shaxsiy blog — Safarov",      "safaroov_blog"),
    ("📚 Fikr, adabiyot va hayot",      "Sutuur_uz"),
    ("🤲 Ruhiy va ma'naviy yo'l",       "Nurulyaqin_uz"),
    ("🧠 Fikr va farosat maydoni",      "farosatdaan"),
    ("📖 Kitoblar va mutolaa olami",    "mutolaachidan"),
    ("📕 Manfaatli kitoblar tavsiyasi", "sutuur_kitoblari"),
    ("🌙 She'r va tafakkur oqshomlari", "devonaiy_bedor"),
    ("🎼 Satrlar ohangi",               "satrlar_ohangi"),
    ("💭 Xayol olami",                  "Xayol_Olamim"),
    ("🤍 Samimiylik istab",             "samimiylik_istab"),
]

# Tavsiyalar: yo'nalish -> (matn, kanal username)
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
LOW_THRESHOLD = 5

# "Tez orada" bo'limlari (callback -> (sarlavha, tavsif))
COMING = {
    "quote": ("🌙 Kun hikmati", "Har kuni yangi iqtibos, she'r va hikmat shu yerda bo'ladi."),
    "tests": ("🧠 Testlar", "Qisqa, qiziqarli o'z-o'zini bilish testlari tez orada qo'shiladi."),
    "books": ("📖 Kitob tanlash", "Kayfiyatingizga mos kitob tavsiyasi tez orada."),
    "feedback": ("💬 Fikr bildirish", "Fikr va takliflaringiz uchun bo'lim tez orada ishga tushadi."),
}

HUB_TEXT = ("🏠 *SAFAROV*\n\n"
            "Xush kelibsiz! Bu — shaxsiy makonim: o'z-o'zini rivojlantirish, "
            "kitob va ma'naviyat bir joyda.\n\nQuyidan tanlang 👇")
# ----------------------------------------------------------------------


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Hayot G'ildiragi", callback_data="wheel")],
        [InlineKeyboardButton("🌙 Kun hikmati", callback_data="quote"),
         InlineKeyboardButton("🧠 Testlar", callback_data="tests")],
        [InlineKeyboardButton("📖 Kitob tanlash", callback_data="books"),
         InlineKeyboardButton("📣 Kanallar", callback_data="channels")],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data="feedback")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="menu")]])


def channels_kb() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, (title, user) in enumerate(CHANNELS, 1):
        row.append(InlineKeyboardButton(title, url=f"https://t.me/{user}"))
        if i % 2 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def wheel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🎯 G'ildirakni to'ldirish", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )


# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HUB_TEXT, reply_markup=main_menu(), parse_mode="Markdown")


async def kanallar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📣 *Bizning kanallarimiz:*", reply_markup=channels_kb(), parse_mode="Markdown")


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu":
        await q.edit_message_text(HUB_TEXT, reply_markup=main_menu(), parse_mode="Markdown")
    elif data == "channels":
        await q.edit_message_text("📣 *Bizning kanallarimiz:*", reply_markup=channels_kb(),
                                  parse_mode="Markdown")
    elif data == "wheel":
        await q.message.reply_text(
            "🎯 *Hayot G'ildiragi*\n\n"
            "Pastdagi *« G'ildirakni to'ldirish »* tugmasini bosing va hayotingizni "
            "10 ta yo'nalish bo'yicha baholang. Natija va shaxsiy tavsiyalar shu yerga keladi.",
            reply_markup=wheel_kb(), parse_mode="Markdown")
    elif data in COMING:
        title, desc = COMING[data]
        await q.edit_message_text(f"*{title}*\n\n🚧 {desc}",
                                  reply_markup=back_kb(), parse_mode="Markdown")


# ---------------- Mini App natijasi ----------------
def format_result(data: dict) -> str:
    lines = ["🎯 *Hayot G'ildiragi — natija*", f"📅 {data.get('date', '')}", ""]
    for a in data.get("areas", []):
        lines.append(f"{a['n']}. {a['name']} — *{a['score']}/10* ({a['level']})")
    lines += ["", "———————————————",
              f"📊 Umumiy ball: *{data.get('average')}/10* — *{data.get('verdict')}*"]
    return "\n".join(lines)


def build_advice(data: dict):
    low = [a for a in data.get("areas", []) if a["score"] <= LOW_THRESHOLD]
    low.sort(key=lambda a: a["score"])
    if not low:
        return ("✨ Barakalla! Hech bir yo'nalish past emas — muvozanatni shu tarzda saqlang.",
                back_kb())
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
    buttons.append([InlineKeyboardButton("🏠 Asosiy menyu", callback_data="menu")])
    return ("\n".join(lines), InlineKeyboardMarkup(buttons))


async def on_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = json.loads(update.effective_message.web_app_data.data)
    except Exception:
        await update.message.reply_text("Ma'lumotni o'qib bo'lmadi.")
        return
    await update.message.reply_text(format_result(data), parse_mode="Markdown")
    text, markup = build_advice(data)
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=markup, disable_web_page_preview=True)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("kanallar", kanallar))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
