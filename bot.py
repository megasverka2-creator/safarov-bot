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
from datetime import datetime, timezone, timedelta
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

import agent
import zikr
import iqtibos  # Iqtibos kartalari (/iqtibos, 3 uslub + AI rasm)
import subtitr  # Video subtitr (faqat admin)
import kurs   # Marketing kursi moduli (Stars to'lovi bilan)
import ustoz  # AI Ustoz: topshiriq tekshirish va savol-javob
import farosat  # Farosatdan kanali uchun kontent-agent
import sutuur   # Sutuur adabiy kanali uchun kontent-agent
import admin    # Yagona boshqaruv paneli (/panel)

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
STATS_FILE = os.path.join(DATA_DIR, "stats.json")   # kunlik funksiya statistikasi

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

# ----- "Shaxsiyat / ichki kuch testi" -----
# Har variant tur harfi bilan: Y=Yetakchi, D=Donishmand, I=Izlanuvchi, M=Mehribon
PTEST_QUESTIONS = [
    ("Do'stlar davrasida odatda men...", [
        ("Suhbatni boshqaraman, yo'naltiraman", "Y"),
        ("Ko'proq kuzataman, tahlil qilaman", "D"),
        ("Yangi g'oya yoki mavzu tashlayman", "I"),
        ("Tinglayman, hammani qo'llab-quvvatlayman", "M")]),
    ("Muammoga duch kelganda...", [
        ("Tez qaror qilib harakatga o'taman", "Y"),
        ("O'ylab, har tomonini tahlil qilaman", "D"),
        ("Yangi, kutilmagan yo'l izlayman", "I"),
        ("Yaqinlarimdan maslahat so'rayman", "M")]),
    ("Bo'sh vaqtimda ko'proq...", [
        ("Reja tuzaman, maqsad qo'yaman", "Y"),
        ("Kitob o'qiyman, fikr yuritaman", "D"),
        ("Yangi narsa o'rganaman, sinab ko'raman", "I"),
        ("Yaqinlarim bilan vaqt o'tkazaman", "M")]),
    ("Meni eng ko'p ilhomlantiradigan narsa...", [
        ("G'alaba va natija", "Y"),
        ("Bilim va haqiqat", "D"),
        ("Yangilik va o'sish", "I"),
        ("Insonlar va munosabatlar", "M")]),
    ("Jamoada men odatda...", [
        ("Yetakchilik qilaman", "Y"),
        ("Strategiya va rejani o'ylayman", "D"),
        ("G'oyalar manbasiman", "I"),
        ("Jamoani birlashtiraman", "M")]),
    ("Qaror qabul qilishda asosan...", [
        ("Maqsadga qarayman", "Y"),
        ("Mantiq va faktlarga", "D"),
        ("Sezgi va imkoniyatga", "I"),
        ("Odamlarga ta'siriga", "M")]),
    ("Men uchun muvaffaqiyat — bu...", [
        ("Qo'ygan maqsadga erishish", "Y"),
        ("Narsalarni chuqur tushunish", "D"),
        ("Doimiy o'sib borish", "I"),
        ("Atrofdagilarni baxtli qilish", "M")]),
    ("Tanqidni qanday qabul qilaman?", [
        ("Kuchli bo'lib, oldinga intilaman", "Y"),
        ("Tahlil qilib, xulosa chiqaraman", "D"),
        ("O'sish imkoni deb bilaman", "I"),
        ("His bilan, lekin tushunaman", "M")]),
    ("Yangi loyihada birinchi...", [
        ("Maqsad va rejani belgilayman", "Y"),
        ("Hamma narsani o'rganib chiqaman", "D"),
        ("Eksperiment qilib ko'raman", "I"),
        ("Jamoani yig'aman", "M")]),
    ("Atrofdagilar meni ko'proq... deb biladi", [
        ("Qat'iyatli va yetakchi", "Y"),
        ("Aqlli va dono", "D"),
        ("Qiziquvchan va ijodkor", "I"),
        ("Mehribon va g'amxo'r", "M")]),
]

PTEST_RESULTS = {
    "Y": ("🦅 Yetakchi",
          "Siz tug'ma yetakchisiz! Qat'iyat, maqsadga intilish va boshqalarni "
          "ergashtira olish — sizning kuchingiz. Qiyinchilikdan qo'rqmaysiz va "
          "atrofdagilarga ilhom berasiz."),
    "D": ("🧠 Donishmand",
          "Siz — Donishmandsiz! Chuqur fikrlash, tahlil va bilimga chanqoqlik sizni "
          "ajratib turadi. Shoshilmasdan, dono qarorlar qabul qilasiz — atrofdagilar "
          "maslahatingizni qadrlaydi."),
    "I": ("🌱 Izlanuvchi",
          "Siz — Izlanuvchisiz! Qiziquvchanlik, ijod va doimiy o'sish — sizning "
          "yo'lingiz. Yangilikdan qo'rqmaysiz, hayotni katta sarguzasht deb bilasiz."),
    "M": ("❤️ Mehribon",
          "Siz — Mehribonsiz! Hamdardlik, g'amxo'rlik va insonlarni tushunish — eng "
          "katta kuchingiz. Atrofdagilarga iliqlik ulashasiz va haqiqiy do'stsiz."),
}

# ----- 2-Mini Konkurs (obuna + tasodifiy g'olib) -----
K2_FILE = os.path.join(DATA_DIR, "k2.json")
K2_CHANNELS = ["sutuur_uz", "sutuur_kitoblari"]   # bot bu kanallarda ADMIN bo'lishi SHART
K2_PRIZE = "«O'tkan kunlar» — Abdulla Qodiriy (3 jildlik)"
K2_DEADLINE = "2-iyul, 21:00"                      # e'lon uchun (ko'rsatiladigan matn)
K2_DEADLINE_LOCAL = "2026-07-02 21:00"             # avtomatik tanlov vaqti (Toshkent, UTC+5)
TASHKENT_TZ = timezone(timedelta(hours=5))

def k2_deadline_dt():
    return datetime.strptime(K2_DEADLINE_LOCAL, "%Y-%m-%d %H:%M").replace(tzinfo=TASHKENT_TZ)
K2_POST_CHANNEL = "sutuur_uz"                       # e'lon shu kanalga joylanadi (bot 'Post' huquqli admin bo'lsin)
K2_POST_CAPTION = (
    "📚 2-MINI KONKURS — «O'tkan kunlar» sovrin! 🎁\n\n"
    "Abdulla Qodiriyning mashhur «O'tkan kunlar» asari (3 jildlik, Hilol Nashr) — "
    "bir baxtli g'olibga sovg'a!\n\n"
    "✅ Qatnashish shartlari:\n"
    "1️⃣ @sutuur_uz va @sutuur_kitoblari kanallariga obuna bo'ling\n"
    "2️⃣ Ushbu post izohiga «Kitob» deb yozing\n"
    "3️⃣ Pastdagi tugma orqali raqamingizni oling 👇\n\n"
    "📅 G'olib " + K2_DEADLINE + " dan so'ng TASODIFIY tanlanadi.\n\n"
    "Omad tilaymiz! 🍀"
)

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


# ---------------- Statistika yordamchilari ----------------
EVENT_LABELS = {
    "menyu":      "🏠 Menyu (start)",
    "konkurs1":   "🏆 1-Konkurs",
    "konkurs2":   "🎲 2-Konkurs",
    "test_dost":  "🧩 Do'st testi",
    "test_shaxs": "💪 Shaxs testi",
    "gildirak":   "🎯 Hayot g'ildiragi",
}

def track_event(name):
    """ Funksiya ishlatilishini kun bo'yicha sanab boradi: {"2026-07-12": {"menyu": 5}} """
    d = load_json(STATS_FILE, {})
    day = time.strftime("%Y-%m-%d")
    d.setdefault(day, {})
    d[day][name] = d[day].get(name, 0) + 1
    save_json(STATS_FILE, d)

def last_days(n=7):
    """ Oxirgi n kun ro'yxati (bugungi kun oxirida): ['2026-07-06', ...] """
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]

UZ_WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]

def bar_chart(pairs, width=10):
    """ pairs = [(label, son), ...] → matnli grafik qatorlari """
    mx = max((v for _, v in pairs), default=0) or 1
    lines = []
    for label, v in pairs:
        n = round(v / mx * width) if v else 0
        lines.append(f"{label} {'▇' * n if n else '·'} {v}")
    return "\n".join(lines)


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
    if args and args[0] == "zikr":
        await zikr.cmd_zikr(update, context)
        return
    if args and args[0] == "k2":
        await k2_join(update, context)
        return
    if args and args[0] == "pt":
        await ptest_start(update, context)
        return
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
    track_event("menyu")
    extra = ""
    if CONTEST_ACTIVE and not contest_over():
        extra = f"\n\n🏆 *{CONTEST_TITLE}* ketyapti — sovrin: {CONTEST_PRIZE}! Qatnashish: /konkurs"
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\nPastdagi *« SAFAROV menyu »* tugmasini bosing — barcha bo'limlar "
        "shu yerda: Hayot G'ildiragi, Kun hikmati, Kitob tavsiyasi, Kanallar, Jamoa va Mini Konkurs."
        + extra, reply_markup=menu_kb(), parse_mode="Markdown")

async def konkurs(update, context):
    track_event("konkurs1")
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
            users[uid]["blocked"] = False
        except Exception:
            failed += 1
            users[uid]["blocked"] = True   # bloklagan/o'chirgan deb belgilanadi
        if (sent + failed) % 25 == 0:
            await asyncio.sleep(1)
    save_json(USERS_FILE, users)
    await update.message.reply_text(
        f"✅ Yetkazildi: {sent}\n🚫 Yetmadi (bloklagan/o'chirgan): {failed}")


async def tekshir(update, context):
    """ Faqat admin: barcha foydalanuvchilarni jimgina tekshiradi — kim botni
    bloklagan/o'chirganini aniqlaydi. Foydalanuvchiga hech narsa bormaydi. """
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_json(USERS_FILE, {})
    ids = list(users.keys())
    await update.message.reply_text(
        f"🔍 Tekshirilmoqda... ({len(ids)} foydalanuvchi, ~{len(ids)//20 + 1} soniya)")
    ok, blocked = 0, 0
    for i, uid in enumerate(ids):
        try:
            # 'typing' harakati xabar emas — foydalanuvchi hech narsa sezmaydi
            await context.bot.send_chat_action(int(uid), "typing")
            ok += 1
            users[uid]["blocked"] = False
        except Exception:
            blocked += 1
            users[uid]["blocked"] = True
        if (i + 1) % 20 == 0:
            await asyncio.sleep(1)
    save_json(USERS_FILE, users)
    pct = round(blocked / len(ids) * 100) if ids else 0
    await update.message.reply_text(
        f"🔍 Tekshiruv tugadi\n\n"
        f"✅ Faol (bot ochiq): {ok}\n"
        f"🚫 Bloklagan/o'chirgan: {blocked} ({pct}%)\n\n"
        f"Endi /stats da ham ko'rinadi.")


async def kanallar(update, context):
    await update.message.reply_text("📣 *Bizning kanallarimiz:*", reply_markup=channels_kb(),
                                    parse_mode="Markdown")

async def stats(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_json(USERS_FILE, {})
    apps = load_json(APPS_FILE, [])
    today = time.strftime("%Y-%m-%d")
    days7 = last_days(7)

    active = sum(1 for u in users.values() if u.get("last_seen") == today)
    active7 = sum(1 for u in users.values() if u.get("last_seen", "") in days7)
    parts = sum(1 for u in users.values() if u.get("points", 0) > 0)
    top = ranking()[:1]
    import html as _html
    top_line = (f"\n🥇 Yetakchi: {_html.escape(str(top[0][1]['name']))} "
                f"({top[0][1]['points']} ochko)") if top else ""
    quizzes = load_json(QUIZ_FILE, {})
    q_made = len(quizzes)
    q_played = sum(len(z.get("attempts", [])) for z in quizzes.values())

    # --- Yangi foydalanuvchilar grafigi (first_seen bo'yicha, oxirgi 7 kun) ---
    new_by_day = {d: 0 for d in days7}
    for u in users.values():
        fs = u.get("first_seen", "")
        if fs in new_by_day:
            new_by_day[fs] += 1
    week_new = sum(new_by_day.values())
    chart_pairs = []
    for d in days7:
        dt = datetime.strptime(d, "%Y-%m-%d")
        chart_pairs.append((f"{dt.strftime('%d.%m')} {UZ_WEEKDAYS[dt.weekday()]}", new_by_day[d]))
    chart = bar_chart(chart_pairs)

    # --- Funksiyalar reytingi (stats.json, oxirgi 7 kun) ---
    ev = load_json(STATS_FILE, {})
    totals = {}
    for d in days7:
        for name, cnt in ev.get(d, {}).items():
            totals[name] = totals.get(name, 0) + cnt
    if totals:
        ranked = sorted(totals.items(), key=lambda x: -x[1])
        feat_pairs = [(EVENT_LABELS.get(n, n), c) for n, c in ranked[:8]]
        feats = "\n".join(f"{i+1}. {lbl} — <b>{c}</b>" for i, (lbl, c) in enumerate(feat_pairs))
    else:
        feats = "<i>Hali ma'lumot yig'ilmagan (yangi versiya ishga tushgandan boshlab yig'iladi)</i>"

    blocked = sum(1 for u in users.values() if u.get("blocked"))
    blocked_line = (f"\n🚫 Bloklagan/o'chirgan: <b>{blocked}</b> · "
                    f"Yetib boradi: <b>{len(users) - blocked}</b>") if blocked else \
                   "\n🚫 Bloklaganlar: <i>aniqlash uchun /tekshir bosing</i>"

    konkurs_line = (f"🏆 Konkurs ishtirokchilari: <b>{parts}</b>{top_line}\n"
                    if parts else "")

    await update.message.reply_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchi: <b>{len(users)}</b>{blocked_line}\n"
        f"🟢 Bugun faol: <b>{active}</b> · Haftada: <b>{active7}</b>\n"
        f"🆕 Haftada yangi: <b>{week_new}</b>\n"
        f"🤝 Jamoaga arizalar: <b>{len(apps)}</b>\n"
        f"{konkurs_line}"
        f"🧩 Testlar: <b>{q_made}</b> yaratilgan · <b>{q_played}</b> o'ynalgan\n\n"
        f"📈 <b>Yangi foydalanuvchilar (7 kun):</b>\n"
        f"<pre>{chart}</pre>\n\n"
        f"🔥 <b>Eng ko'p ishlatilgan bo'limlar (7 kun):</b>\n{feats}",
        parse_mode="HTML")


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
    if "areas" in data:
        track_event("gildirak")
    elif action:
        track_event(f"app_{action}")

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

    elif action == "zikr":
        await zikr.cmd_zikr(update, context)

    elif action == "zikr_off":
        await zikr.cmd_zikr_off(update, context)

    elif action == "k2":
        await k2_join(update, context)

    elif action == "ptest":
        await ptest_start(update, context)

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
    track_event("test_dost")
    context.user_data["quiz"] = {"mode": "c", "step": 0, "answers": []}
    await quiz_send_question(context, update.effective_chat.id)


async def quiz_start_guess(update, context, code):
    track_event("test_dost")
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


# ==================== Shaxsiyat / ichki kuch testi ====================
async def ptest_send_question(context, chat_id, message=None):
    pt = context.user_data.get("ptest")
    if not pt:
        return
    step = pt["step"]
    question, opts = PTEST_QUESTIONS[step]
    head = f"🌟 *Shaxsiyat testi* — {step+1}/10\n\n*{question}*"
    rows = [[InlineKeyboardButton(o[0], callback_data=f"pt:a:{i}")] for i, o in enumerate(opts)]
    kb = InlineKeyboardMarkup(rows)
    if message:
        await message.edit_text(head, reply_markup=kb, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, head, reply_markup=kb, parse_mode="Markdown")


async def ptest_start(update, context):
    track_event("test_shaxs")
    context.user_data["ptest"] = {"step": 0, "scores": {"Y": 0, "D": 0, "I": 0, "M": 0}}
    await ptest_send_question(context, update.effective_chat.id)


async def ptest_cmd(update, context):
    track_user(update.effective_user)
    await ptest_start(update, context)


async def on_ptest_cb(update, context):
    q = update.callback_query
    if q.data == "pt:again":
        await q.answer()
        context.user_data["ptest"] = {"step": 0, "scores": {"Y": 0, "D": 0, "I": 0, "M": 0}}
        await ptest_send_question(context, q.message.chat_id, message=q.message)
        return
    if not q.data.startswith("pt:a:"):
        await q.answer()
        return
    pt = context.user_data.get("ptest")
    if not pt:
        await q.answer()
        await q.edit_message_text("⏳ Sessiya tugagan. /shaxs yozib qaytadan boshlang.")
        return
    await q.answer()
    opt = int(q.data.split(":")[2])
    step = pt["step"]
    typ = PTEST_QUESTIONS[step][1][opt][1]
    pt["scores"][typ] += 1
    pt["step"] += 1

    if pt["step"] < len(PTEST_QUESTIONS):
        await ptest_send_question(context, q.message.chat_id, message=q.message)
        return

    winner = max(pt["scores"], key=lambda k: pt["scores"][k])
    name, desc = PTEST_RESULTS[winner]
    link = f"https://t.me/{BOT_USERNAME}?start=pt"
    share_text = f"Men shaxsiyat testida '{name}' chiqdim! 🌟 Sen qaysi turdasan?"
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(share_text)}"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 Natijani ulashish", url=share_url)],
        [InlineKeyboardButton("🔁 Qaytadan", callback_data="pt:again"),
         InlineKeyboardButton("📩 Blog", url=BLOG_URL)],
    ])
    await q.edit_message_text(
        f"🌟 *Sizning natijangiz:*\n\n*{name}*\n\n{desc}",
        reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)
    context.user_data.pop("ptest", None)


# ==================== 2-Mini Konkurs (obuna + tasodifiy g'olib) ====================
async def k2_check_subs(bot, uid):
    """ Foydalanuvchi K2_CHANNELS dagi BARCHA kanallarga obunami? """
    for ch in K2_CHANNELS:
        try:
            m = await bot.get_chat_member(f"@{ch}", uid)
            if m.status not in ("member", "administrator", "creator"):
                return False
        except Exception:
            return False
    return True


def k2_load():
    return load_json(K2_FILE, {"active": True, "counter": 0, "participants": {}, "winner": None})


def k2_subscribe_kb():
    rows = [[InlineKeyboardButton(f"📣 @{ch} ga obuna", url=f"https://t.me/{ch}")] for ch in K2_CHANNELS]
    rows.append([InlineKeyboardButton("🔄 Tekshirish", callback_data="k2:check")])
    return InlineKeyboardMarkup(rows)


def k2_give_number(data, user):
    """ Yangi raqam beradi va saqlaydi. Raqamni qaytaradi. """
    data["counter"] += 1
    num = data["counter"]
    data["participants"][str(user.id)] = {
        "number": num,
        "name": user.first_name or user.full_name or "Ishtirokchi",
        "date": time.strftime("%Y-%m-%d %H:%M"),
    }
    save_json(K2_FILE, data)
    return num


def k2_joined_text(num):
    return (f"🎉 *Tabriklaymiz! Konkursga qo'shildingiz.*\n\n"
            f"🎟 Tartib raqamingiz: *{num}*\n\n"
            f"🏆 Sovrin: {K2_PRIZE}\n"
            f"📅 G'olib {K2_DEADLINE} dan so'ng ishtirokchilar orasidan TASODIFIY tanlanadi.\n\n"
            "Omad! 🍀")


async def k2_join(update, context):
    track_event("konkurs2")
    user = update.effective_user
    track_user(user)
    chat_id = update.effective_chat.id
    data = k2_load()
    if not data.get("active"):
        await context.bot.send_message(chat_id, "⛔️ Konkurs yakunlangan. Keyingisini kuting!")
        return
    rec = data["participants"].get(str(user.id))
    if rec:
        await context.bot.send_message(
            chat_id,
            f"✅ Siz allaqachon qatnashgansiz!\n\n🎟 Sizning raqamingiz: *{rec['number']}*\n\n"
            f"📅 G'olib {K2_DEADLINE} dan so'ng tasodifiy tanlanadi.",
            parse_mode="Markdown")
        return
    if not await k2_check_subs(context.bot, user.id):
        await context.bot.send_message(
            chat_id,
            "📋 *Qatnashish uchun:*\n\n"
            "1️⃣ Quyidagi ikkala kanalga obuna bo'ling\n"
            "2️⃣ E'lon postiga «Kitob» deb izoh yozing\n"
            "3️⃣ «🔄 Tekshirish» tugmasini bosing\n\n"
            "Obuna bo'lgach, sizga tartib raqami beriladi 👇",
            reply_markup=k2_subscribe_kb(), parse_mode="Markdown")
        return
    num = k2_give_number(data, user)
    await context.bot.send_message(chat_id, k2_joined_text(num), parse_mode="Markdown")


async def k2_cmd(update, context):
    await k2_join(update, context)


async def on_k2_cb(update, context):
    q = update.callback_query
    if q.data != "k2:check":
        await q.answer()
        return
    user = update.effective_user
    data = k2_load()
    if data["participants"].get(str(user.id)):
        rec = data["participants"][str(user.id)]
        await q.answer()
        await q.edit_message_text(
            f"✅ Siz allaqachon qatnashgansiz!\n🎟 Raqamingiz: *{rec['number']}*",
            parse_mode="Markdown")
        return
    if not data.get("active"):
        await q.answer()
        await q.edit_message_text("⛔️ Konkurs yakunlangan.")
        return
    if await k2_check_subs(context.bot, user.id):
        num = k2_give_number(data, user)
        await q.answer("Qabul qilindi! 🎉")
        await q.edit_message_text(k2_joined_text(num), parse_mode="Markdown")
    else:
        await q.answer("Hali ikkala kanalga ham obuna bo'lmagansiz ❌", show_alert=True)


async def k2_elon(update, context):
    """ /elon2 — admin kitob rasmiga reply qilsa, bot e'lonni tugma bilan kanalga joylaydi. """
    if update.effective_user.id != ADMIN_ID:
        return
    msg = update.message.reply_to_message
    if not msg or not msg.photo:
        await update.message.reply_text(
            "❗️ Avval menga kitob rasmini yuboring, keyin o'sha rasmga REPLY qilib /elon2 yozing.")
        return
    photo_id = msg.photo[-1].file_id
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(
        "🤖 Raqam olish", url=f"https://t.me/{BOT_USERNAME}?start=k2")]])
    try:
        await context.bot.send_photo(
            f"@{K2_POST_CHANNEL}", photo=photo_id,
            caption=K2_POST_CAPTION, reply_markup=btn)
        await update.message.reply_text(f"✅ E'lon @{K2_POST_CHANNEL} ga joylandi (tugma bilan)!")
    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Joylab bo'lmadi: {e}\n\n"
            f"Bot @{K2_POST_CHANNEL} da 'Post Messages' huquqli admin ekanini tekshiring.")


async def k1_reset(update, context):
    """ /reset1 — 1-Mini Konkurs natijalarini tozalaydi.
    Ma'lumot yo'qolmasin: avval arxiv faylga saqlanadi. """
    if update.effective_user.id != ADMIN_ID:
        return
    users = load_json(USERS_FILE, {})
    ishtirokchi = {uid: {"name": u.get("name", ""), "points": u.get("points", 0)}
                   for uid, u in users.items() if u.get("points", 0) > 0}
    if not ishtirokchi:
        await update.message.reply_text("Tozalanadigan natija yo'q — allaqachon bo'sh.")
        return

    arxiv_yol = os.path.join(DATA_DIR, "konkurs1_arxiv.json")
    arxiv = load_json(arxiv_yol, [])
    arxiv.append({"sana": time.strftime("%Y-%m-%d %H:%M"),
                  "natijalar": ishtirokchi})
    save_json(arxiv_yol, arxiv)

    for uid in ishtirokchi:
        users[uid]["points"] = 0
    save_json(USERS_FILE, users)

    eng = max(ishtirokchi.values(), key=lambda x: x["points"])
    await update.message.reply_text(
        f"♻️ 1-Mini Konkurs tozalandi.\n\n"
        f"• {len(ishtirokchi)} ishtirokchi ochkosi nolga qaytdi\n"
        f"• Yetakchi edi: {eng['name']} ({eng['points']} ochko)\n"
        f"• Natijalar konkurs1_arxiv.json ga saqlandi\n\n"
        f"Endi /stats da konkurs qatori ko'rinmaydi.")


async def k2_reset(update, context):
    """ /reset2 — admin konkursni toza holatga qaytaradi (raqamlar 1 dan boshlanadi). """
    if update.effective_user.id != ADMIN_ID:
        return
    save_json(K2_FILE, {"active": True, "counter": 0, "participants": {}, "winner": None})
    await update.message.reply_text(
        "♻️ 2-Mini Konkurs tozalandi!\n\n"
        "• Barcha test raqamlar o'chirildi\n"
        "• Konkurs faol holatga qaytdi\n"
        "• Keyingi raqam 1 dan boshlanadi\n\n"
        "Endi /elon2 bilan e'lonni qaytadan joylang.")


async def k2_auto_draw(context):
    """ Belgilangan vaqtda avtomatik: tasodifiy g'olib + kanalga e'lon + g'olibga xabar. """
    data = k2_load()
    if not data.get("active") or data.get("winner"):
        return  # allaqachon tanlangan yoki yopilgan — qayta tanlamaydi
    parts = data["participants"]
    if not parts:
        data["active"] = False
        save_json(K2_FILE, data)
        if ADMIN_ID:
            try:
                await context.bot.send_message(ADMIN_ID, "ℹ️ 2-konkurs vaqti tugadi, lekin ishtirokchi bo'lmadi.")
            except Exception:
                pass
        return
    uid, rec = random.choice(list(parts.items()))
    data["winner"] = {"id": int(uid), "number": rec["number"], "name": rec["name"]}
    data["active"] = False
    save_json(K2_FILE, data)
    text = (f"🏆 *2-MINI KONKURS — G'OLIB!*\n\n"
            f"Jami *{len(parts)}* ishtirokchi orasidan tasodifiy tanlandi:\n\n"
            f"🎉 *{md_esc(rec['name'])}* — raqam #{rec['number']}\n\n"
            f"🎁 Sovrin: {K2_PRIZE}\n\nTabriklaymiz! 🍀")
    try:
        await context.bot.send_message(f"@{K2_POST_CHANNEL}", text, parse_mode="Markdown")
    except Exception:
        pass
    try:
        await context.bot.send_message(
            int(uid),
            f"🎉 *Tabriklaymiz!* Siz 2-Mini Konkurs g'olibi bo'ldingiz!\n\n"
            f"🏆 Sovrin: {K2_PRIZE}\n\nTez orada siz bilan bog'lanamiz.",
            parse_mode="Markdown")
    except Exception:
        pass
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                ADMIN_ID, f"✅ G'olib avtomatik tanlandi va @{K2_POST_CHANNEL} ga e'lon qilindi: "
                          f"{rec['name']} #{rec['number']}")
        except Exception:
            pass


async def k2_golib(update, context):
    """ /golib2 — admin tasodifiy g'olibni tanlaydi. """
    if update.effective_user.id != ADMIN_ID:
        return
    data = k2_load()
    parts = data["participants"]
    if not parts:
        await update.message.reply_text("Hozircha ishtirokchi yo'q.")
        return
    uid, rec = random.choice(list(parts.items()))
    data["winner"] = {"id": int(uid), "number": rec["number"], "name": rec["name"]}
    data["active"] = False
    save_json(K2_FILE, data)
    await update.message.reply_text(
        f"🏆 *2-MINI KONKURS — G'OLIB!*\n\n"
        f"Jami *{len(parts)}* ishtirokchi orasidan tasodifiy tanlandi:\n\n"
        f"🎉 *{md_esc(rec['name'])}* — raqam #{rec['number']}\n\n"
        f"🎁 Sovrin: {K2_PRIZE}\n\n"
        f"_(Bu matnni kanalga e'lon qiling)_",
        parse_mode="Markdown")
    try:
        await context.bot.send_message(
            int(uid),
            f"🎉 *Tabriklaymiz!* Siz 2-Mini Konkurs g'olibi bo'ldingiz!\n\n"
            f"🏆 Sovrin: {K2_PRIZE}\n\nTez orada siz bilan bog'lanamiz.",
            parse_mode="Markdown")
    except Exception:
        pass


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
    # 2-Mini Konkurs: belgilangan vaqtda avtomatik g'olib tanlash taymeri
    try:
        jq = app.job_queue
        if jq is not None:
            if k2_deadline_dt() > datetime.now(TASHKENT_TZ):
                jq.run_once(k2_auto_draw, when=k2_deadline_dt(), name="k2_draw")
                print(f"[K2] Avtomatik g'olib taymeri o'rnatildi: {K2_DEADLINE_LOCAL} (Toshkent)")
            else:
                print(f"[K2] Muddat o'tgan ({K2_DEADLINE_LOCAL}) — taymer o'rnatilmadi. "
                      f"Yangi konkurs uchun K2_DEADLINE ni yangilang.")
        else:
            print("[K2] OGOHLANTIRISH: job_queue yo'q — requirements.txt da [job-queue] kerak.")
    except Exception as e:
        print(f"[K2] Taymer o'rnatilmadi: {e}")


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "menu"], start))
    app.add_handler(CommandHandler("konkurs", konkurs))
    app.add_handler(CommandHandler("kanallar", kanallar))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("xabar", xabar))
    app.add_handler(CommandHandler("tekshir", tekshir))
    app.add_handler(CommandHandler("sinov", quiz_cmd))
    app.add_handler(CommandHandler("shaxs", ptest_cmd))
    app.add_handler(CommandHandler("raqam", k2_cmd))
    app.add_handler(CommandHandler("elon2", k2_elon))
    app.add_handler(CommandHandler("reset2", k2_reset))
    app.add_handler(CommandHandler("reset1", k1_reset))
    app.add_handler(CommandHandler("golib2", k2_golib))
    app.add_handler(CallbackQueryHandler(on_gen, pattern="^gen:"))
    app.add_handler(CallbackQueryHandler(on_contest_cb, pattern="^con_"))
    app.add_handler(CallbackQueryHandler(on_quiz_cb, pattern="^qz:"))
    app.add_handler(CallbackQueryHandler(on_ptest_cb, pattern="^pt:"))
    app.add_handler(CallbackQueryHandler(on_k2_cb, pattern="^k2:"))
    app.add_handler(CallbackQueryHandler(admin_decide, pattern="^(acc|rej):"))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    agent.register(app)
    zikr.register(app)
    iqtibos.register(app)  # Iqtibos kartalari (/iqtibos)
    subtitr.register(app)  # Video subtitr (admin video tashlaydi)
    kurs.register(app)   # Marketing kursi (/kurs, 10 Stars)
    ustoz.register(app)  # AI Ustoz (/topshiriq, /savol)
    farosat.register(app)  # Farosat-agent (/farosat)
    sutuur.register(app)   # Sutuur-agent (/sutuur)
    admin.register(app)    # Boshqaruv paneli (/panel)
    print("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
