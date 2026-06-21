# -*- coding: utf-8 -*-
"""
SAFAROV — Hayot G'ildiragi Interaktiv Tizimi (Telegram bot).

PDF konsepsiyasidagi 3 bosqichli foydalanuvchi yo'li:
  1) Web-sayt   — foydalanuvchi 10 ta yo'nalishni baholaydi (Mini App).
  2) Bot tahlil — natija + grafik shu botga keladi va chiroyli matn bo'ladi.
  3) Tavsiyalar — past ball olgan sohalar uchun blogdagi maqolalar tavsiya qilinadi.

O'rnatish:   pip install "python-telegram-bot>=21,<22"
Ishga tushirish:   TOKEN va URL larni to'ldirib  ->  python bot.py
"""

import json
import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
)

# ----------------------------------------------------------------------
# 1) @BotFather bergan token.
#    Serverga joylaganda BOT_TOKEN nomli "environment variable" qo'ying,
#    shunda token kodda ko'rinmaydi (xavfsizroq). Lokal sinov uchun esa
#    pastdagi qatorga to'g'ridan-to'g'ri yozsangiz ham bo'ladi.
TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_BOT_TOKENINGIZNI_QOYING")

# 2) Asboblar (Mini App'lar). Yangi bo'lim — shunchaki yangi qator.
TOOLS = {
    "🎯 Hayot g'ildiragi": "https://tiny-boba-2c6d74.netlify.app/",
}

# 3) TAVSIYALAR: past ball olingan yo'nalish -> blog maqolasi.
#    Kalitlar Mini App'dagi yo'nalish nomlari bilan AYNAN bir xil bo'lsin.
#    Linklarni o'z kanalingiz postlari bilan almashtiring (https://t.me/Safaroov_blog/123).
ARTICLES = {
    "Sog'liq va Energiya": ("Energiyani tiklash: 5 oddiy odat", "https://t.me/Safaroov_blog"),
    "Karyera va O'sish":   ("Karyerada keyingi qadam qanday", "https://t.me/Safaroov_blog"),
    "Moliyaviy Erkinlik":  ("Moliyaviy yostiq qurish", "https://t.me/Safaroov_blog"),
    "Oila va Yaqinlar":    ("Yaqinlar bilan aloqani mustahkamlash", "https://t.me/Safaroov_blog"),
    "Do'stlar va Muhit":   ("To'g'ri muhitni tanlash", "https://t.me/Safaroov_blog"),
    "Shaxsiy Rivojlanish": ("Har kuni o'sish: oddiy tizim", "https://t.me/Safaroov_blog"),
    "Dam olish":           ("Charchoqdan chiqish va hordiq", "https://t.me/Safaroov_blog"),
    "Ma'naviyat":          ("Ichki xotirjamlikni topish", "https://t.me/Safaroov_blog"),
    "Xobbi":               ("Sevimli mashg'ulot va energiya", "https://t.me/Safaroov_blog"),
    "Atrof-muhit":         ("Maoning hayotingizga ta'siri", "https://t.me/Safaroov_blog"),
}
# Past ball chegarasi: shu ball yoki undan past bo'lsa, maqola tavsiya qilinadi.
LOW_THRESHOLD = 5
# ----------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = [[KeyboardButton(text=name, web_app=WebAppInfo(url=url))]
            for name, url in TOOLS.items()]
    keyboard = ReplyKeyboardMarkup(rows, resize_keyboard=True)
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Bu — *Hayot G'ildiragi*. Quyidagi tugmani bosing va hayotingizni "
        "10 ta yo'nalish bo'yicha baholang. Natija va shaxsiy tavsiyalar shu yerga keladi.\n\n"
        "_Halol javob bering — natija faqat o'zingiz uchun._",
        reply_markup=keyboard, parse_mode="Markdown",
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


def format_advice(data: dict) -> str:
    """ Past ball olingan sohalar uchun maqola tavsiyalari (PDF: 3-bosqich). """
    low = [a for a in data.get("areas", []) if a["score"] <= LOW_THRESHOLD]
    low.sort(key=lambda a: a["score"])  # eng past birinchi
    if not low:
        return "✨ Barakalla! Hech bir yo'nalish past emas — muvozanatni shu tarzda saqlang."
    out = ["💡 *Avval shu yo'nalishlardan boshlang:*", ""]
    for a in low[:3]:  # eng past 3 ta soha
        art = ARTICLES.get(a["name"])
        if art:
            out.append(f"• *{a['name']}* ({a['score']}/10) — [{art[0]}]({art[1]})")
        else:
            out.append(f"• *{a['name']}* ({a['score']}/10)")
    return "\n".join(out)


async def on_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.effective_message.web_app_data.data
    try:
        data = json.loads(raw)
    except Exception:
        await update.message.reply_text("Ma'lumotni o'qib bo'lmadi.")
        return

    await update.message.reply_text(format_result(data), parse_mode="Markdown")
    await update.message.reply_text(
        format_advice(data), parse_mode="Markdown", disable_web_page_preview=True
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
