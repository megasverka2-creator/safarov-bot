# -*- coding: utf-8 -*-
"""
SAFAROV — shaxsiy blog boti (hub + AI + jamoa + statistika + Mini Konkurs).

Mini Konkurs:
  • Har bir foydalanuvchiga shaxsiy referal havola.
  • Do'st shu havola orqali kirib @safaroov_blog ga obuna bo'lsa -> taklif qilganga +3 ochko.
  • Eng ko'p ochko yig'gan g'olib (kitob sovrin). 3 kunlik muddat.

Railway -> Variables: BOT_TOKEN, ANTHROPIC_API_KEY, ADMIN_ID, DATA_DIR=/data
  (ixtiyoriy) CONTEST_PHOTO = kitob rasmining URL manzili

MUHIM: obunani tekshirish uchun bot @safaroov_blog kanalida ADMIN bo'lishi shart.
"""

import os
import re
import json
import time
import asyncio
import httpx
from datetime import datetime
from urllib.parse import quote
from bs4 import BeautifulSoup
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo,
    InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonDefault,
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
WEBAPP_URL = "https://starlit-arithmetic-7b0c9e.netlify.app/"
BOT_USERNAME = "safarovblog_bot"   # post_init da avtomatik yangilanadi

# ----- MINI KONKURS sozlamalari -----
CONTEST_ACTIVE = True
CONTEST_TITLE = "1-Mini Konkurs"
CONTEST_PRIZE = "Kitob 📚"
CONTEST_END = "2026-06-27 23:59"          # 3 kun (server vaqti ~UTC). Tahrirlash mumkin.
CONTEST_CHANNEL = "safaroov_blog"          # qatnashish uchun shu kanalga obuna shart
REF_POINTS = 3                             # har bir taklif uchun ochko
CONTEST_PHOTO = os.environ.get("CONTEST_PHOTO", "")  # ixtiyoriy: kitob rasmi URL

# ----- "Meni qanchalik bilasiz?" (do'st testi) sozlamalari -----
QUIZ_FILE = os.path.join(DATA_DIR, "quizzes.json")
BLOG_URL = "https://t.me/safaroov_blog"   # blog/kanal — kuzatishga taklif

QUIZ_QUESTIONS = [
    ("Bo'sh vaqtimda nima qilishni yoqtiraman?",
     ["Film/serial", "Do'stlar bilan", "Dam olish", "O'yin/telefon"]),
    ("Men qanday insonman?",
     ["Ekstravert", "Introvert", "O'rtasi", "Vaziyatga qarab"]),
    ("Sevimli taom turim?",
     ["Milliy taom", "Fast food", "Shirinlik", "Sog'lom ovqat"]),
    ("Dam olish kunimni qanday o'tkazaman?",
     ["Uyda", "Sayohat/sayr", "Do'stlar bilan", "Ish/o'qish bilan"]),
    ("Jahlimni nima chiqaradi?",
     ["Yolg'on", "Kechikish", "E'tiborsizlik", "Buyruqbozlik"]),
    ("Sevimli faslim?",
     ["Bahor", "Yoz", "Kuz", "Qish"]),
    ("Qanday musiqa tinglayman?",
     ["Zamonaviy/pop", "Milliy", "Rep", "Tinch/klassik"]),
    ("Stressda nima qilaman?",
     ["Yolg'iz qolaman", "Gaplashaman", "Mashg'ulot bilan", "Uxlayman"]),
    ("Pul topsam birinchi nima?",
     ["Sayohat", "Jamg'araman", "Sovg'a qilaman", "O'zimga"]),
    ("Eng katta orzuim?",
     ["Mashina/uy", "O'z biznesim", "Chet el", "Mashhurlik"]),
]

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
    rec.setdefault("points", 0)
    rec["last_seen"] = today
    users[uid] = rec
    save_json(USERS_FILE, users)


# ---------------- Konkurs yordamchilari ----------------
def contest_delta():
    try:
        return datetime.strptime(CONTEST_END, "%Y-%m-%d %H:%M") - datetime.now()
    except Exception:
        return None

def contest_over():
    d = contest_delta()
    return d is not None and d.total_seconds() <= 0

def left_str():
    d = contest_delta()
    if d is None:
        return ""
    s = int(d.total_seconds())
    if s <= 0:
        return "Tugadi"
    days, rem = s // 86400, s % 86400
    hours, mins = rem // 3600, (rem % 3600) // 60
    if days > 0:
        return f"{days} kun {hours} soat qoldi"
    if hours > 0:
        return f"{hours} soat {mins} daqiqa qoldi"
    return f"{mins} daqiqa qoldi"

async def is_subscribed(bot, uid):
    try:
        m = await bot.get_chat_member(f"@{CONTEST_CHANNEL}", uid)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False

async def try_count(bot, uid):
    """ Obuna bo'lgan taklif qilingan foydalanuvchi uchun taklif qilganga +3 ochko. """
    users = load_json(USERS_FILE, {})
    u = users.get(str(uid))
    if not u:
        return None
    ref = u.get("ref_by")
    if not ref or u.get("counted"):
        return None
    if not await is_subscribed(bot, uid):
        return None
    inv = users.get(str(ref))
    u["counted"] = True
    if inv:
        inv["points"] = inv.get("points", 0) + REF_POINTS
        users[str(ref)] = inv
    users[str(uid)] = u
    save_json(USERS_FILE, users)
    return ref if inv else None

def ranking():
    users = load_json(USERS_FILE, {})
    return sorted([(uid, u) for uid, u in users.items() if u.get("points", 0) > 0],
                  key=lambda kv: kv[1]["points"], reverse=True)

def contest_text(user, sub, link):
    pts = load_json(USERS_FILE, {}).get(str(user.id), {}).get("points", 0)
    ranked = ranking()
    pos = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == str(user.id)), "—")
    status = ("✅ Obunangiz tasdiqlandi — qatnashyapsiz!" if sub
              else f"⚠️ Avval @{CONTEST_CHANNEL} ga obuna bo'ling, keyin «Obunani tekshirish».")
    return (
        f"🏆 {CONTEST_TITLE}\n"
        f"🎁 Sovrin: {CONTEST_PRIZE}\n"
        f"⏳ {left_str()}\n\n"
        "Qatnashish shartlari:\n"
        f"1️⃣ @{CONTEST_CHANNEL} ga obuna bo'ling\n"
        "2️⃣ Quyidagi havola orqali do'stlaringizni taklif qiling\n"
        f"3️⃣ Har bir do'st (obuna bo'lsa) = +{REF_POINTS} ochko\n"
        "4️⃣ Eng ko'p ochko yig'gan g'olib — sovrinni yutadi! 🎉\n\n"
        f"{status}\n\n"
        f"🔗 Sizning havolangiz:\n{link}\n\n"
        f"⭐ Ochkolaringiz: {pts}   |   O'rin: {pos}"
    )

def contest_kb(sub, link):
    share = ("https://t.me/share/url?url=" + quote(link, safe="")
             + "&text=" + quote("Mini konkursda qatnashib, kitob yutib oling! 🎁📚", safe=""))
    rows = [[InlineKeyboardButton("📤 Do'stlarni taklif qilish", url=share)],
            [InlineKeyboardButton("✅ Obunani tekshirish", callback_data="con_check"),
             InlineKeyboardButton("🏆 Reyting", callback_data="con_top")]]
    if not sub:
        rows.insert(0, [InlineKeyboardButton(f"📣 @{CONTEST_CHANNEL} ga obuna",
                                             url=f"https://t.me/{CONTEST_CHANNEL}")])
    return InlineKeyboardMarkup(rows)

def leaderboard_text(user):
    ranked = ranking()
    lines = [f"🏆 {CONTEST_TITLE} — Reyting (TOP 10)", f"⏳ {left_str()}", ""]
    medals = ["🥇", "🥈", "🥉"]
    if not ranked:
        lines.append("Hozircha ishtirokchi yo'q. Birinchi bo'ling — do'st taklif qiling!")
    for i, (uid, u) in enumerate(ranked[:10]):
        mark = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{mark} {u.get('name','Foydalanuvchi')} — {u['points']} ochko")
    pos = next((i + 1 for i, (uid, _) in enumerate(ranked) if uid == str(user.id)), None)
    if pos:
        lines += ["", f"Sizning o'rningiz: {pos}"]
    return "\n".join(lines)

def closed_text():
    ranked = ranking()
    if ranked:
        uid, u = ranked[0]
        return (f"🏁 {CONTEST_TITLE} yakunlandi!\n\n"
                f"🥇 G'olib: {u.get('name','Foydalanuvchi')} — {u['points']} ochko\n"
                f"🎁 {CONTEST_PRIZE} g'olibga topshiriladi. Tabriklaymiz! 🎉")
    return f"🏁 {CONTEST_TITLE} yakunlandi!"

async def send_contest(bot, chat_id, user, edit_message=None):
    track_user(user)
    if not CONTEST_ACTIVE:
        msg = "Hozircha faol konkurs yo'q. Tez orada yangi konkurs bo'ladi! 🔔"
        if edit_message:
            await edit_message.edit_text(msg)
        else:
            await bot.send_message(chat_id, msg)
        return
    if contest_over():
        msg = closed_text()
        if edit_message:
            await edit_message.edit_text(msg)
        else:
            await bot.send_message(chat_id, msg)
        return

    inviter = await try_count(bot, user.id)
    if inviter:
        try:
            await bot.send_message(int(inviter),
                                   f"🎉 Havolangiz orqali yangi do'st qo'shildi! +{REF_POINTS} ochko.")
        except Exception:
            pass

    sub = await is_subscribed(bot, user.id)
    link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.id}"
    text = contest_text(user, sub, link)
    kb = contest_kb(sub, link)
    if edit_message:
        try:
            await edit_message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
    else:
        if CONTEST_PHOTO:
            try:
                await bot.send_photo(chat_id, CONTEST_PHOTO)
            except Exception:
                pass
        await bot.send_message(chat_id, text, reply_markup=kb, disable_web_page_preview=True)


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
    user = update.effective_user
    track_user(user)
    args = context.args
    if args and args[0].startswith("q_"):
        await quiz_start_guess(update, context, args[0][2:])
        return
    if args and args[0].startswith("ref_"):
        ref = args[0][4:]
        users = load_json(USERS_FILE, {})
        u = users.get(str(user.id), {})
        if ref.isdigit() and ref != str(user.id) and not u.get("ref_by"):
            u["ref_by"] = ref
            users[str(user.id)] = u
            save_json(USERS_FILE, users)
    inviter = await try_count(context.bot, user.id)
    if inviter:
        try:
            await context.bot.send_message(int(inviter),
                                           f"🎉 Havolangiz orqali yangi do'st qo'shildi! +{REF_POINTS} ochko.")
        except Exception:
            pass
    extra = ""
    if CONTEST_ACTIVE and not contest_over():
        extra = f"\n\n🏆 *{CONTEST_TITLE}* ketyapti — sovrin: {CONTEST_PRIZE}! Qatnashish: /konkurs"
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\nPastdagi *« SAFAROV menyu »* tugmasini bosing — barcha bo'limlar "
        "shu yerda: Hayot G'ildiragi, Kun hikmati, Kitob tavsiyasi, Kanallar, Jamoa va Mini Konkurs."
        + extra, reply_markup=menu_kb(), parse_mode="Markdown")

async def konkurs(update, context):
    await send_contest(context.bot, update.effective_chat.id, update.effective_user)

async def xabar(update, context):
    """ Faqat admin: barcha foydalanuvchilarga xabar yuboradi. /xabar <matn> """
    if update.effective_user.id != ADMIN_ID:
        return
    text = (update.message.text or "").partition(" ")[2].strip()
    if not text:
        await update.message.reply_text(
            "📢 Foydalanish: /xabar <matn>\n\n"
            "Masalan:\n/xabar 🏆 Mini Konkurs davom etyapti! Do'st taklif qilib, kitobni "
            "yutib oling 👉 /konkurs")
        return
    users = load_json(USERS_FILE, {})
    ids = list(users.keys())
    await update.message.reply_text(f"📤 Yuborilmoqda... ({len(ids)} foydalanuvchi)")
    sent, failed = 0, 0
    for uid in ids:
        try:
            await context.bot.send_message(int(uid), text, disable_web_page_preview=True)
            sent += 1
        except Exception:
            failed += 1
        if (sent + failed) % 25 == 0:
            await asyncio.sleep(1)
    await update.message.reply_text(
        f"✅ Yetkazildi: {sent}\n🚫 Yetmadi (bloklagan/o'chirgan): {failed}")


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
    parts = sum(1 for u in users.values() if u.get("points", 0) > 0)
    top = ranking()[:1]
    top_line = f"\n🥇 Yetakchi: {top[0][1]['name']} ({top[0][1]['points']} ochko)" if top else ""
    quizzes = load_json(QUIZ_FILE, {})
    q_made = len(quizzes)
    q_played = sum(len(z.get("attempts", [])) for z in quizzes.values())
    await update.message.reply_text(
        f"📊 *Statistika*\n\n👥 Jami foydalanuvchi: *{len(users)}*\n"
        f"🟢 Bugun faol: *{active}*\n🤝 Jamoaga arizalar: *{len(apps)}*\n"
        f"🏆 Konkurs ishtirokchilari: *{parts}*{top_line}\n"
        f"🧩 Testlar: *{q_made}* yaratilgan · *{q_played}* o'ynalgan",
        parse_mode="Markdown")


# ---------------- Inline callbacklar ----------------
async def on_gen(update, context):
    q = update.callback_query
    await q.answer()
    kind = q.data.split(":")[1]
    await q.edit_message_text(f"{TITLES.get(kind,'')}\n\n⏳ Yangilanmoqda...")
    text = await generate_section(kind, force=True)
    await q.edit_message_text(text, reply_markup=gen_kb(kind), disable_web_page_preview=True)

async def on_contest_cb(update, context):
    q = update.callback_query
    if q.data == "con_top":
        await q.answer()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Konkurs", callback_data="con_back")]])
        await q.edit_message_text(leaderboard_text(update.effective_user), reply_markup=kb)
    else:  # con_check, con_back
        await q.answer("Tekshirildi ✅" if q.data == "con_check" else None)
        await send_contest(context.bot, q.message.chat_id, update.effective_user, edit_message=q.message)

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
        await update.message.reply_text(text, reply_markup=gen_kb(action), disable_web_page_preview=True)

    elif action == "contest":
        await send_contest(context.bot, update.effective_chat.id, user)

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
                ADMIN_ID, f"🆕 Yangi ariza\n\n👤 {user.full_name} {uname}\n🆔 {user.id}\n"
                f"Yo'nalish: {role}\n\nIsm/yosh: {name}\nSabab: {reason}", reply_markup=kb)
        await update.message.reply_text("✅ Arizangiz qabul qilindi! Tez orada bog'lanamiz. Rahmat! 🤝")

    elif action == "quiz_create":
        answers = [str(a).strip()[:80] for a in (data.get("answers") or []) if str(a).strip()][:10]
        if len(answers) < 10:
            await update.message.reply_text(
                "😕 Test to'liq emas. Iltimos, menyudan qaytadan urinib ko'ring.")
            return
        code = quiz_save(user, answers)
        link, kb = quiz_share_kit(code)
        await update.message.reply_text(
            "✅ *Testingiz tayyor!* 🎉\n\n"
            "Havolani yaqinlaringizga yuboring — ular sizni qanchalik bilishini ko'rasiz:\n\n"
            f"`{link}`\n\n👇 yoki bevosita yuboring:",
            reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)

    elif action == "quiz":
        await quiz_start_create(update, context)

    elif "areas" in data:
        await update.message.reply_text(format_result(data), parse_mode="Markdown")
        text, markup = build_advice(data)
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=markup, disable_web_page_preview=True)


# ==================== "Meni qanchalik bilasiz?" (do'st testi) ====================
import random
import string


def md_esc(t):
    """ Markdown maxsus belgilaridan himoya (ism ichida _ * [ ] bo'lsa buzilmasin). """
    return re.sub(r'([_*\[\]()`])', r'\\\1', str(t))


def quiz_label(score):
    if score >= 9:
        return "Eng yaqin inson! 🏆"
    if score >= 7:
        return "Juda yaxshi bilarkansiz 😎"
    if score >= 4:
        return "O'rtacha 🤔"
    return "Yaqinroq tanishish kerak 😅"


def gen_quiz_code():
    quizzes = load_json(QUIZ_FILE, {})
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if code not in quizzes:
            return code


def quiz_save(user, answers):
    """ answers = 10 ta matn (yaratuvchining javoblari). Saqlab, kodni qaytaradi. """
    code = gen_quiz_code()
    quizzes = load_json(QUIZ_FILE, {})
    quizzes[code] = {
        "creator_id": user.id,
        "creator_name": user.first_name or user.full_name or "Do'stingiz",
        "answers": answers,
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "attempts": [],
    }
    save_json(QUIZ_FILE, quizzes)
    return code


def quiz_share_kit(code):
    link = f"https://t.me/{BOT_USERNAME}?start=q_{code}"
    share_text = "Meni qanchalik yaxshi bilasiz? Sinab ko'ring 👀"
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📤 Do'stlarga yuborish", url=share_url)]])
    return link, kb


def build_guess_options(answers):
    """ Har savol uchun mehmonga ko'rsatiladigan 4 variant + to'g'ri indeks.
        Custom javob bo'lsa: yaratuvchi javobi + 3 ta preset aralashtiriladi. """
    out = []
    for i, correct in enumerate(answers):
        presets = list(QUIZ_QUESTIONS[i][1]) if i < len(QUIZ_QUESTIONS) else []
        if correct in presets:
            opts = list(presets)
        else:
            distractors = [p for p in presets if p != correct]
            random.shuffle(distractors)
            opts = [correct] + distractors[:3]
            random.shuffle(opts)
        try:
            ci = opts.index(correct)
        except ValueError:
            opts = ([correct] + opts)[:4]
            ci = 0
        out.append({"opts": opts, "correct": ci})
    return out


async def quiz_send_question(context, chat_id, message=None):
    qz = context.user_data.get("quiz")
    if not qz:
        return
    step = qz["step"]
    question = QUIZ_QUESTIONS[step][0]
    if qz["mode"] == "c":
        opts = QUIZ_QUESTIONS[step][1]
        head = (f"🧩 *Test yaratish* — {step+1}/10\n\n*{question}*\n"
                "_(o'zingiz haqingizda to'g'ri javobni tanlang)_")
    else:
        opts = qz["gopts"][step]["opts"]
        head = (f"🧩 *{md_esc(qz['target_name'])}ni qanchalik bilasiz?* — {step+1}/10\n\n"
                f"*{question}*\n_(uning javobini taxmin qiling)_")
    rows = [[InlineKeyboardButton(o, callback_data=f"qz:a:{i}")] for i, o in enumerate(opts)]
    kb = InlineKeyboardMarkup(rows)
    if message:
        await message.edit_text(head, reply_markup=kb, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, head, reply_markup=kb, parse_mode="Markdown")


async def quiz_start_create(update, context):
    context.user_data["quiz"] = {"mode": "c", "step": 0, "answers": []}
    await quiz_send_question(context, update.effective_chat.id)


async def quiz_start_guess(update, context, code):
    quizzes = load_json(QUIZ_FILE, {})
    data = quizzes.get(code)
    if not data:
        await update.message.reply_text("😕 Bu test topilmadi yoki o'chirilgan.")
        return
    if data.get("creator_id") == update.effective_user.id:
        await update.message.reply_text(
            "🙂 Bu — sizning testingiz! Havolani yaqinlaringizga yuboring — ular sizni "
            "qanchalik bilishini ko'rasiz.")
        return
    name = data.get("creator_name") or "Do'stingiz"
    gopts = build_guess_options(data.get("answers", []))
    context.user_data["quiz"] = {
        "mode": "g", "step": 0, "score": 0, "code": code,
        "target_name": name, "gopts": gopts,
    }
    await update.message.reply_text(
        f"🧩 *{md_esc(name)}* sizni sinab ko'rmoqchi!\n\n"
        "10 ta savol bo'ladi — har birida uning javobini taxmin qiling. Tayyormisiz? 👇",
        parse_mode="Markdown")
    await quiz_send_question(context, update.effective_chat.id)


async def quiz_finish_create(update, context):
    q = update.callback_query
    qz = context.user_data["quiz"]
    code = quiz_save(update.effective_user, qz["answers"])
    link, kb = quiz_share_kit(code)
    await q.edit_message_text(
        "✅ *Testingiz tayyor!* 🎉\n\n"
        "Havolani yaqinlaringizga yuboring — ular sizni qanchalik bilishini ko'rasiz:\n\n"
        f"`{link}`\n\n👇 yoki bevosita yuboring:",
        reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)


async def quiz_finish_guess(update, context):
    q = update.callback_query
    user = update.effective_user
    qz = context.user_data["quiz"]
    quizzes = load_json(QUIZ_FILE, {})
    data = quizzes.get(qz["code"])
    if not data:
        await q.edit_message_text("😕 Test topilmadi.")
        return
    score = qz.get("score", 0)
    label = quiz_label(score)
    name = data.get("creator_name") or "Do'stingiz"
    guesser = user.first_name or user.full_name or "Do'stingiz"

    data.setdefault("attempts", []).append({
        "id": user.id, "name": guesser, "score": score,
        "date": time.strftime("%Y-%m-%d %H:%M"),
    })
    save_json(QUIZ_FILE, quizzes)

    result = (
        "🧩 *Natija*\n\n"
        f"Siz *{md_esc(name)}*ni *{score}/10* bilasiz!\n"
        f"*{label}*\n\n"
        "🌿 Rahmat, qatnashganingiz uchun!\n"
        "Agar bunday qiziqarli o'yinlar yoqsa, blogni kuzatib boring 😊\n\n"
        "🎡 Hayot G'ildiragi  ·  🏆 Yutuqli mini-konkurslar  ·  ✍️ Foydali postlar"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ O'z testingizni yarating",
                              web_app=WebAppInfo(WEBAPP_URL + "#quiz"))],
        [InlineKeyboardButton("📩 Blogni kuzatish", url=BLOG_URL)],
    ])
    await q.edit_message_text(result, reply_markup=kb, parse_mode="Markdown",
                              disable_web_page_preview=True)

    # yaratuvchiga bildirishnoma
    try:
        await context.bot.send_message(
            int(data["creator_id"]),
            f"🔔 *{md_esc(guesser)}* sizni *{score}/10* bildi! {label}",
            parse_mode="Markdown")
    except Exception:
        pass


async def quiz_cmd(update, context):
    """ /sinov — testni bevosita boshlash (Mini App'siz sinash uchun). """
    track_user(update.effective_user)
    await quiz_start_create(update, context)


async def on_quiz_cb(update, context):
    q = update.callback_query
    if not q.data.startswith("qz:a:"):
        await q.answer()
        return
    qz = context.user_data.get("quiz")
    if not qz:
        await q.answer()
        await q.edit_message_text("⏳ Sessiya tugagan. /sinov yozib qaytadan boshlang.")
        return
    await q.answer()
    opt = int(q.data.split(":")[2])
    step = qz["step"]

    if qz["mode"] == "c":
        qz["answers"].append(QUIZ_QUESTIONS[step][1][opt])
    else:
        if opt == qz["gopts"][step]["correct"]:
            qz["score"] += 1

    qz["step"] += 1
    if qz["step"] < len(QUIZ_QUESTIONS):
        await quiz_send_question(context, q.message.chat_id, message=q.message)
        return

    if qz["mode"] == "c":
        await quiz_finish_create(update, context)
    else:
        await quiz_finish_guess(update, context)
    context.user_data.pop("quiz", None)


async def post_init(app):
    global BOT_USERNAME
    try:
        me = await app.bot.get_me()
        if me.username:
            BOT_USERNAME = me.username
    except Exception:
        pass
    try:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    except Exception:
        pass


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("konkurs", konkurs))
    app.add_handler(CommandHandler("kanallar", kanallar))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("xabar", xabar))
    app.add_handler(CommandHandler("sinov", quiz_cmd))
    app.add_handler(CallbackQueryHandler(on_gen, pattern="^gen:"))
    app.add_handler(CallbackQueryHandler(on_contest_cb, pattern="^con_"))
    app.add_handler(CallbackQueryHandler(on_quiz_cb, pattern="^qz:"))
    app.add_handler(CallbackQueryHandler(admin_decide, pattern="^(acc|rej):"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
