# -*- coding: utf-8 -*-
"""
SAFAROV — shaxsiy blog boti (hub + AI bo'limlari).

Bo'limlar:
  🎯 Hayot G'ildiragi  -> Mini App (web)
  🌙 Kun hikmati        -> AI: kanallardan eng ta'sirli fikr/she'r
  📖 Kitob tavsiyasi    -> AI: kitob kanallaridan bitta tavsiya
  🧠 Testlar / 💬 Fikr  -> tez orada
  📣 Kanallar           -> barcha kanallar

Kerakli o'zgaruvchilar (Railway -> Variables):
  BOT_TOKEN           = @BotFather token
  ANTHROPIC_API_KEY   = console.anthropic.com dagi kalit

O'rnatish: pip install -r requirements.txt
"""

import os
import re
import json
import time
import html
import httpx
from bs4 import BeautifulSoup
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)

try:
    from anthropic import AsyncAnthropic
except Exception:
    AsyncAnthropic = None

# ----------------------------------------------------------------------
TOKEN = os.environ.get("BOT_TOKEN", "BU_YERGA_BOT_TOKENINGIZNI_QOYING")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = "claude-haiku-4-5-20251001"   # arzon va tez; kerak bo'lsa o'zgartirsa bo'ladi

aclient = AsyncAnthropic(api_key=ANTHROPIC_KEY) if (ANTHROPIC_KEY and AsyncAnthropic) else None

WEBAPP_URL = "https://starlit-arithmetic-7b0c9e.netlify.app/"

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

# AI bo'limlari uchun manba kanallar
SECTION_SOURCES = {
    "quote": ["devonaiy_bedor", "farosatdaan", "Sutuur_uz"],
    "books": ["mutolaachidan", "sutuur_kitoblari"],
}

# G'ildirak tavsiyalari
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

COMING = {
    "tests": ("🧠 Testlar", "Qisqa, qiziqarli o'z-o'zini bilish testlari tez orada qo'shiladi."),
    "feedback": ("💬 Fikr bildirish", "Fikr va takliflaringiz uchun bo'lim tez orada ishga tushadi."),
}

HUB_TEXT = ("🏠 *SAFAROV*\n\n"
            "Xush kelibsiz! Bu — shaxsiy makonim: o'z-o'zini rivojlantirish, "
            "kitob va ma'naviyat bir joyda.\n\nQuyidan tanlang 👇")

CACHE = {}            # key -> (timestamp, text)
CACHE_TTL = 6 * 3600  # 6 soat
# ----------------------------------------------------------------------


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Hayot G'ildiragi", callback_data="wheel")],
        [InlineKeyboardButton("🌙 Kun hikmati", callback_data="quote"),
         InlineKeyboardButton("📖 Kitob tavsiyasi", callback_data="books")],
        [InlineKeyboardButton("🧠 Testlar", callback_data="tests"),
         InlineKeyboardButton("📣 Kanallar", callback_data="channels")],
        [InlineKeyboardButton("💬 Fikr bildirish", callback_data="feedback")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="menu")]])


def section_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Yangilash", callback_data=f"{kind}_new")],
        [InlineKeyboardButton("⬅️ Asosiy menyu", callback_data="menu")],
    ])


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
        resize_keyboard=True)


# ---------------- Kanal postlarini olish ----------------
async def fetch_posts(username: str, limit: int = 15):
    url = f"https://t.me/s/{username}"
    try:
        async with httpx.AsyncClient(timeout=15.0,
                                     headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for div in soup.select("div.tgme_widget_message_text"):
            txt = div.get_text("\n", strip=True)
            txt = re.sub(r"\n{3,}", "\n\n", txt).strip()
            if len(txt) > 20:
                out.append(txt[:500])
        return out[-limit:]
    except Exception:
        return []


async def collect_sources(kind: str):
    chunks = []
    for user in SECTION_SOURCES.get(kind, []):
        posts = await fetch_posts(user)
        if posts:
            joined = "\n- ".join(posts[-8:])
            chunks.append(f"[@{user}]\n- {joined}")
    return "\n\n".join(chunks)[:7000]


# ---------------- AI ----------------
SYS = ("Sen 'Safarov' o'zbek blogining yordamchisisan. Faqat o'zbek tilida, "
       "sodda va samimiy yoz. Markdown belgilarini (*, _, #) ishlatma.")

PROMPTS = {
    "quote": ("Quyida bir nechta Telegram kanal postlari (manbasi bilan) berilgan. "
              "Ulardan eng ta'sirli, qisqa va ma'noli BITTA fikr yoki she'r parchasini tanla. "
              "Avval o'sha hikmatning o'zini yoz, keyin yangi qatorda '— manba: @kanal' ko'rinishida "
              "manbani ko'rsat. Ortiqcha izoh yozma. Maksimum 60 so'z.\n\nPostlar:\n{texts}"),
    "books": ("Quyida kitob kanallaridan postlar (manbasi bilan) berilgan. Ulardan BITTA kitobni "
              "tanlab tavsiya qil. Avval kitob nomi (va muallifi agar bor bo'lsa), keyin 1-2 jumla "
              "nima haqida ekani, keyin yangi qatorda '— manba: @kanal'. Qisqa va aniq.\n\nPostlar:\n{texts}"),
}

TITLES = {"quote": "🌙 Kun hikmati", "books": "📖 Kitob tavsiyasi"}


async def generate_section(kind: str, force: bool = False) -> str:
    now = time.time()
    if not force and kind in CACHE and now - CACHE[kind][0] < CACHE_TTL:
        return CACHE[kind][1]

    if aclient is None:
        return (f"{TITLES.get(kind,'')}\n\n🚧 AI hali sozlanmagan. "
                "Railway'da ANTHROPIC_API_KEY o'zgaruvchisini qo'shing.")

    texts = await collect_sources(kind)
    if not texts:
        return (f"{TITLES.get(kind,'')}\n\nHozircha kanallardan post topilmadi. "
                "Birozdan keyin urinib ko'ring.")

    try:
        msg = await aclient.messages.create(
            model=MODEL, max_tokens=350, system=SYS,
            messages=[{"role": "user", "content": PROMPTS[kind].format(texts=texts)}],
        )
        body = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    except Exception as e:
        return f"{TITLES.get(kind,'')}\n\n⚠️ Tahlil qilib bo'lmadi. Keyinroq urinib ko'ring."

    result = f"{TITLES.get(kind,'')}\n\n{body}"
    CACHE[kind] = (now, result)
    return result


# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HUB_TEXT, reply_markup=main_menu(), parse_mode="Markdown")


async def kanallar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📣 *Bizning kanallarimiz:*", reply_markup=channels_kb(),
                                    parse_mode="Markdown")


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
            "🎯 *Hayot G'ildiragi*\n\nPastdagi *« G'ildirakni to'ldirish »* tugmasini bosing va "
            "hayotingizni 10 ta yo'nalish bo'yicha baholang.",
            reply_markup=wheel_kb(), parse_mode="Markdown")
    elif data in ("quote", "books", "quote_new", "books_new"):
        kind = data.replace("_new", "")
        force = data.endswith("_new")
        await q.edit_message_text(f"{TITLES[kind]}\n\n⏳ Tayyorlanmoqda...")
        text = await generate_section(kind, force=force)
        await q.edit_message_text(text, reply_markup=section_kb(kind),
                                  disable_web_page_preview=True)
    elif data in COMING:
        title, desc = COMING[data]
        await q.edit_message_text(f"*{title}*\n\n🚧 {desc}", reply_markup=back_kb(),
                                  parse_mode="Markdown")


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
