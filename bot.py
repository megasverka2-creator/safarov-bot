# -*- coding: utf-8 -*-
"""
SAFAROV — shaxsiy blog boti.
Asosiy menyu endi VIZUAL Mini App (index.html). Bot quyidagilarni boshqaradi:
  • /start -> pastdan "SAFAROV menyu" web-tugmasi
  • Mini App'dan kelgan signallar:
      {action:"quote"}  -> AI: Kun hikmati
      {action:"books"}  -> AI: Kitob tavsiyasi
      {action:"join", name, role, reason} -> ariza adminga
      {areas:[...]}     -> Hayot G'ildiragi natijasi
  • /kanallar, /stats (admin)

Railway -> Variables: BOT_TOKEN, ANTHROPIC_API_KEY, ADMIN_ID, (DATA_DIR ixtiyoriy)
"""

import os
import re
import json
import time
import httpx
from bs4 import BeautifulSoup
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp,
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
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
MODEL = "claude-haiku-4-5-20251001"

DATA_DIR = os.environ.get("DATA_DIR", ".")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
APPS_FILE = os.path.join(DATA_DIR, "applications.json")

aclient = AsyncAnthropic(api_key=ANTHROPIC_KEY) if (ANTHROPIC_KEY and AsyncAnthropic) else None
WEBAPP_URL = "https://starlit-arithmetic-7b0c9e.netlify.app/"   # index.html (hub)

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
SECTION_SOURCES = {
    "quote": ["devonaiy_bedor", "farosatdaan", "Sutuur_uz"],
    "books": ["mutolaachidan", "sutuur_kitoblari"],
}
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
TITLES = {"quote": "🌙 Kun hikmati", "books": "📖 Kitob tavsiyasi"}
CACHE = {}
CACHE_TTL = 6 * 3600
# ----------------------------------------------------------------------


# ---------------- Saqlash ----------------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass

def track_user(user):
    users = load_json(USERS_FILE, {})
    uid = str(user.id)
    today = time.strftime("%Y-%m-%d")
    rec = users.get(uid, {})
    rec["name"] = user.full_name
    rec["username"] = user.username or ""
    rec.setdefault("first_seen", today)
    rec["last_seen"] = today
    users[uid] = rec
    save_json(USERS_FILE, users)


# ---------------- Klaviaturalar ----------------
def menu_kb():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🏠 SAFAROV menyu", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True)

def gen_kb(kind):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Yangilash", callback_data=f"gen:{kind}")]])

def channels_kb():
    rows, row = [], []
    for i, (title, user) in enumerate(CHANNELS, 1):
        row.append(InlineKeyboardButton(title, url=f"https://t.me/{user}"))
        if i % 2 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


# ---------------- Kanal postlari + AI ----------------
async def fetch_posts(username, limit=15):
    try:
        async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = await c.get(f"https://t.me/s/{username}")
        soup = BeautifulSoup(r.text, "html.parser")
        out = []
        for div in soup.select("div.tgme_widget_message_text"):
            txt = re.sub(r"\n{3,}", "\n\n", div.get_text("\n", strip=True)).strip()
            if len(txt) > 20:
                out.append(txt[:500])
        return out[-limit:]
    except Exception:
        return []

async def collect_sources(kind):
    chunks = []
    for user in SECTION_SOURCES.get(kind, []):
        posts = await fetch_posts(user)
        if posts:
            chunks.append(f"[@{user}]\n- " + "\n- ".join(posts[-8:]))
    return "\n\n".join(chunks)[:7000]

SYS = ("Sen 'Safarov' o'zbek blogining yordamchisisan. Faqat o'zbek tilida, sodda va "
       "samimiy yoz. Markdown belgilarini (*, _, #) ishlatma.")
PROMPTS = {
    "quote": ("Quyida Telegram kanal postlari (manbasi bilan) berilgan. Ulardan eng ta'sirli, "
              "qisqa va ma'noli BITTA fikr yoki she'r parchasini tanla. Avval hikmatning o'zini, "
              "keyin yangi qatorda '— manba: @kanal'. Ortiqcha izoh yo'q. Maks 60 so'z.\n\n{texts}"),
    "books": ("Quyida kitob kanallaridan postlar (manbasi bilan). Ulardan BITTA kitobni tanlab "
              "tavsiya qil: nomi (va muallifi), 1-2 jumla mazmuni, keyin '— manba: @kanal'.\n\n{texts}"),
}

async def generate_section(kind, force=False):
    now = time.time()
    if not force and kind in CACHE and now - CACHE[kind][0] < CACHE_TTL:
        return CACHE[kind][1]
    if aclient is None:
        return f"{TITLES.get(kind,'')}\n\n🚧 AI hali sozlanmagan (ANTHROPIC_API_KEY yo'q)."
    texts = await collect_sources(kind)
    if not texts:
        return f"{TITLES.get(kind,'')}\n\nHozircha post topilmadi. Birozdan keyin urinib ko'ring."
    try:
        msg = await aclient.messages.create(
            model=MODEL, max_tokens=350, system=SYS,
            messages=[{"role": "user", "content": PROMPTS[kind].format(texts=texts)}])
        body = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
    except Exception:
        return f"{TITLES.get(kind,'')}\n\n⚠️ Tahlil qilib bo'lmadi. Keyinroq urinib ko'ring."
    result = f"{TITLES.get(kind,'')}\n\n{body}"
    CACHE[kind] = (now, result)
    return result


# ---------------- Buyruqlar ----------------
async def start(update, context):
    track_user(update.effective_user)
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "Pastdagi *« SAFAROV menyu »* tugmasini bosing — barcha bo'limlar shu yerda: "
        "Hayot G'ildiragi, Kun hikmati, Kitob tavsiyasi, Kanallar va Jamoaga qo'shilish.",
        reply_markup=menu_kb(), parse_mode="Markdown")

async def kanallar(update, context):
    await update.message.reply_text("📣 *Bizning kanallarimiz:*", reply_markup=channels_kb(),
                                    parse_mode="Markdown")

async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_json(USERS_FILE, {})
    apps = load_json(APPS_FILE, [])
    today = time.strftime("%Y-%m-%d")
    active = sum(1 for u in users.values() if u.get("last_seen") == today)
    await update.message.reply_text(
        f"📊 *Statistika*\n\n👥 Jami foydalanuvchi: *{len(users)}*\n"
        f"🟢 Bugun faol: *{active}*\n🤝 Jamoaga arizalar: *{len(apps)}*",
        parse_mode="Markdown")


# ---------------- Inline callbacklar ----------------
async def on_gen(update, context):
    q = update.callback_query
    await q.answer()
    kind = q.data.split(":")[1]
    await q.edit_message_text(f"{TITLES.get(kind,'')}\n\n⏳ Yangilanmoqda...")
    text = await generate_section(kind, force=True)
    await q.edit_message_text(text, reply_markup=gen_kb(kind), disable_web_page_preview=True)

async def admin_decide(update, context):
    q = update.callback_query
    await q.answer()
    if update.effective_user.id != ADMIN_ID:
        return
    action, uid = q.data.split(":")
    uid = int(uid)
    if action == "acc":
        msg = "🎉 Tabriklaymiz! Siz jamoaga qabul qilindingiz. Tez orada bog'lanamiz."
        tag = "✅ Qabul qilindi"
    else:
        msg = "Arizangiz uchun rahmat. Hozircha imkoniyat bo'lmadi, lekin aloqada bo'lamiz."
        tag = "❌ Rad etildi"
    try:
        await context.bot.send_message(uid, msg)
    except Exception:
        pass
    await q.edit_message_text((q.message.text or "") + f"\n\n— {tag}")


# ---------------- Mini App'dan kelgan ma'lumot ----------------
def format_result(data):
    lines = ["🎯 *Hayot G'ildiragi — natija*", f"📅 {data.get('date','')}", ""]
    for a in data.get("areas", []):
        lines.append(f"{a['n']}. {a['name']} — *{a['score']}/10* ({a['level']})")
    lines += ["", "———————————————",
              f"📊 Umumiy ball: *{data.get('average')}/10* — *{data.get('verdict')}*"]
    return "\n".join(lines)

def build_advice(data):
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
    return ("\n".join(lines), InlineKeyboardMarkup(buttons) if buttons else None)

async def on_webapp_data(update, context):
    user = update.effective_user
    track_user(user)
    try:
        data = json.loads(update.effective_message.web_app_data.data)
    except Exception:
        await update.message.reply_text("Ma'lumotni o'qib bo'lmadi.")
        return

    action = data.get("action")

    if action in ("quote", "books"):
        await update.message.reply_text(f"{TITLES[action]}\n\n⏳ Tayyorlanmoqda...")
        text = await generate_section(action)
        await update.message.reply_text(text, reply_markup=gen_kb(action),
                                        disable_web_page_preview=True)

    elif action == "join":
        name = data.get("name", "—"); role = data.get("role", "—"); reason = data.get("reason", "—")
        apps = load_json(APPS_FILE, [])
        apps.append({"id": user.id, "name": user.full_name, "username": user.username or "",
                     "form_name": name, "role": role, "reason": reason,
                     "date": time.strftime("%Y-%m-%d %H:%M")})
        save_json(APPS_FILE, apps)
        if ADMIN_ID:
            uname = f"@{user.username}" if user.username else "(username yo'q)"
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Qabul", callback_data=f"acc:{user.id}"),
                InlineKeyboardButton("❌ Rad", callback_data=f"rej:{user.id}")]])
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 Yangi ariza\n\n👤 {user.full_name} {uname}\n🆔 {user.id}\n"
                f"Yo'nalish: {role}\n\nIsm/yosh: {name}\nSabab: {reason}",
                reply_markup=kb)
        await update.message.reply_text(
            "✅ Arizangiz qabul qilindi! Tez orada siz bilan bog'lanamiz. Rahmat! 🤝")

    elif "areas" in data:
        await update.message.reply_text(format_result(data), parse_mode="Markdown")
        text, markup = build_advice(data)
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=markup, disable_web_page_preview=True)


async def post_init(app):
    """ Xabar yozish joyi yonidagi doimiy «menyu» tugmasini o'rnatadi (ochilganda Mini App). """
    try:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="SAFAROV", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception:
        pass


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("kanallar", kanallar))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(on_gen, pattern="^gen:"))
    app.add_handler(CallbackQueryHandler(admin_decide, pattern="^(acc|rej):"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
