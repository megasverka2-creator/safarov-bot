# -*- coding: utf-8 -*-
"""
agent.py — AI Yangiliklar Agenti (@safarovblog_bot uchun modul)
================================================================

Mavjud bot.py ga ULANADI, uni almashtirmaydi. Konkurs, testlar va boshqa
funksiyalarga tegmaydi.

Ulash — bot.py ga atigi 2 qator:

    import agent                      # fayl boshidagi importlar yoniga

    agent.register(app)               # run_polling(...) dan OLDIN
                                      # (app — sizdagi Application o'zgaruvchisi;
                                      #  agar u "application" deb nomlangan bo'lsa,
                                      #  agent.register(application) yozing)

requirements.txt ga qo'shiladi:
    python-telegram-bot[job-queue]>=21,<22
    openai
    feedparser
    trafilatura

Railway → Variables ga qo'shiladi:
    OPENAI_API_KEY = sk-...
    ADMIN_ID       = sizning Telegram ID raqamingiz
    CHANNEL_ID     = @safaroov_blog        (ixtiyoriy, default shu)
    DB_PATH        = /data/agent.db        (volume ulangan bo'lsa — pastga qarang)

Nima qiladi:
  * Har kuni 07:00 (Toshkent): 3 manbadan yangiliklarni oladi, gpt-4o-mini
    bilan saralaydi, eng yaxshi 3-5 tasidan o'zbekcha post yozib ADMINGA yuboradi.
  * Admin ✅ bossa — kanalga chiqadi. ❌ — arxiv. Avtomatik hech narsa chiqmaydi.
  * 20:00: ko'rilmagan postlar bo'lsa eslatma.
  * Buyruqlar: /agent_status /agent_run /agent_pause /agent_resume /agent_sources
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime, time as dtime, date
from zoneinfo import ZoneInfo

import feedparser
import httpx
import trafilatura
from openai import OpenAI
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ======================================================================
# SOZLAMALAR (hammasi Railway Variables orqali boshqariladi)
# ======================================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@safaroov_blog")
# Baza botdagi boshqa fayllar (users.json) bilan bir joyda — Railway volume'da saqlanadi:
DB_PATH = os.environ.get("DB_PATH",
                         os.path.join(os.environ.get("DATA_DIR", "."), "agent.db"))
# Aisha AI (o'zbekcha ovoz) — kalit berilsa postlarda 🎙 Ovozli tugmasi paydo bo'ladi
AISHA_API_KEY = os.environ.get("AISHA_API_KEY", "")
AISHA_BASE = "https://back.aisha.group"

TZ = ZoneInfo("Asia/Tashkent")
MODEL = "gpt-4o-mini"
MIN_SCORE = 6                  # nomzodlik chegarasi (siz baribir qo'lda tanlaysiz)
MAX_POSTS_PER_DAY = 6          # kunlik post-nomzodlar
MAX_PER_RUBRIKA = 2            # bitta yo'nalish kunni bosib ketmasligi uchun
MAX_API_CALLS_PER_DAY = 60     # 9 manba uchun; baribir kuniga ~$0.02 atrofida
SCORING_RESERVE = MAX_POSTS_PER_DAY  # post yozish uchun doim zaxira chaqiruv qoladi
ARTICLE_CHAR_LIMIT = 8000
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"

# Rubrikalar: ai (AI/marketing) · rivojlanish (shaxsiy rivojlanish) · podcast (audio/video)
SOURCES = [
    # --- 🗞 AI va marketing ---
    ("Google AI",     "https://blog.google/technology/ai/rss/",                        "ai"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "ai"),
    ("HubSpot",       "https://blog.hubspot.com/marketing/rss.xml",                    "ai"),
    # --- 🌱 Shaxsiy rivojlanish ---
    ("Farnam Street", "https://fs.blog/feed/",                                         "rivojlanish"),
    ("Mark Manson",   "https://markmanson.net/feed",                                   "rivojlanish"),
    ("HBR",           "http://feeds.hbr.org/harvardbusiness",                          "rivojlanish"),
    # --- 🎧 Podcast va video ---
    ("TED Talks",     "https://feeds.feedburner.com/TEDTalks_audio",                   "podcast"),
    ("Huberman Lab",  "https://feeds.megaphone.fm/hubermanlab",                        "podcast"),
    ("Tim Ferriss",   "https://rss.art19.com/tim-ferriss-show",                        "podcast"),
]

RUBRIKA_EMOJI = {"ai": "🗞", "rivojlanish": "🌱", "podcast": "🎧"}
RUBRIKA_NOMI = {"ai": "AI va marketing", "rivojlanish": "Shaxsiy rivojlanish",
                "podcast": "Podcast va video"}

log = logging.getLogger("agent")

_ai = None  # OpenAI klienti kech yaratiladi (import paytida kalit talab qilinmasin)

def ai_client():
    global _ai
    if _ai is None:
        _ai = OpenAI()  # kalit OPENAI_API_KEY dan olinadi
    return _ai


# ======================================================================
# BAZA (SQLite)
# ======================================================================
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_articles(
        url TEXT PRIMARY KEY, title TEXT, source TEXT,
        seen_at TEXT, score INTEGER, status TEXT DEFAULT 'new')""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_url TEXT, text TEXT, status TEXT DEFAULT 'draft',
        created_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS agent_meta(
        key TEXT PRIMARY KEY, value TEXT)""")
    # Migratsiya: eski bazaga yangi ustunlarni qo'shish
    for col in ("summary TEXT", "rubrika TEXT DEFAULT 'ai'"):
        try:
            conn.execute(f"ALTER TABLE agent_articles ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # ustun allaqachon bor
    return conn


def meta_get(conn, key, default=""):
    row = conn.execute("SELECT value FROM agent_meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def meta_set(conn, key, value):
    conn.execute(
        "INSERT INTO agent_meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn.commit()


def api_calls_today(conn):
    today = date.today().isoformat()
    if meta_get(conn, "api_day") != today:
        meta_set(conn, "api_day", today)
        meta_set(conn, "api_calls", "0")
    return int(meta_get(conn, "api_calls", "0"))


def api_call_inc(conn):
    meta_set(conn, "api_calls", api_calls_today(conn) + 1)


# ======================================================================
# AI QATLAMI
# ======================================================================
SCORE_PROMPT = """Sen @safaroov_blog Telegram kanalining kuratorisan. Kanal ikki \
yo'nalishda: (1) AI va marketing, (2) shaxsiy rivojlanish. Auditoriya: O'zbekistondagi \
marketologlar, kichik biznes egalari, o'z ustida ishlaydigan yoshlar.

Quyidagi material sarlavhasi va annotatsiyasiga qarab baho ber.
Yuqori baho: amaliy foyda, yangi vosita/model, real keys, kuchli hayotiy saboq, \
ilmiy asosli maslahat, mashhur mehmon bilan chuqur suhbat. \
Past baho: tor ilmiy mavzu, mahalliy ahamiyatsiz xabar, reklama, takror, suv quyilgan umumiy gap.

FAQAT JSON qaytar, boshqa hech narsa yozma:
{"score": 0dan 10gacha butun son, "sabab": "bir gap"}"""

_UMUMIY_QOIDALAR = """Qat'iy qoidalar:
1. Bu TARJIMA EMAS — o'z so'zing bilan qisqa xulosa. Asosiy matn 500 belgidan oshmasin.
2. Materialda bo'lmagan fakt yoki raqamni QO'SHMA.
3. SARLAVHA to'liq tabiiy o'zbek tilida bo'lsin. Inglizcha gap tuzilishini \
ko'chirma ("AI-enabled" → "AI-lekin" kabi so'zma-so'z tarjima TAQIQLANADI). \
Yomon: "Yangi AI-lekin himoyada: Savi Security". \
Yaxshi: "Savi Security: AI endi firibgarlardan himoya qiladi".
4. Kompaniya, mahsulot, model va odam nomlari asl holicha qoladi.
5. "Ushbu tadqiqotga asoslanib", "shuni ta'kidlash joizki" kabi quruq iboralar \
ishlatilmasin — gaplar sodda, aniq va ravon bo'lsin.
6. Terminlar: birinchi ishlatishda o'zbekcha + qavsda asli. \
Masalan: "katta til modeli (LLM)".
FAQAT tayyor post matnini qaytar, izohsiz."""

POST_PROMPTS = {
    "ai": """Sen @safaroov_blog Telegram kanalining muharririsan. Kanal tili: o'zbek. \
Ohang: professional, jonli, "siz"lab.

Quyidagi inglizcha maqola asosida AI/marketing rubrikasi uchun POST yoz.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🗞 [Tabiiy o'zbekcha sarlavha]

[2-4 gap: nima bo'ldi va nega bu muhim]

💡 Bu bizga nima beradi: [1-2 gap — O'zbekiston marketologi yoki kichik biznes uchun amaliy foyda]

🔗 Manba: {url}

@safaroov_blog""",

    "rivojlanish": """Sen @safaroov_blog Telegram kanalining muharririsan. Kanal tili: \
o'zbek. Ohang: samimiy, ilhomlantiruvchi, lekin quruq motivatsiyasiz — aniq fikr va amaliy xulosa muhim.

Quyidagi inglizcha maqola asosida Shaxsiy rivojlanish rubrikasi uchun POST yoz.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🌱 [Tabiiy o'zbekcha sarlavha]

[2-4 gap: maqolaning asosiy g'oyasi — hayotiy va tushunarli tilda]

💡 Bugunoq sinab ko'ring: [1-2 gap — bitta aniq amaliy qadam]

🔗 Manba: {url}

@safaroov_blog""",

    "podcast": """Sen @safaroov_blog Telegram kanalining muharririsan. Kanal tili: \
o'zbek. Ohang: do'stona tavsiya beruvchi.

Quyida yangi podcast/video epizodining sarlavhasi va tavsifi berilgan. Sen epizodni \
to'liq eshitmagansan — shuning uchun bu TAVSIYA POSTI: tavsifga tayanib nima haqida \
ekanini va kimga foydali bo'lishini ayt, mazmunni to'qib chiqarma.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🎧 [Epizod mavzusi — tabiiy o'zbekcha]

[2-3 gap: nima haqida va nega eshitishga arziydi]

👥 Kimga foydali: [1 gap]

🔗 Tinglash: {url}

@safaroov_blog""",
}


def ai_score(conn, title, summary):
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    resp = ai_client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        max_tokens=100,
        messages=[
            {"role": "system", "content": SCORE_PROMPT},
            {"role": "user", "content": f"Sarlavha: {title}\nAnnotatsiya: {summary[:1000]}"},
        ],
    )
    try:
        return int(json.loads(resp.choices[0].message.content).get("score", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0


def ai_write_post(conn, url, article_text, rubrika="ai"):
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    prompt = POST_PROMPTS.get(rubrika, POST_PROMPTS["ai"])
    resp = ai_client().chat.completions.create(
        model=MODEL,
        max_tokens=700,
        messages=[
            {"role": "system", "content": prompt.format(url=url)},
            {"role": "user", "content": article_text[:ARTICLE_CHAR_LIMIT]},
        ],
    )
    return resp.choices[0].message.content.strip()


# ======================================================================
# AISHA AI — O'ZBEKCHA OVOZ (TTS)
# ======================================================================
def _clean_for_tts(text):
    """Postni ovoz uchun tozalaydi: havolalar, teglar va emojilar olib tashlanadi."""
    lines = []
    for ln in text.splitlines():
        if "http" in ln or "@safaroov_blog" in ln or ln.strip().startswith("🔗"):
            continue
        lines.append(ln)
    t = "\n".join(lines)
    t = re.sub(r"[^\w\s.,!?:;()'\-‘’ʻʼ«»%+]", "", t, flags=re.UNICODE)
    return re.sub(r"\n{3,}", "\n\n", t).strip()[:950]  # Aisha limiti: 1000 belgi


async def tts_generate(text):
    """Aisha AI orqali o'zbekcha audio (WAV baytlari) qaytaradi."""
    clean = _clean_for_tts(text)
    if not AISHA_API_KEY or not clean:
        return None
    async with httpx.AsyncClient(timeout=90) as cli:
        r = await cli.post(
            AISHA_BASE + "/api/v1/tts/post/",
            headers={"X-Api-Key": AISHA_API_KEY},
            data={"transcript": clean, "language": "uz",
                  "model": "Gulnoza", "mood": "Neutral", "speed": "1.0"})
        if r.status_code == 402:
            raise RuntimeError("Aisha balansi tugagan (402) — space.aisha.group da to'ldiring")
        if r.status_code != 201:
            raise RuntimeError(f"Aisha TTS xatosi {r.status_code}: {r.text[:150]}")
        path = r.json().get("audio_path", "")
        if not path:
            raise RuntimeError("Aisha javobida audio_path kelmadi")
        a = await cli.get(AISHA_BASE + path)
        a.raise_for_status()
        return a.content


def draft_keyboard(post_id):
    """Post-nomzod tugmalari. Aisha kaliti bo'lsa 🎙 ham chiqadi."""
    row = [InlineKeyboardButton("✅ Kanalga", callback_data=f"agpub:{post_id}")]
    if AISHA_API_KEY:
        row.append(InlineKeyboardButton("🎙 Ovozli", callback_data=f"agpubv:{post_id}"))
    row.append(InlineKeyboardButton("❌", callback_data=f"agskip:{post_id}"))
    return InlineKeyboardMarkup([row])


# ======================================================================
# AGENT — ASOSIY OQIM
# ======================================================================
def fetch_new_articles(conn):
    """RSS manbalardan bazada yo'q maqolalarni 'new' holatida saqlaydi."""
    added = 0
    for source_name, feed_url, rubrika in SOURCES:
        try:
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
        except Exception as e:
            log.warning("RSS xato (%s): %s", source_name, e)
            continue
        for entry in feed.entries[:10]:
            url = entry.get("link", "")
            if not url:
                continue
            if conn.execute("SELECT 1 FROM agent_articles WHERE url=?", (url,)).fetchone():
                continue
            title = entry.get("title", "(nomsiz)")
            summary = entry.get("summary", "") or entry.get("description", "")
            conn.execute(
                "INSERT OR IGNORE INTO agent_articles"
                "(url,title,source,seen_at,summary,rubrika) VALUES(?,?,?,?,?,?)",
                (url, title, source_name, datetime.now(TZ).isoformat(),
                 summary[:2000], rubrika))
            added += 1
    conn.commit()
    return added


async def run_agent(context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    if meta_get(conn, "paused") == "1":
        conn.close()
        return

    added = fetch_new_articles(conn)
    log.info("Agent: yangi maqolalar %d", added)

    # --- Bosqich A: saralash ('new' navbatidan; post yozish uchun zaxira qoladi) ---
    queue = conn.execute(
        "SELECT url, title, COALESCE(summary,'') FROM agent_articles "
        "WHERE status='new' ORDER BY seen_at DESC LIMIT 30").fetchall()
    for url, title, summary in queue:
        if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY - SCORING_RESERVE:
            log.info("Saralash to'xtadi — zaxira limitiga yetildi, qolgani ertaga.")
            break
        score = ai_score(conn, title, summary)
        if score is None:
            break
        conn.execute("UPDATE agent_articles SET score=?, status='scored' WHERE url=?",
                     (score, url))
    conn.commit()

    # --- Bosqich B: nomzodlar (har rubrikadan ko'pi bilan MAX_PER_RUBRIKA ta) ---
    rows = conn.execute(
        "SELECT url, title, source, score, COALESCE(summary,''), "
        "COALESCE(rubrika,'ai') FROM agent_articles "
        "WHERE status='scored' AND score>=? "
        "ORDER BY score DESC, seen_at DESC LIMIT 30",
        (MIN_SCORE,)).fetchall()
    candidates, taken = [], {}
    for row in rows:
        rub = row[5]
        if taken.get(rub, 0) >= MAX_PER_RUBRIKA:
            continue
        taken[rub] = taken.get(rub, 0) + 1
        candidates.append(row)
        if len(candidates) >= MAX_POSTS_PER_DAY:
            break
    log.info("Nomzodlar: %d (%s)", len(candidates), taken)

    for url, title, source, score, summary, rubrika in candidates:
        try:
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded) if downloaded else None
            if not text:
                text = title + "\n\n" + summary
            post_text = ai_write_post(conn, url, text, rubrika)
            if not post_text:
                log.info("Kunlik API limiti tugadi — qolgan nomzodlar ertaga.")
                break
            conn.execute(
                "INSERT INTO agent_posts(article_url,text,created_at) VALUES(?,?,?)",
                (url, post_text, datetime.now(TZ).isoformat()))
            conn.execute("UPDATE agent_articles SET status='posted' WHERE url=?", (url,))
            conn.commit()
            post_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            emoji = RUBRIKA_EMOJI.get(rubrika, "📬")
            nomi = RUBRIKA_NOMI.get(rubrika, rubrika)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{emoji} {nomi} · {source} · baho {score}/10:"
                     f"\n\n{post_text}",
                reply_markup=draft_keyboard(post_id),
            )
        except Exception as e:
            log.exception("Agent xatosi: %s", e)
            try:
                await context.bot.send_message(
                    ADMIN_ID, f"⚠️ Agent xatosi ({url}): {e}")
            except Exception:
                pass
    conn.close()


async def evening_reminder(context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    n = conn.execute("SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
    conn.close()
    if n:
        await context.bot.send_message(
            ADMIN_ID, f"⏰ Eslatma: {n} ta post hali ko'rilmagan. /agent_status")


# ======================================================================
# TUGMALAR (tasdiqlash)
# ======================================================================
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Bu tugma faqat admin uchun.", show_alert=True)
        return
    action, post_id = query.data.split(":")
    conn = db()
    row = conn.execute("SELECT text,status FROM agent_posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        await query.answer("Post topilmadi.")
        conn.close()
        return
    text, status = row
    if status != "draft":
        await query.answer("Bu post allaqachon ko'rilgan.")
        conn.close()
        return

    if action in ("agpub", "agpubv"):
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
            conn.execute("UPDATE agent_posts SET status='published' WHERE id=?", (post_id,))
            conn.commit()
        except Exception as e:
            await query.answer(f"Xato: {e}", show_alert=True)
            conn.close()
            return

        audio_note = ""
        if action == "agpubv":
            await query.answer("Matn chiqdi, ovoz tayyorlanmoqda... 🎙")
            try:
                audio = await tts_generate(text)
                if audio:
                    title = text.splitlines()[0].strip()[:60] or "Safarov blog"
                    await context.bot.send_audio(
                        chat_id=CHANNEL_ID, audio=audio,
                        filename="post.wav", title=title,
                        performer="Safarov blog")
                    audio_note = " + 🎙 OVOZ"
                else:
                    audio_note = " (ovoz o'tkazildi: matn bo'sh)"
            except Exception as e:
                log.exception("TTS xatosi: %s", e)
                audio_note = f"\n⚠️ Ovoz chiqmadi: {e}"
        else:
            await query.answer("Kanalga jo'natildi! ✅")
        await query.edit_message_text(f"✅ KANALGA CHIQDI{audio_note}\n\n{text}")
    else:  # agskip
        conn.execute("UPDATE agent_posts SET status='skipped' WHERE id=?", (post_id,))
        conn.commit()
        await query.answer("O'tkazib yuborildi.")
        await query.edit_message_text(f"❌ O'TKAZILDI\n\n{text}")
    conn.close()


# ======================================================================
# ADMIN BUYRUQLARI
# ======================================================================
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or update.effective_user.id != ADMIN_ID:
            return
        return await func(update, context)
    return wrapper


@admin_only
async def cmd_status(update, context):
    conn = db()
    today = date.today().isoformat()
    seen = conn.execute("SELECT COUNT(*) FROM agent_articles WHERE seen_at LIKE ?",
                        (today + "%",)).fetchone()[0]
    drafts = conn.execute("SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
    pub = conn.execute("SELECT COUNT(*) FROM agent_posts WHERE status='published'").fetchone()[0]
    calls = api_calls_today(conn)
    paused = meta_get(conn, "paused") == "1"
    conn.close()
    await update.message.reply_text(
        f"📊 Agent holati\n"
        f"Holat: {'⏸ pauzada' if paused else '▶️ ishlamoqda'}\n"
        f"Bugun ko'rilgan maqolalar: {seen}\n"
        f"Kutayotgan postlar: {drafts}\n"
        f"Jami chiqarilgan: {pub}\n"
        f"Bugungi API chaqiruvlar: {calls}/{MAX_API_CALLS_PER_DAY}\n"
        f"Taxminiy bugungi xarajat: ~${calls * 0.001:.3f}")


@admin_only
async def cmd_run(update, context):
    await update.message.reply_text("🔍 Manbalarni tekshiryapman, biroz kuting...")
    await run_agent(context)
    await update.message.reply_text("Tekshiruv tugadi. /agent_status")


@admin_only
async def cmd_pause(update, context):
    conn = db(); meta_set(conn, "paused", "1"); conn.close()
    await update.message.reply_text("⏸ Agent pauzaga qo'yildi. /agent_resume — davom ettirish.")


@admin_only
async def cmd_resume(update, context):
    conn = db(); meta_set(conn, "paused", "0"); conn.close()
    await update.message.reply_text("▶️ Agent yana ishga tushdi.")


@admin_only
async def cmd_requeue(update, context):
    """0 baho olib qolgan maqolalarni navbatga qaytaradi (bir martalik tiklash)."""
    conn = db()
    n = conn.execute(
        "UPDATE agent_articles SET status='new', score=NULL "
        "WHERE status='scored' AND score=0").rowcount
    conn.commit()
    conn.close()
    await update.message.reply_text(
        f"♻️ {n} ta maqola navbatga qaytarildi. Endi /agent_run bosing.")


@admin_only
async def cmd_sources(update, context):
    parts = []
    for rub in ("ai", "rivojlanish", "podcast"):
        names = ", ".join(n for n, _, r in SOURCES if r == rub)
        parts.append(f"{RUBRIKA_EMOJI[rub]} {RUBRIKA_NOMI[rub]}: {names}")
    await update.message.reply_text("📡 Manbalar:\n" + "\n".join(parts))


# ======================================================================
# BUYRUQLAR MENYUSI (Telegram'da avtomatik ko'rinadi)
# ======================================================================
PUBLIC_COMMANDS = [
    BotCommand("start",   "🏠 Bosh menyu"),
    BotCommand("konkurs", "🏆 Konkurs haqida"),
    BotCommand("raqam",   "🔢 Konkursdagi raqamim"),
    BotCommand("sinov",   "🧩 Bilim testi"),
    BotCommand("shaxs",   "🧠 Shaxsiyat testi"),
    BotCommand("kanallar","📣 Kanallarimiz"),
]
ADMIN_COMMANDS = PUBLIC_COMMANDS + [
    BotCommand("agent_status",  "📊 Agent holati"),
    BotCommand("agent_run",     "🔍 Agentni hozir ishga tushirish"),
    BotCommand("agent_sources", "📡 Agent manbalari"),
    BotCommand("agent_requeue", "♻️ Maqolalarni navbatga qaytarish"),
    BotCommand("agent_pause",   "⏸ Agentni to'xtatish"),
    BotCommand("agent_resume",  "▶️ Agentni davom ettirish"),
    BotCommand("stats",  "📈 Bot statistikasi"),
    BotCommand("xabar",  "📢 Hammaga xabar yuborish"),
    BotCommand("elon2",  "📚 Konkurs e'lonini joylash"),
    BotCommand("golib2", "🎉 Konkurs g'olibini tanlash"),
    BotCommand("reset2", "🧹 Konkursni tozalash"),
]


async def _setup_commands(context: ContextTypes.DEFAULT_TYPE):
    """Menyu: hammaga ommaviy buyruqlar, adminga to'liq ro'yxat."""
    try:
        await context.bot.set_my_commands(
            PUBLIC_COMMANDS, scope=BotCommandScopeDefault())
        await context.bot.set_my_commands(
            ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=ADMIN_ID))
        log.info("Buyruqlar menyusi o'rnatildi (%d ommaviy, %d admin).",
                 len(PUBLIC_COMMANDS), len(ADMIN_COMMANDS))
    except Exception as e:
        log.warning("Menyu o'rnatishda xato: %s", e)


# ======================================================================
# ULASH NUQTASI — bot.py dan chaqiriladi
# ======================================================================
def register(app: Application):
    """Mavjud Application ga agent buyruqlari, tugmalari va jadvalini qo'shadi."""
    if not ADMIN_ID:
        log.warning("ADMIN_ID berilmagan — agent o'chirilgan holda qoladi.")
        return
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY berilmagan — agent o'chirilgan holda qoladi.")
        return

    app.add_handler(CommandHandler("agent_status", cmd_status))
    app.add_handler(CommandHandler("agent_run", cmd_run))
    app.add_handler(CommandHandler("agent_pause", cmd_pause))
    app.add_handler(CommandHandler("agent_resume", cmd_resume))
    app.add_handler(CommandHandler("agent_requeue", cmd_requeue))
    app.add_handler(CommandHandler("agent_sources", cmd_sources))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(agpub|agpubv|agskip):\d+$"))

    if app.job_queue is None:
        log.error("JobQueue yo'q! requirements.txt da "
                  "python-telegram-bot[job-queue] bo'lishi kerak.")
    else:
        app.job_queue.run_daily(run_agent, time=dtime(7, 0, tzinfo=TZ), name="agent_morning")
        app.job_queue.run_daily(evening_reminder, time=dtime(20, 0, tzinfo=TZ), name="agent_evening")
        app.job_queue.run_once(_setup_commands, when=3, name="setup_commands")

    log.info("AI agent ulandi: 07:00 avtomatik, /agent_run — qo'lda. Aisha TTS: %s",
             "yoqilgan 🎙" if AISHA_API_KEY else "o'chiq (AISHA_API_KEY berilmagan)")
