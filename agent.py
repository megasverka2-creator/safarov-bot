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
    pillow>=10.1

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

import html
import json
import logging
import os
import re
import sqlite3
from io import BytesIO
from datetime import datetime, time as dtime, date, timedelta
from zoneinfo import ZoneInfo

import feedparser
import httpx
import trafilatura
from openai import OpenAI

try:  # Pillow — post uchun rasm-karta chizadi. Bo'lmasa agent rasmsiz ishlayveradi.
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ======================================================================
# SOZLAMALAR (hammasi Railway Variables orqali boshqariladi)
# ======================================================================
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0") or "0")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@safaroov_blog")
# RICH (maqola) formati: 1 = yoqilgan (default), 0 = eski usul.
# Xato bo'lsa kod o'zi eski usulga tushadi — post baribir chiqadi.
RICH_POSTS = os.environ.get("RICH_POSTS", "1").strip().lower() \
    not in ("0", "false", "off", "no", "")
# Rasm ombori: rasm shu yerga yuklanadi va undan havola olinadi.
# Bo'sh qoldirilsa — adminning shaxsiy chatiga tushadi.
RICH_IMAGE_STORE = os.environ.get("RICH_IMAGE_STORE", "").strip()
# ======================================================================
# KO'P KANALLI MARSHRUTLASH — istalgan rubrika istalgan kanalga
# Railway Variables:
#   CHANNEL_MAP = "dunyo=@zahiradagi_jurnalist, uzb=@zahiradagi_jurnalist, sport=@zahiradagi_jurnalist, mutolaa=@mutolaachidan"
#   (yozilmagan rubrikalar asosiy CHANNEL_ID ga chiqadi)
#   CHANNEL2_ID = eski usul ham ishlaydi: dunyo/uzb/sport uchun qisqa yo'l
# ======================================================================
CHANNEL2_ID = os.environ.get("CHANNEL2_ID", "")
RUBRIKA_CHANNELS = {}
for _pair in os.environ.get("CHANNEL_MAP", "").split(","):
    if "=" in _pair:
        _r, _c = _pair.split("=", 1)
        _r, _c = _r.strip(), _c.strip()
        if _r and _c:
            RUBRIKA_CHANNELS[_r] = _c
if CHANNEL2_ID:
    for _r in ("dunyo", "uzb", "sport"):
        RUBRIKA_CHANNELS.setdefault(_r, CHANNEL2_ID)

def _channel_for(rubrika):
    return RUBRIKA_CHANNELS.get(rubrika, CHANNEL_ID)

def _brand_for(rubrika):
    """Karta pastidagi brend: rubrika qaysi kanalga chiqsa, o'sha nom."""
    chan = RUBRIKA_CHANNELS.get(rubrika)
    if chan:
        h = chan.lstrip("@")
        return (h.replace("_", " ").upper(), f"t.me/{h}")
    return ("SAFAROV BLOG", "t.me/safaroov_blog")
# Baza botdagi boshqa fayllar (users.json) bilan bir joyda — Railway volume'da saqlanadi:
DB_PATH = os.environ.get("DB_PATH",
                         os.path.join(os.environ.get("DATA_DIR", "."), "agent.db"))
# Aisha AI (o'zbekcha ovoz) — kalit berilsa postlarda 🎙 Ovozli tugmasi paydo bo'ladi
AISHA_API_KEY = os.environ.get("AISHA_API_KEY", "")
AISHA_BASE = "https://back.aisha.group"

TZ = ZoneInfo("Asia/Tashkent")
# --- AI modellari (Railway Variables orqali kod o'zgartirmasdan almashtiriladi) ---
# AI_MODEL_FAST  — arzon ishlar: saralash, surat so'rovi, ovoz routeri
# AI_MODEL_SMART — sifat muhim ishlar: post yozish (tarjima!)
MODEL_FAST = os.environ.get("AI_MODEL_FAST", "gpt-5.4-nano")
MODEL_SMART = os.environ.get("AI_MODEL_SMART", "gpt-5.6-luna")
MODEL = MODEL_FAST  # eski nom bilan moslik
MIN_SCORE = 6                  # nomzodlik chegarasi (siz baribir qo'lda tanlaysiz)
MAX_POSTS_PER_DAY = int(os.environ.get("MAX_POSTS_PER_DAY", "12"))
# Vaqtincha o'chirilgan rubrikalar (Railway: RUBRIKA_OFF=dunyo,uzb,sport,smm).
# O'chirilgan rubrika: RSS ham o'qilmaydi, saralanmaydi, post ham yozilmaydi —
# ya'ni API xarajati to'liq to'xtaydi. Kanal va manbalar joyida qoladi.
RUBRIKA_OFF = {r.strip().lower() for r in
               os.environ.get("RUBRIKA_OFF", "").split(",") if r.strip()}
MAX_PER_RUBRIKA = int(os.environ.get("MAX_PER_RUBRIKA", "2"))
# 1 qilinsa — har rubrikadan kuniga bittadan nomzod (xarajat ~2 barobar kam)
MAX_API_CALLS_PER_DAY = int(os.environ.get("MAX_API_CALLS_PER_DAY", "150"))
# Railway Variables orqali oshirish mumkin. To'plamli saralashdan keyin
# 150 odatda yetadi; kerak bo'lsa 300 qilinsa ham xarajat kuniga bir necha sent.
SCORING_RESERVE = MAX_POSTS_PER_DAY  # post yozish uchun doim zaxira chaqiruv qoladi
ARTICLE_CHAR_LIMIT = 8000
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"

# Rubrikalar: ai · rivojlanish · podcast · dunyo (jahon yangiliklari) · mutolaa (kitob)
SOURCES = [
    # --- 🗞 AI va marketing ---
    ("OpenAI",        "https://openai.com/news/rss.xml",                               "ai"),
    ("Anthropic",     "scrape:anthropic",                                              "ai"),
    ("Google AI",     "https://blog.google/technology/ai/rss/",                        "ai"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "ai"),
    # --- 📈 SMM va marketing (@marketing_bysafarov) ---
    ("HubSpot",       "https://blog.hubspot.com/marketing/rss.xml",                    "smm"),
    ("Social Media Today", "https://www.socialmediatoday.com/feeds/news/",             "smm"),
    ("Buffer",        "https://buffer.com/resources/rss/",                             "smm"),
    ("Sprout Social", "https://sproutsocial.com/insights/feed/",                       "smm"),
    ("TechCrunch Social", "https://techcrunch.com/category/social/feed/",              "smm"),
    # --- 🌱 Shaxsiy rivojlanish ---
    ("Farnam Street", "https://fs.blog/feed/",                                         "rivojlanish"),
    ("Mark Manson",   "https://markmanson.net/feed",                                   "rivojlanish"),
    ("HBR",           "http://feeds.hbr.org/harvardbusiness",                          "rivojlanish"),
    # --- 🎧 Podcast va video ---
    ("TED Talks",     "https://feeds.feedburner.com/TEDTalks_audio",                   "podcast"),
    ("Huberman Lab",  "https://feeds.megaphone.fm/hubermanlab",                        "podcast"),
    ("Tim Ferriss",   "https://rss.art19.com/tim-ferriss-show",                        "podcast"),
    # --- 🌍 Dunyo yangiliklari (faqat nufuzli, tekshirilgan tahririyatlar) ---
    ("BBC World",     "https://feeds.bbci.co.uk/news/world/rss.xml",                   "dunyo"),
    ("Al Jazeera",    "https://www.aljazeera.com/xml/rss/all.xml",                     "dunyo"),
    ("NYT World",     "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",        "dunyo"),
    # --- 🇺🇿 O'zbekiston yangiliklari ---
    ("Gazeta.uz",     "https://www.gazeta.uz/uz/rss/",                                 "uzb"),
    ("Spot.uz",       "https://www.spot.uz/rss/",                                      "uzb"),
    # --- ⚽ Sport ---
    ("BBC Futbol",    "https://feeds.bbci.co.uk/sport/football/rss.xml",               "sport"),
    ("BBC Sport",     "https://feeds.bbci.co.uk/sport/rss.xml",                        "sport"),
    # --- 📱 Texno: gadjetlar va harbiy texnologiyalar ---
    ("Engadget",      "https://www.engadget.com/rss.xml",                              "texno"),
    ("GSMArena",      "https://www.gsmarena.com/rss-news-reviews.php3",                "texno"),
    ("Defense News",  "https://www.defensenews.com/arc/outboundfeeds/rss/",            "texno"),
    # --- 🕌 Islom olami yangiliklari ---
    ("Arab News",     "https://www.arabnews.com/rss.xml",                              "islom"),
    ("Anadolu",       "https://www.aa.com.tr/en/rss/default?cat=live",                 "islom"),
    ("Middle East Eye","https://www.middleeasteye.net/rss",                            "islom"),
    # --- 📚 Kitob va mutolaa ---
    ("Literary Hub",  "https://lithub.com/feed/",                                      "mutolaa"),
    ("Austin Kleon",  "https://austinkleon.com/feed/",                                 "mutolaa"),
    ("Ryan Holiday",  "https://ryanholiday.net/feed/",                                 "mutolaa"),
]

RUBRIKA_EMOJI = {"ai": "🗞", "rivojlanish": "🌱", "podcast": "🎧",
                 "dunyo": "🌍", "mutolaa": "📚", "uzb": "🇺🇿", "sport": "⚽", "texno": "📱", "islom": "🕌", "smm": "📈"}
RUBRIKA_NOMI = {"ai": "AI va marketing", "rivojlanish": "Shaxsiy rivojlanish",
                "podcast": "Podcast va video", "dunyo": "Dunyo yangiliklari",
                "mutolaa": "Kitob va mutolaa",
                "uzb": "O'zbekiston", "sport": "Sport", "texno": "Texno olami",
                "islom": "Islom olami",
                "smm": "SMM va marketing"}

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


def posts_today(conn):
    """Bugun yozilgan post-nomzodlar soni (kunlik, run bo'yicha emas)."""
    today = date.today().isoformat()
    if meta_get(conn, "post_day") != today:
        meta_set(conn, "post_day", today)
        meta_set(conn, "post_count", "0")
    return int(meta_get(conn, "post_count", "0"))


def post_inc(conn):
    meta_set(conn, "post_count", posts_today(conn) + 1)


# ======================================================================
# AI QATLAMI
# ======================================================================
SCORE_PROMPT = """Sen @safaroov_blog Telegram kanalining kuratorisan. Kanal yo'nalishlari: \
(1) AI va marketing, (2) shaxsiy rivojlanish, (3) muhim jahon yangiliklari, \
(4) kitob va mutolaa, (5) podcast, (6) O'zbekiston yangiliklari, (7) sport \
(ayniqsa futbol va O'zbekistonga aloqador voqealar), (8) texno olami — \
gadjetlar, yangi qurilmalar, harbiy texnologiyalar, (9) Islom olami \
yangiliklari — musulmon mamlakatlar va jamoalardagi muhim voqealar (Haj, \
xalqaro sammitlar, iqtisodiy-madaniy hodisalar). Islom olami uchun past baho: \
mazhabiy bahs-munozaralar, ichki nizolarni qo'zg'aydigan materiallar. Auditoriya: O'zbekistondagi marketologlar, kichik \
biznes egalari, o'z ustida ishlaydigan yoshlar. Auditoriyaning asosiy qismi musulmonlar — \
material hurmatli va ishonchli bo'lishi shart.

Quyidagi material sarlavhasi va annotatsiyasiga qarab baho ber.

RUBRIKA MOSLIGI (birinchi tekshiriladi): material qaysi rubrikaga tegishli \
ekani "Rubrika:" qatorida beriladi. Agar material o'sha rubrika mavzusiga \
BEVOSITA tegishli bo'lmasa — baho 3 dan oshmasin, mazmuni qanchalik yaxshi \
bo'lmasin. Xususan "islom" rubrikasi FAQAT islom olami va musulmon \
mamlakatlariga bevosita aloqador xabarlar uchun. Umumiy jahon iqtisodi, birja \
narxlari, boshqa mintaqalar siyosati, umumiy ob-havo yoki sport xabarlari bu \
rubrikaga TUSHMAYDI — ular manba agentligi musulmon davlatiniki bo'lsa ham \
past baho oladi. Masalan "jahon bozorida bug'doy narxi oshdi" — bu "islom" \
rubrikasi EMAS.
Yuqori baho: amaliy foyda, yangi vosita/model, real keys, kuchli hayotiy saboq, \
ilmiy asosli maslahat, dunyodagi chinakam muhim voqea (siyosat, iqtisod — keng ommaga \
ta'sir qiladigan), mutolaa madaniyati va kitoblar haqida qiziqarli material. \
Past baho: tor ilmiy mavzu, mahalliy ahamiyatsiz xabar, reklama, takror, suv quyilgan \
umumiy gap, mish-mish yoki tasdiqlanmagan xabar, shov-shuvli sariq matbuot uslubi, \
faqat dahshat va qo'rquvga qurilgan xabar.

FAQAT JSON qaytar, boshqa hech narsa yozma:
{"score": 0dan 10gacha butun son, "sabab": "bir gap"}"""

_UMUMIY_QOIDALAR = """Qat'iy qoidalar:
1. Bu TARJIMA EMAS — o'z so'zing bilan qisqa xulosa. Asosiy matn 500 belgidan oshmasin.
2. Materialda bo'lmagan fakt yoki raqamni QO'SHMA.
3. SARLAVHA to'liq tabiiy o'zbek tilida bo'lsin. Inglizcha gap tuzilishini \
ko'chirma ("AI-enabled" → "AI-lekin" kabi so'zma-so'z tarjima TAQIQLANADI). \
Yomon: "Yangi AI-lekin himoyada: Savi Security". \
Yaxshi: "Savi Security: AI endi firibgarlardan himoya qiladi".
4. Kompaniya, mahsulot, model va ODAM nomlari MANBADAGIDEK qoladi \
(Google, Chelsea, Gemini, Mark Dowd, Abbas Araghchi). Ismni o'zbekchalashtirishga \
URINMA — noto'g'ri o'zgartirilgan ism jiddiy xato hisoblanadi. \
Yomon: "Mark Dowd" → "Mark Daud". \
Faqat azaldan o'zbekcha shakli bor joy nomlari o'zbekcha yoziladi \
(Misr, Makka, Madina, Istanbul).
4a. VALYUTA belgisi emas, so'z bilan yoziladi. \
Yomon: "£117 mln", "$20". Yaxshi: "117 mln funt sterling", "20 dollar".
4b. RUSCHA-INGLIZCHA KO'CHIRMA IBORALAR TAQIQ. \
Yomon: "bayonot yangradi" (прозвучало). Yaxshi: "bayonot e'lon qilindi".
4c. TEXNIKA ATAMALARI o'zbek texno matnlaridagidek yoziladi. \
Yomon: "mA·soat" (ruscha мА·ч), "talqini" (versiya ma'nosida). \
Yaxshi: "mAh", "versiyasi". Vt, GB, MP, Hz — shu holicha qoladi.
5. Terminlar: birinchi ishlatishda o'zbekcha + qavsda asli. \
Masalan: "katta til modeli (LLM)".
6. Sonlar va sanalar o'zbekcha: 15-iyul, 3 mln, 40 foiz (yoki 40%).
7. Auditoriya asosan musulmonlar — ohang doim hurmatli. Behayo, haqoratli yoki \
diniy tuyg'ularga tegadigan ifodalar ishlatilmasin. Diniy va siyosiy mavzularda \
qat'iy betaraf pozitsiya, hech bir tomonga baho berilmasin.
8. Matn oson o'qilsin: qisqa gaplar (o'rtacha 8-14 so'z), qisqa xatboshilar \
(2-3 gapdan oshmasin), bitta postda bitta asosiy fikr.

TARJIMA SIFATI — TAQIQLANGAN QURILMALAR (professional tahrirchi qoidalari):
A) Bir jumlada ikkita "uchun" TAQIQ. \
Yomon: "huquqlarni buzayotgani uchun sudga tortilgani uchun". \
Yaxshi: "huquqni buzganlikda ayblanib sudga berildi".
B) Idoraviy-quruq iboralar TAQIQ: "ushbu ishda qatnashayotgan shaxslar" (→ \
"da'vogarlar"), "shuni ta'kidlash joizki" (→ olib tashla), "amalga oshirmoqda" \
(→ "qilmoqda"), "mazkur", "ushbu" (→ "bu"), "hisoblanadi" (→ "—" yoki tushirib \
qoldir), "o'z ichiga oladi" (→ "bor", "kiradi").
C) "...zarurligini anglatadi / muhimligini ko'rsatadi" kalkasi TAQIQ. \
Yomon: "ehtiyotkor bo'lish zarurligini anglatadi". \
Yaxshi: "ehtiyot bo'lish kerak" yoki "e'tiborli bo'ling".
D) Majhul nisbat ketma-ket kelmasin ("qilindi... etildi... berildi..."): kim \
qilgan bo'lsa, o'shani ega qilib yoz. Yomon: "Google tomonidan e'lon qilindi". \
Yaxshi: "Google e'lon qildi".
E) Inglizcha egalik zanjiri kalkasi TAQIQ. Yomon: "kompaniyaning AI \
platformasining o'qitish jarayonining natijalari". Yaxshi: gapni bo'lib yoz.
F) "Bo'lib," bilan cho'zilgan gaplar o'rniga ikki qisqa gap yoz.
G) Fe'lni jonlantir: "qo'llab-quvvatlashni taqdim etadi" emas — "yordam beradi"; \
"imkoniyat yaratadi" emas — "imkon beradi".
H) SARLAVHA to'liq tugallangan bo'lsin: "-gani", "-ekani", "-ligi" bilan \
TUGAMASIN. Yomon: "qizil tus dasturiy muammo ekani". \
Yaxshi: "qizil tus — dasturiy muammo" yoki "qizil tus dasturiy muammo ekan".
I) Manbada YO'Q maslahat va xulosa QO'SHMA ("...ga murojaat qiling", "...ni \
kuting" kabi tavsiyalar faqat manbada aniq aytilgan bo'lsagina yoziladi). \
Manbada yo'q tafsilotni ham qo'shma. \
Yomon (manbada "oziq-ovqat inflyatsiyasi kutilmalari" deyilgan): \
"importga bog'liq mamlakatlarda oziq-ovqat inflyatsiyasi xavfi". \
Yaxshi: "oziq-ovqat narxlariga ta'sir qilishi mumkin".
J) O'ZBEK O'QUVCHISIGA NOTANISH O'LCHOV BIRLIGI qavsda tushuntirilsin \
(bushel, funt, gallon, akr, dyuym, barrel va h.k.) — aks holda raqam ma'nosiz. \
Yomon: "7,085 dollar/bushelga yetdi". \
Yaxshi: "bir bushel (taxminan 27 kg) uchun 7,085 dollarga chiqdi". \
Slash ("/") belgisi o'rniga so'z bilan yoz.
K) TABIAT VA IQTISOD ATAMALARINI so'zma-so'z ko'chirma. \
Yomon: "issiq to'lqinlar" (heat waves), "qurg'oqchilik tashvishlari". \
Yaxshi: "jazirama issiq", "qurg'oqchilikdan xavotir".
L) "...bo'yicha" ulagichi idoraviy — imkon boricha tushirib qoldir. \
Yomon: "don eksporti bo'yicha xavotirlar kuchaydi". \
Yaxshi: "don eksportidan xavotir kuchaydi".

MAZMUNGA SODIQLIK (eng muhim bo'lim — buzilsa post yaroqsiz):
S1) HARAKAT EGASI DOIM KO'RSATILADI: kim, kimga/nimaga, qachon qildi. \
Mavhum ot bilan almashtirish TAQIQ ("voqea", "holat", "vaziyat", "hodisa", \
"ma'lum bir tomon"). \
Yomon: "Sakkiz davlat masjid hududidagi voqeani qoraladi". \
Yaxshi: "Sakkiz davlat tashqi ishlar vaziri isroilliklarning Al-Aqso \
masjidiga ommaviy kirishini qoraladi".
S2) MANBADAGI ASOSIY TALAB, RAQAM YOKI XULOSA TUSHIRILMAYDI. Postni qisqartirish \
mumkin, lekin xabarning o'zagini olib tashlab bo'lmaydi. Agar bayonotda aniq \
talab bo'lsa (masalan, biror huquqni tan olishga chaqiriq) — u yoziladi.
S3) BETARAFLIK = NISBAT BERISH, o'chirish emas. Baholovchi so'zlarni o'zingdan \
yozma, lekin tomonning so'zini nisbat bilan keltir. \
Yomon: baholovchi so'zni butunlay olib tashlash. \
Yomon: "Bu noqonuniy harakat" (o'zingdan baho). \
Yaxshi: "Bayonotda bu harakat 'noqonuniy va ekstremistik' deb atalgan".
S4) YUMSHATIB YUBORMA: manbadagi so'zning kuchi saqlansin. \
"bostirib kirish / reyd" → "kirish" emas; "ogohlantirdi" → "bildirdi" emas; \
"qat'iy qoraladi" → "e'tiroz bildirdi" emas.
S5) "Nega muhim / Bu bizga nima beradi" — O'QUVCHI UCHUN KONTEKST, manba \
jumlasining takrori EMAS. Bu yerda YANGI ma'lumot bo'lishi shart: oqibat, \
miqyos, O'zbekistonga aloqasi yoki keyingi kutilayotgan qadam. \
TEKSHIR: bu qatordagi gap sarlavha yoki yuqoridagi paragrafda allaqachon \
aytilganmi? Aytilgan bo'lsa — qatorni butunlay O'CHIR, takrorlama. \
Yomon (sarlavha "Belarusda ishlash taklif qilindi"): "Bu nimani anglatadi: \
o'zbekistonliklar Belarusda ish topish imkoniga ega". \
Yaxshi: "Bu nimani anglatadi: taklif rasmiy shartnoma asosida, ya'ni mehnat \
huquqlari himoyalangan bo'ladi" (agar manbada shunday deyilgan bo'lsa).
S6) Post o'qilgach o'quvchi quyidagilarga javob topa olsin: NIMA bo'ldi? KIM \
qildi? QAChON? NATIJA yoki TALAB nima? Bittasi yo'q bo'lsa — post qayta yoziladi.

O'Z-O'ZINI TEKSHIRISH (majburiy yakuniy qadam): postni yozib bo'lgach, har \
jumlani ovoz chiqarib o'qiyotgandek tekshir: (1) o'zbek suhbatida shunday \
deyiladimi? (2) bitta jumlada ikki "uchun"/"tomonidan"/"ushbu" yo'qmi? \
(3) jumla 20 so'zdan oshmadimi? (4) harakat egasi aniqmi — "kim nima qildi" \
ko'rinib turibdimi, mavhum ot bilan almashtirilmaganmi? (5) manbadagi asosiy \
talab, raqam yoki xulosa saqlanganmi? (6) manbada bo'lmagan tafsilot \
qo'shilmaganmi? Muammoli jumlani QAYTA yoz, keyin yakuniy matnni qaytar.

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

#ai · @safaroov_blog""",

    "rivojlanish": """Sen @safaroov_blog Telegram kanalining muharririsan. Kanal tili: \
o'zbek. Ohang: samimiy, ilhomlantiruvchi, lekin quruq motivatsiyasiz — aniq fikr va amaliy xulosa muhim.

Quyidagi inglizcha maqola asosida Shaxsiy rivojlanish rubrikasi uchun POST yoz.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🌱 [Tabiiy o'zbekcha sarlavha]

[2-4 gap: maqolaning asosiy g'oyasi — hayotiy va tushunarli tilda]

💡 Bugunoq sinab ko'ring: [1-2 gap — bitta aniq amaliy qadam]

🔗 Manba: {url}

#rivojlanish · @safaroov_blog""",

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

#podkast · @safaroov_blog""",

    "dunyo": """Sen @safaroov_blog Telegram kanalining xalqaro yangiliklar muharririsan. \
Kanal tili: o'zbek. Ohang: xolis, vazmin, ishonchli — xuddi jiddiy axborot agentligi kabi.

Quyidagi inglizcha maqola asosida Dunyo yangiliklari rubrikasi uchun POST yoz.

QO'SHIMCHA QAT'IY TALABLAR (jahon yangiliklari uchun):
- FAQAT manbada aniq tasdiqlangan faktlar. Taxmin, bashorat va mish-mish YO'Q.
- Hech bir davlat, xalq, din yoki siyosiy tomonga baho berma, ayblama, oqlama — \
faqat nima bo'lganini ayt.
- Urush va fojia mavzularida dahshatli tafsilotlar (qon, jarohat tasviri) berilmasin — \
voqea mohiyati yetarli.
- Postda kim xabar berganini aniq ko'rsat (masalan: "BBC xabariga ko'ra...").
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🌍 [Xolis, aniq o'zbekcha sarlavha]

[2-4 gap: nima bo'ldi — faqat tasdiqlangan faktlar, manba nomi bilan]

📌 Nega muhim: [1-2 gap — bu voqea dunyoga yoki mintaqamizga qanday ta'sir qilishi mumkin]

🔗 Manba: {url}

#dunyo · @safaroov_blog""",

    "mutolaa": """Sen @safaroov_blog Telegram kanalining kitob va mutolaa rubrikasi \
muharririsan. Kanal tili: o'zbek. Ohang: iliq, kitobsevar do'st kabi — mutolaaga \
mehr uyg'otadigan.

Quyidagi inglizcha maqola asosida Kitob va mutolaa rubrikasi uchun POST yoz. \
Maqola kitob, yozuvchi, o'qish odati yoki mutolaa madaniyati haqida bo'lishi mumkin.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

📚 [Qiziqarli o'zbekcha sarlavha]

[2-3 gap: maqolaning asosiy g'oyasi — kitobxonga qiziq bo'ladigan tilda]

✨ Mutolaa uchun: [1-2 gap — kitob tavsiyasi yoki o'qish odatiga oid amaliy maslahat]

🔗 Manba: {url}

#mutolaa · @safaroov_blog""",

    "uzb": """Sen @safaroov_blog Telegram kanalining O'zbekiston yangiliklari \
muharririsan. Kanal tili: o'zbek (lotin alifbosi). Ohang: xolis, aniq, xalqchil.

Quyidagi maqola (o'zbek-kirill yoki rus tilida bo'lishi mumkin) asosida \
O'zbekiston rubrikasi uchun POST yoz. Manba kirill alifbosida bo'lsa, lotinga \
tabiiy o'gir.

QO'SHIMCHA QAT'IY TALABLAR (mahalliy yangiliklar uchun):
- FAQAT manbada tasdiqlangan faktlar; mish-mish va taxmin YO'Q.
- Siyosiy mavzularda qat'iy betaraflik: shaxslar va idoralarga baho berma, \
maqtama, ayblama — faqat nima bo'lganini ayt.
- Fojia va jinoyat xabarlarida dahshatli tafsilotlar berilmasin, ehtirom saqlansin.
- O'quvchiga amaliy foydasi bo'lsa (yangi qoida, imkoniyat, muddat) — shuni \
alohida ochiq ayt.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🇺🇿 [Aniq, xolis sarlavha]

[2-4 gap: nima bo'ldi — faqat faktlar]

📌 Bu nimani anglatadi: [1-2 gap — oddiy odamga qanday ta'sir qiladi yoki nima qilish kerak]

🔗 Manba: {url}

#uzbekiston · @safaroov_blog""",

    "sport": """Sen @safaroov_blog Telegram kanalining sport muharririsan. \
Kanal tili: o'zbek. Ohang: jonli, ishtiyoqli, lekin hurmatli — haqiqiy sport \
sharhlovchisi kabi. Auditoriya futbolni ayniqsa sevadi va O'zbekiston terma \
jamoasi hamda o'zbek sportchilariga aloqador voqealarni intiqlik bilan kutadi.

Quyidagi inglizcha maqola asosida Sport rubrikasi uchun POST yoz.

QO'SHIMCHA TALABLAR (sport uchun):
- Hisob, natija va raqamlar aniq bo'lsin — sport o'quvchisi xatoni darrov sezadi.
- Jamoa, klub va sportchi nomlari asl holicha (masalan: Real Madrid, Arsenal).
- O'zbekistonga aloqasi bo'lsa (o'zbek futbolchisi, raqib jamoa, terma) — buni \
albatta birinchi o'ringa chiqar.
- Muxlislarni haqorat qiladigan yoki masxara ohangidagi ifodalar TAQIQ.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

⚽ [Jonli, aniq sarlavha]

[2-3 gap: nima bo'ldi — natija, asosiy voqea, qahramon]

🔥 Qiziq jihati: [1 gap — o'yinning eng esda qolarli lahzasi yoki konteksti]

🔗 Manba: {url}

#sport · @safaroov_blog""",

    "texno": """Sen @safaroov_blog Telegram kanalining Texno olami rubrikasi \
muharririsan. Kanal tili: o'zbek. Ohang: qiziquvchan, aniq, texnologiyani \
sevadigan sharhlovchi kabi — lekin quruq spets-varaq emas, jonli hikoya.

Quyidagi inglizcha maqola asosida Texno rubrikasi uchun POST yoz. Mavzular: \
gadjetlar (telefon, noutbuk, soat), yangi qurilmalar, ilmiy-texnik yutuqlar, \
harbiy texnologiyalar.

QO'SHIMCHA TALABLAR (texno uchun):
- Texnik ko'rsatkichlar (narx, quvvat, o'lcham, sana) manbadagidek ANIQ bo'lsin.
- Qurilma va brend nomlari asl holicha: iPhone, Samsung Galaxy, F-35.
- O'quvchiga "bu menga nima" burchagini ber: qachon chiqadi, taxminan qancha \
turadi, nimasi bilan ajralib turadi.
- HARBIY mavzularda: faqat texnologiya faktlari, xolis ohang. Urushni yoki \
qurolni ulug'lash, biror tomonni qo'llash TAQIQ. Qurbonlar tafsiloti \
berilmasin. Texnika — mavzu, urush — emas.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

📱 [Qiziqarli, aniq sarlavha]

[2-3 gap: nima taqdim etildi/kashf qilindi — asosiy faktlar va raqamlar]

⚙️ Ajralib turadigan jihati: [1-2 gap — eng muhim xususiyat yoki nima uchun bu muhim]

🔗 Manba: {url}

#texno · @safaroov_blog""",

    "islom": """Sen @safaroov_blog loyihasining Islom olami yangiliklari \
muharririsan. Kanal tili: o'zbek. Ohang: hurmatli, vazmin, xolis — jiddiy \
axborot agentligi kabi. Auditoriya — musulmonlar; ular ishonchli, tasdiqlangan \
xabar kutadi.

Quyidagi inglizcha maqola asosida Islom olami rubrikasi uchun POST yoz. \
Mavzular: musulmon mamlakatlar va jamoalardagi muhim voqealar — Haj va Umra \
mavsumi, xalqaro sammitlar, iqtisodiy-madaniy hodisalar, ilm-fan va ta'lim, \
musulmon jamoalari hayoti.

ENG QAT'IY TALABLAR (bu rubrika uchun alohida mas'uliyat):
- Bu YANGILIK, diniy ta'limot EMAS: hech qanday diniy hukm, fatvo, ibodat \
ko'rsatmasi, oyat-hadis talqini YOZMA — faqat voqea faktlari.
- Mazhab, oqim va davlatlararo bahslarda MUTLAQO betaraf tur: hech bir \
tomonni qo'llama, ayblama, baholama. Ichki nizolarni qo'zg'aydigan ohang TAQIQ.
- LEKIN BETARAFLIK — FAKTNI O'CHIRISH EMAS. Kim nima qilgani, qachon va qayerda \
bo'lgani ANIQ yoziladi. Baho beruvchi so'zlar faqat nisbat bilan keltiriladi \
("bayonotda ... deb atalgan", "vazirlar ... deb hisoblaydi"). Voqeani "hodisa", \
"vaziyat" kabi mavhum so'z bilan almashtirish TAQIQ — o'quvchi nima bo'lganini \
tushunmay qolsa, post vazifasini bajarmagan bo'ladi.
- Muqaddas tushunchalar haqida faqat hurmatli shakllarda yoz.
- Diniy sanalar (Ramazon, hayit boshlanishi kabi) faqat manbada rasmiy e'lon \
sifatida kelgan bo'lsa yoziladi, taxmin qilinmaydi.
- Fojia xabarlarida dahshatli tafsilotlar berilmasin, qurbonlar ehtirom bilan \
tilga olinsin.
- Manba nomini ko'rsat ("Anadolu xabariga ko'ra...").
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

🕌 [Hurmatli, xolis sarlavha]

[2-4 gap: nima bo'ldi — faqat tasdiqlangan faktlar, manba nomi bilan]

📌 Nega muhim: [1-2 gap — bu voqea musulmon olami yoki yurtimiz uchun qanday ahamiyatga ega]

🔗 Manba: {url}

#islomolami · @safaroov_blog""",

    "smm": """Sen @marketing_bysafarov kanali muharririsan. Auditoriya — SMM va \
marketing MUTAXASSISLARI (havaskorlar emas).

Shu kanalning uslubi:
- Sarlavhada EMOJI YO'Q. Sarlavha — qisqa, tasdiqlovchi gap (40-60 belgi): \
nima bo'lganini aytadi. Yomon: "SMM haqida qiziq yangilik". \
Yaxshi: "LinkedIn post vaqti: 4,8 mln post tahlili".
- Asosni tushuntirma: SMM nima, algoritm qanday ishlaydi — auditoriya biladi. \
Darrov mohiyatga o't.
- RAQAM VA SANA majburiy: platforma nomi, tadqiqot hajmi, o'zgarish sanasi.
- "Nega muhim" o'rniga "Nima qilish kerak" — mutaxassisga AMAL kerak, kontekst \
emas. Bu qatorda aniq qadam bo'lsin: nimani o'zgartirsin, nimani sinab ko'rsin.
- Imkon bo'lsa O'zbekiston bozoriga bog'la (vaqt mintaqasi, mahalliy \
platformalar), lekin manbada yo'q narsani TO'QIMA.
""" + _UMUMIY_QOIDALAR + """
Shablon (kvadrat qavslarni o'z matning bilan almashtir):

[Sarlavha — emojisiz, qisqa, tasdiqlovchi gap]

[2-4 gap: nima aniqlandi yoki o'zgardi — raqam va manba nomi bilan]

Nima qilish kerak: [1-2 gap — aniq amaliy qadam]

🔗 Manba: {url}

#marketing · @marketing_bysafarov""",
}


def ai_score(conn, title, summary, rubrika=None):
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    sov = f"Rubrika: {rubrika or 'nomaʼlum'}\nSarlavha: {title}\n" \
          f"Annotatsiya: {summary[:1000]}"
    resp = ai_client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        max_completion_tokens=100,
        messages=[
            {"role": "system", "content": SCORE_PROMPT},
            {"role": "user", "content": sov},
        ],
    )
    try:
        return int(json.loads(resp.choices[0].message.content).get("score", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0


SCORE_BATCH = 10      # bitta so'rovda nechta maqola baholanadi


def ai_score_batch(conn, items):
    """Bir nechta maqolani BITTA so'rovda baholaydi — chaqiruvni ~10 barobar tejaydi.
    items: [(url, title, summary, rubrika), ...]
    Qaytaradi: {url: ball}. Xato bo'lsa bo'sh lug'at (chaqiruvchi tomon hal qiladi)."""
    if not items:
        return {}
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    satrlar = []
    for i, (_, title, summary, rubrika) in enumerate(items, 1):
        satrlar.append(f"[{i}] Rubrika: {rubrika or 'nomaʼlum'}\n"
                       f"Sarlavha: {title}\n"
                       f"Annotatsiya: {summary[:400]}")
    sov = ("Quyidagi materiallarni birma-bir bahola. Har biri uchun alohida ball ber.\n\n"
           + "\n\n".join(satrlar) +
           '\n\nJavobni shu ko\'rinishda qaytar: {"ballar": [{"n": 1, "score": 7}, ...]}'
           "\nHar bir raqam uchun bittadan ball bo'lishi shart.")
    try:
        resp = ai_client().chat.completions.create(
            model=MODEL,
            response_format={"type": "json_object"},
            max_completion_tokens=60 * len(items) + 100,
            messages=[
                {"role": "system", "content": SCORE_PROMPT},
                {"role": "user", "content": sov},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        log.warning("To'plamli saralash xatosi: %s", e)
        return {}
    natija = {}
    for el in (data.get("ballar") or []):
        try:
            n = int(el.get("n", 0))
            if 1 <= n <= len(items):
                natija[items[n - 1][0]] = int(el.get("score", 0))
        except (TypeError, ValueError):
            continue
    return natija


POLISH_SOURCE_LIMIT = 2000     # tahrirchiga beriladigan manba qismi (belgi)

EDIT_PROMPT_SOURCE = """Sen o'zbek nashrining MAS'UL MUHARRIRISAN. Senga ikki \
matn beriladi: inglizcha MANBA va uning asosida yozilgan O'ZBEKCHA POST. \
Vazifang — postni manba bilan solishtirib, xatolarini tuzatish.

A. FAKT TEKSHIRUVI (birinchi navbatda):
1. RAQAMLAR: summa, foiz, sana, miqdor, muddat manbaga mos keladimi? Mos \
kelmasa — manbadagisiga to'g'rila.
2. ISM VA NOMLAR: kim nima qilgani chalkashib ketmaganmi? Tashkilot nomi \
to'g'rimi?
3. TUSHIB QOLGAN KALIT SO'Z: manbadagi ma'noni o'zgartiradigan so'z postda \
bormi? Masalan "consecutive" (ketma-ket), "warned" (ogohlantirdi), "urged" \
(chaqirdi), "denied" (rad etdi), "alleged" (da'vo qilinmoqda), "may/could" \
(mumkin). Bunday so'z tushib qolgan bo'lsa — QAYTA KIRIT.
4. SARLAVHA xabarning o'zagini aks ettiradimi? Manbadagi asosiy jihat \
sarlavhada yo'q bo'lsa — sarlavhani to'g'rila. \
Yomon: "13-kecha zarba berdi" (ketma-ketlik yo'qolgan). \
Yaxshi: "ketma-ket 13-kecha zarba berdi".
5. MANBADA YO'Q narsa qo'shilganmi? Qo'shilgan bo'lsa — o'chir.
6. KUCHI YUMSHATILGANMI? "raid/incursion" → "kirish" emas, "bostirib kirish"; \
"condemned" → "e'tiroz bildirdi" emas, "qoraladi".

B. TIL TAHRIRI:
1. Noto'g'ri so'z yasalishi: "Uganda ayolasi" → "ugandalik ayol".
2. Joy nomlarida ortiqcha apostrof: "Uganda'da" → "Ugandada".
3. "Ushbu", "mazkur" → "bu"; "hisoblanadi" → tushirib qoldir.
4. Idoraviy fe'llar: "amalga oshirmoqda" → "qilmoqda".
5. Bir jumlada ikkita "uchun"/"tomonidan" — qayta tuz.
6. 20 so'zdan uzun jumlani bo'l.
7. Sarlavha "-gani/-ekani/-ligi" bilan tugamasin.
8. Mavhum ot aniq harakat o'rnida turmasin ("voqea", "holat", "vaziyat").
9. Ruscha-inglizcha ko'chirmalar: "yangradi" (прозвучало) → "e'lon qilindi"; \
"issiq to'lqinlar" → "jazirama issiq".
10. ISMLAR MANBADAGIDEK qolsin — o'zbekchalashtirma. \
Yomon: "Mark Dowd" → "Mark Daud". Ism buzilishi jiddiy xato.
11. Valyuta so'z bilan: "£117 mln" → "117 mln funt sterling"; "$20" → \
"20 dollar"; "€5 mln" → "5 mln yevro".
12. O'zbek o'quvchisiga notanish o'lchov birligi qavsda tushuntirilsin \
(bushel, funt, gallon, akr, barrel).
13. Texnika atamalari: "mA·soat" → "mAh"; "talqini" (versiya ma'nosida) → \
"versiyasi". Vt, GB, MP, Hz — shu holicha.
14. KOMPANIYA VA TASHKILOT NOMI tushib qolmasin: manbada aniq kompaniya \
aytilgan bo'lsa, postda ham aytilsin. \
Yomon: "AI cheklovlari" (kim cheklagani noma'lum). \
Yaxshi: "OpenAI va Anthropic cheklovlari".

TEGMA: emoji, qatorlar tartibi, havolalar, hashtag, manba nomi, kompaniya va \
mahsulot nomlari (Google, Chelsea, Gemini — asl holicha).
MUHIM: postni qayta yozma, uzaytirma — faqat xato joyini tuzat.
FAQAT tuzatilgan post matnini qaytar, izohsiz."""


EDIT_PROMPT = """Sen o'zbek tilining professional muharririsan. Quyida Telegram \
post berilgan. Vazifang: MAZMUNIGA TEGMASDAN faqat TILINI tuzatish.

Tuzatiladigan xatolar:
1. Noto'g'ri so'z yasalishi: "Uganda ayolasi" → "ugandalik ayol"; davlat/millat \
sifatlari "-lik" bilan yasaladi.
2. Joy nomlarida ortiqcha apostrof: "Uganda'da" → "Ugandada", "Toshkent'ga" → \
"Toshkentga".
3. "Ushbu", "mazkur" → "bu"; "hisoblanadi" → tushirib qoldir yoki "—".
4. Idoraviy fe'llar: "taqdim etmoqda" → "bermoqda/ochmoqda", "amalga \
oshirmoqda" → "qilmoqda".
5. Buzuq boshqaruv: "ayollarga imkoniyatlarni oshiradi" → "ayollarning \
imkoniyatlarini kengaytiradi" yoki "ayollarga imkon yaratadi".
6. Xato o'zlashmalar: "briquet" → "briket"; "charcoal" ma'nosida "kuydirilgan \
yoqilg'i" → "pista ko'mir".
7. Bir jumlada ikkita "uchun"/"tomonidan" — qayta tuz.
8. G'aliz yoki 20 so'zdan uzun jumlalarni bo'lib, tabiiy so'zlashuv ohangiga \
keltir.
9. Sarlavha "-gani/-ekani/-ligi" bilan tugagan bo'lsa, tugallangan shaklga \
keltir: "muammo ekani" → "muammo ekan" yoki "— muammo".
10. MAVHUMLIK: agar sarlavha yoki matnda "voqea", "holat", "vaziyat", "hodisa" \
kabi mavhum so'z aniq harakat o'rniga ishlatilgan bo'lsa va matnning o'zida \
aniqrog'i bor bo'lsa — o'shanga almashtir. Matnda ham aniqlik bo'lmasa, \
tegma (o'zingdan fakt QO'SHMA).
11. Kuchini yo'qotgan fe'llarni tikla: "bildirdi" → manbada ogohlantirish \
bo'lsa "ogohlantirdi"; "e'tiroz bildirdi" → qoralash bo'lsa "qoraladi". \
Bunda faqat matnning o'zidagi ma'noga tayan.

TEGMA: emoji, tuzilma (qatorlar tartibi), havolalar, hashtag, manba nomi, \
raqamlar, atoqli otlar (kompaniya/odam/tashabbus nomlari asl holicha).
FAQAT tuzatilgan matnni qaytar, izohsiz."""

_MANBA_QATOR_RE = re.compile(r"^.*Manba\s*:\s*https?://\S+.*$", re.M)
_IMZO_QATOR_RE = re.compile(r"^.*#[\w\u0400-\u04FF]+.*@\w+.*$", re.M)


def _qatorlarni_tikla(asl, yangi):
    """Tahrirchi manba yoki hashtag/kanal imzosini o'chirib yuborsa — qaytaradi.
    Promptga ishonmaymiz: bu qatorlar postning majburiy qismi."""
    for regex in (_MANBA_QATOR_RE, _IMZO_QATOR_RE):
        m = regex.search(asl)
        if m and not regex.search(yangi):
            yangi = yangi.rstrip() + "\n\n" + m.group(0).strip()
            log.warning("Tahrirchi qatorni o'chirgan, tiklandi: %s",
                        m.group(0).strip()[:60])
    return yangi


def ai_polish(conn, post_text, article_text=None):
    """Ikkinchi o'tish — tahrirchi.
    Manba matni berilsa, tahrirchi postni MANBA BILAN SOLISHTIRIB tekshiradi:
    raqam, ism, sana, tushib qolgan kalit so'z. Bu qo'shimcha API chaqiruvi
    emas — bir so'rov ichida ko'proq matn beriladi, kunlik limitga tegmaydi."""
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return post_text
    try:
        api_call_inc(conn)
        if article_text:
            sys_prompt = EDIT_PROMPT_SOURCE
            user = (f"=== MANBA (asl matn) ===\n{article_text[:POLISH_SOURCE_LIMIT]}\n\n"
                    f"=== O'ZBEKCHA POST ===\n{post_text}")
        else:
            sys_prompt = EDIT_PROMPT
            user = post_text
        resp = ai_client().chat.completions.create(
            model=MODEL_SMART, max_completion_tokens=900,
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": user}])
        polished = resp.choices[0].message.content.strip()
        polished = _qatorlarni_tikla(post_text, polished)
        # Himoya: tahrirchi tuzilmani buzsa (juda qisqarib/uzayib ketsa) — aslini qoldir
        if 0.6 < len(polished) / max(len(post_text), 1) < 1.4:
            return polished
    except Exception as e:
        log.warning("Tahrirchi o'tish xatosi: %s", e)
    return post_text


def ai_write_post(conn, url, article_text, rubrika="ai"):
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    prompt = POST_PROMPTS.get(rubrika, POST_PROMPTS["ai"])
    resp = ai_client().chat.completions.create(
        model=MODEL_SMART,
        max_completion_tokens=700,
        messages=[
            {"role": "system", "content": prompt.format(url=url)},
            {"role": "user", "content": article_text[:ARTICLE_CHAR_LIMIT]},
        ],
    )
    draft = resp.choices[0].message.content.strip()
    # ikkinchi o'tish: tahrirchi manba bilan solishtirib tekshiradi
    draft = ai_polish(conn, draft, article_text)
    # Rubrika boshqa kanalga chiqsa — imzo ham o'sha kanalniki
    chan = RUBRIKA_CHANNELS.get(rubrika)
    if chan:
        draft = draft.replace("@safaroov_blog", chan)
    return draft


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
        # audio_path ba'zan to'liq URL, ba'zan nisbiy yo'l bo'lib keladi
        audio_url = path if path.startswith("http") else AISHA_BASE + path
        a = await cli.get(audio_url)
        a.raise_for_status()
        return a.content


def draft_keyboard(post_id):
    """Post-nomzod tugmalari. Aisha kaliti bo'lsa 🎙 ham chiqadi.
    ✍️ Fikr — admin o'z qarashini qo'shadi (eng kuchli ta'sir ko'rsatkichi)."""
    row = [InlineKeyboardButton("✅ Kanalga", callback_data=f"agpub:{post_id}"),
           InlineKeyboardButton("✍️ Fikr", callback_data=f"agfikr:{post_id}")]
    if AISHA_API_KEY:
        row.append(InlineKeyboardButton("🎙 Ovozli", callback_data=f"agpubv:{post_id}"))
    row.append(InlineKeyboardButton("❌", callback_data=f"agskip:{post_id}"))
    return InlineKeyboardMarkup([row])


# Admin fikr yozishini kutish holati: {admin_id: post_id}
_fikr_kutilmoqda = {}


def matnga_fikr_qosh(matn, fikr):
    """Admin fikrini postga qo'shadi — manba qatoridan OLDIN, alohida xatboshi.
    Oxiriga savol qo'yiladi (savol bo'lmasa), chunki savol qatnashuvni oshiradi."""
    fikr = fikr.strip()
    if not fikr:
        return matn
    if not fikr.endswith("?"):
        fikr += "\n\nSiz nima deb o'ylaysiz?"
    qatorlar = matn.rstrip().split("\n")
    # manba yoki imzo qatorini topamiz — fikr o'shalardan oldin turadi
    joy = len(qatorlar)
    for i, q in enumerate(qatorlar):
        if _MANBA_QATOR_RE.match(q) or _IMZO_QATOR_RE.match(q):
            joy = i
            break
    bosh = "\n".join(qatorlar[:joy]).rstrip()
    qoldiq = "\n".join(qatorlar[joy:]).strip()
    natija = f"{bosh}\n\n{fikr}"
    if qoldiq:
        natija += f"\n\n{qoldiq}"
    return natija


# ======================================================================
# RASM-AGENT — post uchun brendli karta (Pillow, bepul, API'siz)
# ======================================================================
CARD_W, CARD_H = 1280, 720
CARD_VARIANTS = 4

# Har rubrika uchun 4 ta dizayn: (yuqori rang, pastki rang, aksent rang)
CARD_PALETTES = {
    "dunyo":       [("#0f2027", "#2c5364", "#4fc3f7"), ("#141e30", "#243b55", "#ffd54f"),
                    ("#232526", "#414345", "#80cbc4"), ("#1a2980", "#26d0ce", "#ffffff")],
    "ai":          [("#41295a", "#2f0743", "#e040fb"), ("#0f0c29", "#302b63", "#7c4dff"),
                    ("#1e3c72", "#2a5298", "#82b1ff"), ("#232526", "#414345", "#b388ff")],
    "rivojlanish": [("#134e5e", "#71b280", "#ccff90"), ("#0f2027", "#2c5364", "#69f0ae"),
                    ("#1d976c", "#093028", "#f4ff81"), ("#232526", "#414345", "#a5d6a7")],
    "mutolaa":     [("#3e2723", "#795548", "#ffcc80"), ("#4e342e", "#212121", "#ffab91"),
                    ("#5d4037", "#8d6e63", "#fff8e1"), ("#263238", "#37474f", "#ffe082")],
    "podcast":     [("#0f2027", "#203a43", "#80deea"), ("#2c003e", "#512b58", "#ea80fc"),
                    ("#000046", "#1cb5e0", "#ffffff"), ("#232526", "#414345", "#84ffff")],
    "uzb":         [("#0f3443", "#34e89e", "#e8f9f1"), ("#1a2980", "#26d0ce", "#aef3e7"),
                    ("#134e5e", "#71b280", "#ffffff"), ("#232526", "#414345", "#69f0ae")],
    "sport":       [("#0f2027", "#2c5364", "#69f0ae"), ("#1d976c", "#093028", "#ccff90"),
                    ("#141e30", "#243b55", "#ffd54f"), ("#232526", "#414345", "#80d8ff")],
    "texno":       [("#000428", "#004e92", "#40c4ff"), ("#0f0c29", "#302b63", "#18ffff"),
                    ("#141e30", "#243b55", "#82b1ff"), ("#232526", "#414345", "#80deea")],
    "islom":       [("#0b3d2e", "#14594a", "#d4af37"), ("#08281f", "#1d6b52", "#f0e6c8"),
                    ("#132f26", "#2a5a48", "#c9a86a"), ("#232526", "#414345", "#a5d6a7")],
}

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

def _card_font(size):
    for p in _FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)   # Pillow >= 10.1
    except TypeError:
        return ImageFont.load_default()

def _hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _card_title(post_text):
    """Postning birinchi qatoridan toza sarlavha oladi (emojisiz)."""
    for ln in post_text.splitlines():
        t = re.sub(r"[^\w\s.,!?:;()'’ʻʼ«»%+\-–—]", "", ln, flags=re.UNICODE).strip()
        if len(t) >= 8:
            return t[:120]
    return "Safarov blog"

def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

def make_card(post_text, rubrika, variant=0):
    """Post uchun 1280x720 brendli karta. PNG baytlari qaytadi."""
    if Image is None:
        return None
    pal = CARD_PALETTES.get(rubrika, CARD_PALETTES["ai"])
    top, bottom, accent = pal[variant % len(pal)]
    top, bottom, accent = _hex_rgb(top), _hex_rgb(bottom), _hex_rgb(accent)

    img = Image.new("RGB", (CARD_W, CARD_H), top)
    d = ImageDraw.Draw(img, "RGBA")
    # Gradient fon
    for y in range(CARD_H):
        k = y / CARD_H
        d.line([(0, y), (CARD_W, y)],
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    # Bezak doiralar (shaffof)
    d.ellipse([CARD_W - 380, -220, CARD_W + 160, 320], fill=accent + (26,))
    d.ellipse([-180, CARD_H - 260, 260, CARD_H + 180], fill=accent + (18,))

    # Rubrika yorlig'i (yuqorida)
    label = RUBRIKA_NOMI.get(rubrika, "YANGILIK").upper()
    f_lbl = _card_font(30)
    lw = d.textlength(label, font=f_lbl)
    d.rounded_rectangle([70, 70, 70 + lw + 48, 128], radius=29, fill=accent + (46,))
    d.rounded_rectangle([70, 70, 70 + lw + 48, 128], radius=29, outline=accent, width=2)
    d.text((94, 84), label, font=f_lbl, fill=accent)

    # Sarlavha (o'rtada, avtomatik o'lcham)
    title = _card_title(post_text)
    for fsize in (76, 64, 54, 46):
        f_t = _card_font(fsize)
        lines = _wrap(d, title, f_t, CARD_W - 190)
        if len(lines) <= 4:
            break
    lh = int(fsize * 1.25)
    y0 = max(200, (CARD_H - lh * len(lines)) // 2 - 30)
    d.rectangle([70, y0 + 8, 82, y0 + lh * len(lines) - 8], fill=accent)  # aksent chiziq
    for i, ln in enumerate(lines):
        d.text((108, y0 + i * lh), ln, font=f_t, fill=(255, 255, 255))

    # Pastki panel: brend + sana
    f_b = _card_font(36)
    f_s = _card_font(26)
    bname, bhandle = _brand_for(rubrika)
    d.text((70, CARD_H - 96), bname, font=f_b, fill=(255, 255, 255))
    sana = datetime.now(TZ).strftime("%d.%m.%Y")
    d.text((70, CARD_H - 50), bhandle, font=f_s, fill=accent)
    sw = d.textlength(sana, font=f_s)
    d.text((CARD_W - 70 - sw, CARD_H - 56), sana, font=f_s, fill=(255, 255, 255, 210))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def preview_keyboard(post_id, variant):
    """Rasm oldindan ko'rish tugmalari."""
    nxt = (variant + 1) % CARD_VARIANTS
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🖼 Shu rasm bilan chiqarish",
                              callback_data=f"agok:{post_id}:{variant}")],
        [InlineKeyboardButton("🔄 Boshqa dizayn", callback_data=f"agrd:{post_id}:{nxt}"),
         InlineKeyboardButton("📝 Rasmsiz", callback_data=f"agtxt:{post_id}")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data=f"agno:{post_id}")],
    ])


# ======================================================================
# FOTO-KARTA — Pexels'dan mos surat topib, blog uslubida bezaydi
# (PEXELS_API_KEY bo'lsa: 1-2-variantlar foto, 3-4 gradient; bo'lmasa hammasi gradient)
# ======================================================================
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
_photo_cache = {}   # post_id -> suratlar URL ro'yxati (restartgacha)

def ai_photo_query(text):
    """Post mazmunidan 2-4 so'zlik inglizcha surat qidiruvini chiqaradi."""
    resp = ai_client().chat.completions.create(
        model=MODEL, max_completion_tokens=20,
        messages=[{"role": "user", "content":
                   "Give 2-4 English keywords for a professional stock photo "
                   "matching this post. Reply with keywords only:\n" + text[:500]}])
    q = re.sub(r"[^\w\s]", "", resp.choices[0].message.content).strip()
    return q[:60] or "modern business"

async def pexels_photos(query, n=4):
    async with httpx.AsyncClient(timeout=20) as cl:
        r = await cl.get("https://api.pexels.com/v1/search",
                         params={"query": query, "per_page": n,
                                 "orientation": "landscape"},
                         headers={"Authorization": PEXELS_KEY})
        r.raise_for_status()
        return [p["src"]["large2x"] for p in r.json().get("photos", [])]

async def _fetch_bytes(url):
    async with httpx.AsyncClient(timeout=25, follow_redirects=True) as cl:
        r = await cl.get(url)
        r.raise_for_status()
        return r.content

_cover_cache = {}   # post_id -> (title, badge)

def ai_cover_title(post_id, post_text, rubrika):
    """Muqova uchun qisqa urg'uli sarlavha: ("MITTI RAZVEDKA", "DRONI")."""
    if post_id in _cover_cache:
        return _cover_cache[post_id]
    title, badge = None, None
    try:
        resp = ai_client().chat.completions.create(
            model=MODEL_FAST, max_completion_tokens=60,
            messages=[{"role": "user", "content":
                "Quyidagi o'zbekcha post uchun Instagram muqova sarlavhasini tuz. "
                "FAQAT JSON qaytar: {\"title\": \"1-3 so'zli urg'uli sarlavha\", "
                "\"badge\": \"1-2 so'zli kategoriya\"}. "
                "Misollar: {\"title\": \"MITTI RAZVEDKA\", \"badge\": \"DRONI\"} yoki "
                "{\"title\": \"TILANCHI\", \"badge\": \"ROBOTLAR\"}. "
                "So'zlar postdagi eng qiziq faktdan olinsin, katta harflarda.\n\n"
                + post_text[:600]}])
        data = json.loads(re.sub(r"```json|```", "", resp.choices[0].message.content).strip())
        title = str(data.get("title", "")).upper().strip()[:28]
        badge = str(data.get("badge", "")).upper().strip()[:18]
    except Exception as e:
        log.warning("Muqova sarlavha xatosi: %s", e)
    if not title:
        words = _card_title(post_text).upper().split()
        title, badge = " ".join(words[:3])[:28], RUBRIKA_NOMI.get(rubrika, "").upper()[:18]
    if not badge:
        badge = RUBRIKA_NOMI.get(rubrika, "YANGILIK").upper()[:18]
    _cover_cache[post_id] = (title, badge)
    return title, badge


def make_photo_card(photo_bytes, post_text, rubrika, cover=None,
                    size=None):
    """Suratni blog uslubiga keltiradi: qoraytirish + muqova sarlavha + brend."""
    if Image is None:
        return None
    W, H = size or (CARD_W, CARD_H)
    pal = CARD_PALETTES.get(rubrika, CARD_PALETTES["ai"])
    accent = _hex_rgb(pal[0][2])

    src = Image.open(BytesIO(photo_bytes)).convert("RGB")
    # Cover-crop: kadr o'lchamiga to'ldirib kesish
    k = max(W / src.width, H / src.height)
    src = src.resize((int(src.width * k) + 1, int(src.height * k) + 1))
    x = (src.width - W) // 2
    y = (src.height - H) // 2
    img = src.crop((x, y, x + W, y + H))

    d = ImageDraw.Draw(img, "RGBA")
    # Pastdan yuqoriga qorong'i gradient (matn o'qilishi uchun)
    for i in range(H):
        alpha = int(200 * max(0, (i - H * 0.35) / (H * 0.65)))
        d.line([(0, i), (W, i)], fill=(10, 12, 16, alpha))
    d.rectangle([0, 0, W, H], fill=(10, 12, 16, 55))  # yengil umumiy dim

    # === MUQOVA USLUBI (techno.kun.uz kabi): markazda katta sarlavha + yorliq ===
    title, badge = cover if cover else (
        _card_title(post_text).upper()[:28],
        RUBRIKA_NOMI.get(rubrika, "YANGILIK").upper())

    # Katta markaziy sarlavha (1-2 qator)
    for fsize in (100, 86, 72, 60):
        f_t = _card_font(fsize)
        lines = _wrap(d, title, f_t, W - 160)
        if len(lines) <= 2:
            break
    lh = int(fsize * 1.12)
    badge_h = 66
    total_h = lh * len(lines) + 22 + badge_h
    y0 = H - 120 - total_h
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f_t)
        x = (W - w) / 2
        # yengil soya — o'qilishi uchun
        d.text((x + 3, y0 + i * lh + 3), ln, font=f_t, fill=(0, 0, 0, 170))
        d.text((x, y0 + i * lh), ln, font=f_t, fill=(255, 255, 255))

    # Kategoriya-yorliq (oq pilyulya, qora matn)
    f_bdg = _card_font(30)
    bw = d.textlength(badge, font=f_bdg)
    bx = (W - bw - 56) / 2
    by = y0 + lh * len(lines) + 22
    d.rounded_rectangle([bx, by, bx + bw + 56, by + badge_h], radius=badge_h // 2,
                        fill=(245, 245, 245, 235))
    d.text((bx + 28, by + 16), badge, font=f_bdg, fill=(20, 22, 26))

    # Brend (yuqori chapda, mayda) va sana (pastda, mayda)
    f_s = _card_font(24)
    bname, bhandle = _brand_for(rubrika)
    d.text((70, 64), bname, font=f_s, fill=(255, 255, 255, 230))
    d.text((70, 98), bhandle, font=_card_font(20), fill=accent)
    sana = datetime.now(TZ).strftime("%d.%m.%Y")
    sw = d.textlength(sana, font=f_s)
    d.text((W - 70 - sw, H - 54), sana, font=f_s,
           fill=(255, 255, 255, 180))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

async def make_card_variant(post_id, text, rubrika, variant):
    """Variant 0: GPT Image (4:5, AI chizadi) · 1-2: Pexels foto · 3: gradient."""
    if variant == 0 and Image is not None:
        card = await make_genai_card(post_id, text, rubrika)
        if card:
            return card
        variant = 1   # AI ishlamasa — foto variantiga tushamiz
    if PEXELS_KEY and variant < 3 and Image is not None:
        try:
            urls = _photo_cache.get(post_id)
            if urls is None:
                urls = await pexels_photos(ai_photo_query(text))
                _photo_cache[post_id] = urls
            if urls:
                photo = await _fetch_bytes(urls[variant % len(urls)])
                card = make_photo_card(photo, text, rubrika,
                                       cover=ai_cover_title(post_id, text, rubrika))
                if card:
                    return card
        except Exception as e:
            log.warning("Foto-karta xatosi (gradientga o'tildi): %s", e)
    return make_card(text, rubrika, variant)


# ======================================================================
# GPT IMAGE — postga mos rasmni AI o'zi chizadi (4:5, muqova uslubida)
# ======================================================================
IMG_MODEL = os.environ.get("AI_MODEL_IMAGE", "gpt-image-2")
IMG_QUALITY = os.environ.get("AI_IMAGE_QUALITY", "medium")   # low/medium/high
IMG_PER_DAY = int(os.environ.get("AI_IMAGE_PER_DAY", "20"))  # xarajat himoyasi
_genimg_cache = {}          # post_id -> tayyor karta baytlari
_genimg_count = {"date": "", "n": 0}

def _img_quota_ok():
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    if _genimg_count["date"] != today:
        _genimg_count.update({"date": today, "n": 0})
    if _genimg_count["n"] >= IMG_PER_DAY:
        return False
    _genimg_count["n"] += 1
    return True

def ai_image_prompt(post_text, rubrika):
    """Post mazmunidan rasm modeli uchun inglizcha tasvir-prompt tuzadi."""
    resp = ai_client().chat.completions.create(
        model=MODEL_FAST, max_completion_tokens=120,
        messages=[{"role": "user", "content":
            "Write a vivid English image-generation prompt (max 60 words) for an "
            "editorial cover illustration matching this news post. Style: cinematic, "
            "dramatic lighting, photorealistic, vertical composition, subject in "
            "upper two-thirds (bottom will hold a title). STRICT: no text, no "
            "words, no letters, no logos, no real people's faces. "
            "Reply with the prompt only:\n" + post_text[:500]}])
    return resp.choices[0].message.content.strip()[:900]

async def make_genai_card(post_id, text, rubrika):
    """GPT Image bilan 4:5 muqova-karta. Keshlanadi — qayta pul ketmaydi."""
    if post_id in _genimg_cache:
        return _genimg_cache[post_id]
    if not _img_quota_ok():
        log.info("Rasm generatsiya kunlik limiti tugadi (%s)", IMG_PER_DAY)
        return None
    try:
        import base64
        prompt = ai_image_prompt(text, rubrika)
        resp = ai_client().images.generate(
            model=IMG_MODEL, prompt=prompt,
            size="1024x1536", quality=IMG_QUALITY, n=1)
        raw = base64.b64decode(resp.data[0].b64_json)
        card = make_photo_card(raw, text, rubrika,
                               cover=ai_cover_title(post_id, text, rubrika),
                               size=(1080, 1350))   # 4:5
        if card:
            _genimg_cache[post_id] = card
        return card
    except Exception as e:
        log.warning("GPT Image xatosi (fotoga o'tildi): %s", e)
        return None

def _post_rubrika(conn, post_id):
    row = conn.execute(
        "SELECT COALESCE(a.rubrika,'ai') FROM agent_posts p "
        "LEFT JOIN agent_articles a ON a.url = p.article_url "
        "WHERE p.id=?", (post_id,)).fetchone()
    return row[0] if row else "ai"

async def rich_photo_url(post_id, text, variant=0):
    """Rich maqola ICHIGA qo'yish uchun ochiq havolali foto (Pexels).
    Rasm bloki faqat http(s) havola bilan ishlaydi, shuning uchun xom foto."""
    if not PEXELS_KEY:
        return None
    try:
        urls = _photo_cache.get(post_id)
        if urls is None:
            urls = await pexels_photos(ai_photo_query(text))
            _photo_cache[post_id] = urls
        if urls:
            return urls[variant % len(urls)]
    except Exception as e:
        log.warning("Rich foto havolasi olinmadi: %s", e)
    return None


async def _send_to_channel(context, text, image_bytes=None, rubrika=None,
                           image_url=None):
    """Kanalga chiqarish. RICH yoqilgan bo'lsa — maqola ko'rinishida:
    sarlavha → rasm → matn → manba. Xato bo'lsa eski usulga tushadi."""
    chan = _channel_for(rubrika)

    # --- 1) RICH (maqola) formati ---
    if RICH_POSTS:
        try:
            md = post_to_rich_markdown(text, image_url=image_url)
            if not image_url and image_bytes:
                # havola yo'q — muqova alohida rasm bo'lib tepada chiqadi
                await context.bot.send_photo(chat_id=chan, photo=image_bytes)
                image_bytes = None       # zaxirada takrorlanmasin
            ok, data = await send_rich_markdown(context, chan, md)
            if ok:
                return
            log.warning("Rich chiqmadi (%s) — eski usulga o'tildi.",
                        data.get("description"))
        except Exception as e:
            log.warning("Rich xatosi (%s) — eski usulga o'tildi.", e)

    # --- 2) ESKI USUL (zaxira, yoki RICH_POSTS=0 bo'lsa) ---
    photo = image_bytes or image_url
    if photo:
        if len(text) <= 1024:
            await context.bot.send_photo(chat_id=chan, photo=photo, caption=text)
        else:  # caption limiti — rasm alohida, matn alohida
            await context.bot.send_photo(chat_id=chan, photo=photo)
            await context.bot.send_message(chat_id=chan, text=text)
    else:
        await context.bot.send_message(chat_id=chan, text=text)


# ======================================================================
# RICH MESSAGE (Bot API 10.1 — "maqola" formati)
# ======================================================================
# PTB hali sendRichMessage'ni o'ramaydi, shuning uchun to'g'ridan-to'g'ri
# httpx bilan chaqiramiz. Muhim: parse_mode BERILMAYDI (rich bilan ishlamaydi).
#   POST .../sendRichMessage
#   {"chat_id": ..., "rich_message": {"markdown": "..."}}

_EMOJI_BOSH = re.compile(
    r"^[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u27BF\u2B00-\u2BFF\uFE0F\u200D]+\s*")
_MANBA_RE = re.compile(r"^\s*\S{0,3}\s*Manba\s*:\s*(https?://\S+)", re.I)
_TAG_RE = re.compile(r"#[\w\u0400-\u04FF]+")
_KANAL_RE = re.compile(r"@\w+")


def _rich_escape(body):
    """Qator boshidagi '#' — Rich Markdown'da sarlavha belgisi.
    Hashtag yo'qolmasligi uchun himoyalanadi."""
    out = []
    for line in body.split("\n"):
        s = line.lstrip()
        if s.startswith("#") and not re.match(r"#{1,6}\s", s):
            line = line.replace("#", "\\#", 1)
        out.append(line)
    return "\n".join(out)


def post_to_rich_markdown(text, image_url=None):
    """Postni maqola ko'rinishiga keltiradi:
        sarlavha → rasm → hashtag → matn → [Manba](havola) · @kanal
    Emoji belgilar (💡 ✨ 📌 🔗) matndan olib tashlanadi."""
    lines = [l.rstrip() for l in text.strip().split("\n")]
    if not lines:
        return ""
    title = lines[0].strip()
    if not title.startswith("#"):
        title = "# " + title

    manba_url, teglar, kanal, gavda = None, [], None, []
    for line in lines[1:]:
        m = _MANBA_RE.match(line)
        if m:                                   # "🔗 Manba: https://..."
            manba_url = m.group(1).rstrip(".,;")
            continue
        if _TAG_RE.search(line) and _KANAL_RE.search(line) and len(line) < 100:
            teglar = _TAG_RE.findall(line)      # "#mutolaa · @safaroov_blog"
            kanal = _KANAL_RE.search(line).group(0)
            continue
        gavda.append(_EMOJI_BOSH.sub("", line))

    qismlar = [title]
    if image_url:
        qismlar.append(f"![]({image_url})")
    if teglar:                                  # hashtag matn boshida
        qismlar.append(" ".join("\\" + t for t in teglar))
    matn = _rich_escape("\n".join(gavda).strip())
    if matn:
        qismlar.append(matn)
    oxiri = []
    if manba_url:
        oxiri.append(f"[Manba]({manba_url})")
    if kanal:
        oxiri.append(kanal)
    if oxiri:
        qismlar.append(" · ".join(oxiri))
    return "\n\n".join(qismlar)


async def tg_image_url(context, image_bytes):
    """Rasm baytlarini Telegramga yuklab, unga HTTPS havola qaytaradi.
    Rich rasm bloki faqat http(s) havola bilan ishlaydi, bayt bilan emas."""
    store = RICH_IMAGE_STORE or ADMIN_ID
    msg = await context.bot.send_photo(chat_id=store, photo=image_bytes,
                                       disable_notification=True)
    f = await context.bot.get_file(msg.photo[-1].file_id)
    return f.file_path        # PTB to'liq HTTPS havola qaytaradi


async def send_rich_markdown(context, chat_id, markdown_text):
    """Bot API 10.1 sendRichMessage — markdown ko'rinishida "maqola" xabari.
    (ok: bool, data: dict) qaytaradi. Xato bo'lsa data['description']da sabab bor."""
    url = f"https://api.telegram.org/bot{context.bot.token}/sendRichMessage"
    payload = {"chat_id": chat_id,
               "rich_message": {"markdown": markdown_text}}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(url, json=payload)
    try:
        data = r.json()
    except Exception:
        return False, {"description": f"HTTP {r.status_code}: {r.text[:200]}"}
    return bool(data.get("ok")), data


# --- SINOV MATNI: barcha asosiy formatlarni tekshiradi ---
RICH_TEST_MD = """# Bu — maqola sarlavhasi

Bu oddiy paragraf. Rich format matnda **qalin**, _kursiv_ va boshqa \
uslublarni tabiiy ko'rsatadi. Agent yozgan yangilik aynan shunday, \
tinch va o'qishli chiqadi.

Ikkinchi paragraf. Maqola formati uzun matnni ham chiroyli joylaydi — \
sarlavha tepada ajralib turadi, matn esa ostida.

> Bu — iqtibos bloki. Sutuur kanalidagi adib so'zlari yoki mashhur \
iqtiboslar aynan shunday ajralib ko'rinadi.

Asosiy fikrlar:
- Birinchi muhim nuqta
- Ikkinchi muhim nuqta
- Uchinchi muhim nuqta

@safaroov_blog"""


# ======================================================================
# OVOZLI YORDAMCHI (Aisha STT + AI javob + Aisha TTS)
# ======================================================================
async def stt_transcribe(audio_bytes, filename="voice.ogg"):
    """Aisha AI orqali ovozni o'zbekcha matnga o'giradi."""
    async with httpx.AsyncClient(timeout=120) as cli:
        r = await cli.post(
            AISHA_BASE + "/api/v1/stt/post/",
            headers={"X-Api-Key": AISHA_API_KEY},
            files={"audio": (filename, audio_bytes, "audio/ogg")},
            data={"has_diarization": "false", "language": "uz"})
        if r.status_code == 402:
            raise RuntimeError("Aisha balansi tugagan (402)")
        if r.status_code not in (200, 201):
            raise RuntimeError(f"Aisha STT xatosi {r.status_code}: {r.text[:150]}")
        data = r.json()
        # Turli versiyalarda kalit nomi farq qilishi mumkin — himoyali o'qiymiz
        text = (data.get("transcript") or data.get("text")
                or data.get("result") or "")
        if isinstance(text, dict):
            text = text.get("text", "")
        return str(text).strip()


ROUTER_PROMPT = """Sen @safaroov_blog kanalining ovozli yordamchisisan. Admin senga \
ovozli buyruq berdi (matnga o'girilgan). Ikki xil niyat bo'lishi mumkin:

1) "savol" — yangiliklar haqida so'rayapti ("marketingda nima yangiliklar", \
"rivojlanish bo'yicha nima bor"). Bunda:
   - Quyidagi materiallar ro'yxatidan FAQAT savolga mos keladiganlarini tanla.
   - Javobni raqamlangan ro'yxat qilib yoz (1. 2. 3. ...), har biriga 1 gap. \
Havolalarni javob matniga QO'SHMA — ular alohida ko'rsatiladi.
   - "urls" massivida tanlagan materiallaring havolalarini AYNAN javobdagi raqamlar \
tartibida ber.
   - Mos material bo'lmasa: javob "Bu mavzuda hozircha yangilik yo'q", urls bo'sh.
   - Javob 700 belgidan oshmasin. Hech narsa to'qima.

2) "chiqarish" — oldingi ro'yxatdagi yangilikni kanalga chiqarishni buyuryapti \
("birinchi yangilikni kanalga chiqar", "2-chisini ovozli qilib chiqaraylik", \
"shu maqolani ham matnli ham ovozli chiqar"). Bunda:
   - "raqam": nechanchi yangilik (aytilmasa 1).
   - "ovozli": "ovozli", "audio", "ovoz bilan", "ham ovozli ham matnli" desa true, \
aks holda false.

FAQAT JSON qaytar:
{"intent":"savol","javob":"...","urls":["...","..."]}
yoki
{"intent":"chiqarish","raqam":1,"ovozli":true}"""


def _recent_articles_digest(conn, limit=40):
    rows = conn.execute(
        "SELECT title, COALESCE(rubrika,'ai'), url, COALESCE(score,0) "
        "FROM agent_articles WHERE score IS NOT NULL "
        "ORDER BY seen_at DESC LIMIT ?", (limit,)).fetchall()
    return "\n".join(
        f"- [{RUBRIKA_NOMI.get(r,'?')}] {t} (baho {s}) — {u}"
        for t, r, u, s in rows)


def ai_voice_router(conn, question, digest):
    """Ovozli buyruqning niyatini aniqlaydi va kerak bo'lsa javob tayyorlaydi."""
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return {"intent": "savol",
                "javob": "Bugungi AI limiti tugadi — ertaga qayta so'rang.", "urls": []}
    api_call_inc(conn)
    resp = ai_client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        max_completion_tokens=700,
        messages=[
            {"role": "system", "content": ROUTER_PROMPT},
            {"role": "user",
             "content": f"Buyruq: {question}\n\nMateriallar:\n{digest}"},
        ],
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        return {"intent": "savol", "javob": "Tushunmadim, qayta so'rang.", "urls": []}


async def publish_article(context, conn, url, ovozli):
    """Bazadagi maqoladan post yasab, darhol kanalga chiqaradi.
    (post_text, audio_note) qaytaradi — audio xatosi jarayonni yiqitmaydi."""
    row = conn.execute(
        "SELECT title, COALESCE(summary,''), COALESCE(rubrika,'ai') "
        "FROM agent_articles WHERE url=?", (url,)).fetchone()
    if not row:
        raise RuntimeError("Bu maqola bazada topilmadi")
    title, summary, rubrika = row
    try:
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded) if downloaded else None
    except Exception:
        text = None
    if not text:
        text = title + "\n\n" + summary
    post_text = ai_write_post(conn, url, text, rubrika)
    if not post_text:
        raise RuntimeError("Kunlik AI limiti tugadi")

    # 1) Matn kanalga + darhol bazaga yoziladi
    await context.bot.send_message(chat_id=CHANNEL_ID, text=post_text)
    conn.execute(
        "INSERT INTO agent_posts(article_url,text,status,created_at) "
        "VALUES(?,?,'published',?)", (url, post_text, datetime.now(TZ).isoformat()))
    conn.execute("UPDATE agent_articles SET status='posted' WHERE url=?", (url,))
    conn.commit()

    # 2) Audio alohida — xatosi postga ta'sir qilmaydi
    audio_note = ""
    if ovozli:
        try:
            audio = await tts_generate(post_text)
            if audio:
                audio_title = post_text.splitlines()[0].strip()[:60] or "Safarov blog"
                await context.bot.send_audio(
                    chat_id=_channel_for(rubrika), audio=audio, filename="post.wav",
                    title=audio_title, performer="Safarov blog")
                audio_note = " + 🎙 OVOZ"
        except Exception as e:
            log.exception("Kanal audio xatosi: %s", e)
            audio_note = f"\n⚠️ Matn chiqdi, lekin ovoz chiqmadi: {e}"
    return post_text, audio_note


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin ovozli xabar tashlasa: STT → niyat → javob YOKI kanalga chiqarish."""
    if not update.effective_user or update.effective_user.id != ADMIN_ID:
        return
    if not AISHA_API_KEY:
        await update.message.reply_text(
            "🎙 Ovozli so'rovlar uchun Railway'da AISHA_API_KEY berilishi kerak.")
        return
    try:
        await update.message.reply_text("🎧 Eshityapman...")
        tg_file = await update.message.voice.get_file()
        audio_bytes = bytes(await tg_file.download_as_bytearray())
        question = await stt_transcribe(audio_bytes)
        if not question:
            await update.message.reply_text(
                "Ovozdan matn chiqmadi — yaqinroqdan, ravshanroq gapirib ko'ring.")
            return
        await update.message.reply_text(f"🗣 Sizni eshitdim: «{question}»")

        conn = db()
        digest = _recent_articles_digest(conn)
        if not digest:
            await update.message.reply_text(
                "Bazada hali materiallar yo'q — avval /agent_run bosing.")
            conn.close()
            return

        data = ai_voice_router(conn, question, digest)

        # --- Buyruq: N-yangilikni kanalga chiqarish ---
        if data.get("intent") == "chiqarish":
            urls = json.loads(meta_get(conn, "last_urls", "[]"))
            n = int(data.get("raqam") or 1)
            ovozli = bool(data.get("ovozli"))
            if not urls:
                await update.message.reply_text(
                    "Qaysi yangilik ekanini bilmayapman — avval savol bering "
                    "(masalan: «marketingda nima yangiliklar?»), keyin raqamini ayting.")
            elif n < 1 or n > len(urls):
                await update.message.reply_text(
                    f"Ro'yxatda {len(urls)} ta yangilik bor edi, "
                    f"{n}-raqamlisi yo'q. Qayta ayting.")
            else:
                await update.message.reply_text(
                    f"⏳ {n}-yangilikdan post tayyorlab kanalga chiqaryapman"
                    f"{' (ovoz bilan 🎙)' if ovozli else ''}...")
                post_text, audio_note = await publish_article(
                    context, conn, urls[n-1], ovozli)
                await update.message.reply_text(
                    f"✅ KANALGA CHIQDI{audio_note}\n\n{post_text}")
            conn.close()
            return

        # --- Savol: javob + ro'yxatni eslab qolish ---
        answer = data.get("javob", "Tushunmadim, qayta so'rang.")
        urls = data.get("urls") or []
        meta_set(conn, "last_urls", json.dumps(urls))
        if urls:
            answer += "\n\n" + "\n".join(
                f"{i+1}) {u}" for i, u in enumerate(urls))
            answer += ("\n\n🎙 Chiqarish uchun ayting: "
                       "«N-yangilikni kanalga chiqar» (+ «ovozli» desangiz audio bilan)")
        conn.close()
        await update.message.reply_text(answer, disable_web_page_preview=True)

        # Javobni ovozda ham qaytaramiz (ro'yxat va havolalarsiz, faqat asosiy matn)
        try:
            audio = await tts_generate(data.get("javob", ""))
            if audio:
                await update.message.reply_voice(voice=audio)
        except Exception as e:
            log.warning("Javob ovozi chiqmadi: %s", e)
    except Exception as e:
        log.exception("Ovozli so'rov xatosi: %s", e)
        await update.message.reply_text(f"⚠️ Xato: {e}")


# ======================================================================
# AGENT — ASOSIY OQIM
# ======================================================================
_ANTH_LINK_RE = re.compile(
    r'<a[^>]+href="(/news/[^"#?]{3,})"[^>]*>(.*?)</a>', re.I | re.S)
_TEG_RE = re.compile(r"<[^>]+>")
_SANA_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s*\d{4}\b")
_KATEG_RE = re.compile(
    r"\b(Announcements?|Product|Policy|Research|Economic Research|Societal Impacts)\b")


def scrape_anthropic(limit=10):
    """Anthropic RSS chiqarmaydi — news sahifasidan maqolalarni o'qiymiz.
    RSS yozuviga o'xshash lug'atlar ro'yxatini qaytaradi."""
    natija, korilgan = [], set()
    try:
        r = httpx.get("https://www.anthropic.com/news", timeout=30,
                      follow_redirects=True, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        for yol, ichi in _ANTH_LINK_RE.findall(r.text):
            if yol in korilgan:
                continue
            korilgan.add(yol)
            matn = html.unescape(_TEG_RE.sub(" ", ichi))
            matn = _SANA_RE.sub(" ", matn)          # "Jul 9, 2026" olib tashlanadi
            matn = _KATEG_RE.sub(" ", matn)         # rubrika yorlig'i olib tashlanadi
            matn = re.sub(r"\s+", " ", matn).strip()
            slug = yol.rsplit("/", 1)[-1].replace("-", " ").capitalize()
            sarlavha = matn[:180] if len(matn) >= 15 else slug
            natija.append({"link": "https://www.anthropic.com" + yol,
                           "title": sarlavha, "summary": ""})
            if len(natija) >= limit:
                break
    except Exception as e:
        log.warning("Anthropic sahifasi o'qilmadi: %s", e)
    return natija


SCRAPERS = {"anthropic": scrape_anthropic}


def fetch_new_articles(conn):
    """RSS manbalardan bazada yo'q maqolalarni 'new' holatida saqlaydi.
    'scrape:NOM' ko'rinishidagi manba RSS emas — SCRAPERS dagi funksiya o'qiydi."""
    added = 0
    for source_name, feed_url, rubrika in SOURCES:
        if rubrika in RUBRIKA_OFF:      # vaqtincha o'chirilgan — o'qilmaydi ham
            continue
        if feed_url.startswith("scrape:"):
            entries = SCRAPERS.get(feed_url[7:], lambda: [])()
        else:
            try:
                feed = feedparser.parse(feed_url, agent=USER_AGENT)
            except Exception as e:
                log.warning("RSS xato (%s): %s", source_name, e)
                continue
            entries = feed.entries
        for entry in entries[:10]:
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
    # 3 kundan eski ko'rilmagan postlar avtomatik o'tkaziladi (uyum yig'ilmasin)
    conn.execute("UPDATE agent_posts SET status='skipped' "
                 "WHERE status='draft' AND created_at < ?",
                 ((datetime.now(TZ) - timedelta(days=3)).isoformat(),))
    conn.commit()
    if meta_get(conn, "paused") == "1":
        conn.close()
        return

    added = fetch_new_articles(conn)
    log.info("Agent: yangi maqolalar %d", added)

    # --- Bosqich A: saralash ('new' navbatidan; post yozish uchun zaxira qoladi) ---
    # To'plamli baholash: 10 tadan bitta so'rovda — API chaqiruvini ~10 barobar tejaydi.
    queue = [r for r in conn.execute(
        "SELECT url, title, COALESCE(summary,''), COALESCE(rubrika,'ai') "
        "FROM agent_articles "
        "WHERE status='new' ORDER BY seen_at DESC LIMIT 60").fetchall()
        if r[3] not in RUBRIKA_OFF][:30]
    for i in range(0, len(queue), SCORE_BATCH):
        if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY - SCORING_RESERVE:
            log.info("Saralash to'xtadi — zaxira limitiga yetildi, qolgani ertaga.")
            break
        bolak = queue[i:i + SCORE_BATCH]
        ballar = ai_score_batch(conn, bolak)
        if ballar is None:          # kunlik limit tugadi
            break
        for url, title, summary, rubrika in bolak:
            score = ballar.get(url)
            if score is None:       # to'plamda tushib qolgan bo'lsa — bittalab
                if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY - SCORING_RESERVE:
                    break
                score = ai_score(conn, title, summary, rubrika)
                if score is None:
                    break
            conn.execute(
                "UPDATE agent_articles SET score=?, status='scored' WHERE url=?",
                (score, url))
    conn.commit()

    # --- Bosqich B: nomzodlar (har rubrikadan ko'pi bilan MAX_PER_RUBRIKA ta) ---
    rows = conn.execute(
        "SELECT url, title, source, score, COALESCE(summary,''), "
        "COALESCE(rubrika,'ai') FROM agent_articles "
        "WHERE status='scored' AND score>=? "
        "ORDER BY score DESC, seen_at DESC LIMIT 60",
        (MIN_SCORE,)).fetchall()
    sent_count = 0
    # Kunlik chegara: MAX_POSTS_PER_DAY endi HAQIQATAN kunlik (run bo'yicha emas)
    qoldiq = MAX_POSTS_PER_DAY - posts_today(conn)
    if qoldiq <= 0:
        log.info("Kunlik post chegarasi to'ldi (%d) — qolgani ertaga.",
                 MAX_POSTS_PER_DAY)
        conn.close()
        return 0
    candidates, taken = [], {}
    for row in rows:
        rub = row[5]
        if rub in RUBRIKA_OFF:          # vaqtincha o'chirilgan rubrika
            continue
        if taken.get(rub, 0) >= MAX_PER_RUBRIKA:
            continue
        taken[rub] = taken.get(rub, 0) + 1
        candidates.append(row)
        if len(candidates) >= qoldiq:
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
            post_inc(conn)
            emoji = RUBRIKA_EMOJI.get(rubrika, "📬")
            nomi = RUBRIKA_NOMI.get(rubrika, rubrika)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{emoji} {nomi} · {source} · baho {score}/10:"
                     f"\n\n{post_text}",
                reply_markup=draft_keyboard(post_id),
            )
            sent_count += 1
        except Exception as e:
            log.exception("Agent xatosi: %s", e)
            try:
                await context.bot.send_message(
                    ADMIN_ID, f"⚠️ Agent xatosi ({url}): {e}")
            except Exception:
                pass
    conn.close()
    return sent_count


async def evening_reminder(context: ContextTypes.DEFAULT_TYPE):
    await _send_digest(context)


async def _send_digest(context):
    """Kutayotgan postlarni bitta ixcham ro'yxat qilib yuboradi."""
    conn = db()
    rows = conn.execute(
        "SELECT p.id, p.text, COALESCE(a.rubrika,'ai') FROM agent_posts p "
        "LEFT JOIN agent_articles a ON a.url = p.article_url "
        "WHERE p.status='draft' ORDER BY p.id DESC LIMIT 8").fetchall()
    total = conn.execute(
        "SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
    conn.close()
    if not rows:
        await context.bot.send_message(
            ADMIN_ID, "📭 Kutayotgan post yo'q — hammasi ko'rilgan! ✅")
        return
    lines, btns = [], []
    for i, (pid, text, rub) in enumerate(rows, 1):
        title = text.splitlines()[0].strip()[:55]
        lines.append(f"{i}. {RUBRIKA_EMOJI.get(rub, '📰')} {title}")
        btns.append(InlineKeyboardButton(str(i), callback_data=f"agopen:{pid}"))
    kb = [btns[j:j + 4] for j in range(0, len(btns), 4)]
    kb.append([InlineKeyboardButton("🧹 2 kundan eskilarini tozalash",
                                    callback_data="agclean:0")])
    await context.bot.send_message(
        ADMIN_ID,
        f"📥 Kutayotgan postlar: {total} ta (eng yangi {len(rows)} tasi)\n\n"
        + "\n".join(lines)
        + "\n\n👇 Raqamni bosing — post tugmalari bilan ochiladi.",
        reply_markup=InlineKeyboardMarkup(kb))


async def cmd_postlar(update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    await _send_digest(context)


# ======================================================================
# TUGMALAR (tasdiqlash)
# ======================================================================
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("Bu tugma faqat admin uchun.", show_alert=True)
        return
    parts = query.data.split(":")
    action, post_id = parts[0], parts[1]
    variant = int(parts[2]) if len(parts) > 2 else 0
    conn = db()

    # --- 🧹 Eski postlarni tozalash (2 kundan oshganlar) ---
    if action == "agclean":
        limit = (datetime.now(TZ) - timedelta(days=2)).isoformat()
        cur = conn.execute(
            "UPDATE agent_posts SET status='skipped' "
            "WHERE status='draft' AND created_at < ?", (limit,))
        conn.commit()
        conn.close()
        await query.answer(f"{cur.rowcount} ta eski post tozalandi 🧹")
        await _send_digest(context)
        return

    # --- 📬 Ro'yxatdan postni ochish ---
    if action == "agopen":
        row = conn.execute(
            "SELECT text,status FROM agent_posts WHERE id=?", (post_id,)).fetchone()
        conn.close()
        if not row or row[1] != "draft":
            await query.answer("Bu post allaqachon ko'rilgan.", show_alert=True)
            return
        await query.answer()
        await context.bot.send_message(
            chat_id=ADMIN_ID, text=row[0], reply_markup=draft_keyboard(post_id))
        return

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

    # --- ✅ Kanalga: avval rasm taklif qilinadi ---
    if action == "agpub":
        rubrika = _post_rubrika(conn, post_id)
        await query.answer("Rasm tayyorlanmoqda... 🎨")
        # RICH rejim: maqola ichiga ochiq havolali foto ketadi —
        # shuning uchun ko'rsatiladigan rasm ham aynan o'sha bo'ladi.
        if RICH_POSTS:
            url = await rich_photo_url(post_id, text, 0)
            if url:
                try:
                    await context.bot.send_photo(
                        chat_id=ADMIN_ID, photo=url,
                        caption=f"🖼 Rasm 1/{CARD_VARIANTS} — maqola ichiga shu ketadi",
                        reply_markup=preview_keyboard(post_id, 0))
                    await query.edit_message_text(f"🎨 RASM TANLANMOQDA (pastda)\n\n{text}")
                except Exception as e:
                    await query.answer(f"Rasm xatosi: {e}", show_alert=True)
                conn.close()
                return
        img = await make_card_variant(post_id, text, rubrika, 0)
        if not img:  # Pillow yo'q — eski usul: to'g'ridan-to'g'ri matn
            try:
                await _send_to_channel(context, text, rubrika=rubrika)
                conn.execute("UPDATE agent_posts SET status='published' WHERE id=?", (post_id,))
                conn.commit()
                await query.answer("Kanalga jo'natildi! ✅")
                await query.edit_message_text(f"✅ KANALGA CHIQDI\n\n{text}")
            except Exception as e:
                await query.answer(f"Xato: {e}", show_alert=True)
            conn.close()
            return
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_ID, photo=img,
                caption=f"🎨 Dizayn 1/{CARD_VARIANTS} — postga mos keladimi?",
                reply_markup=preview_keyboard(post_id, 0))
            await query.edit_message_text(f"🎨 RASM TANLANMOQDA (pastda)\n\n{text}")
        except Exception as e:
            await query.answer(f"Rasm xatosi: {e}", show_alert=True)
        conn.close()
        return

    # --- 🔄 Boshqa dizayn ---
    if action == "agrd":
        rubrika = _post_rubrika(conn, post_id)
        await query.answer("Tayyorlanmoqda... 🎨")
        if RICH_POSTS:
            url = await rich_photo_url(post_id, text, variant)
            if url:
                try:
                    await query.edit_message_media(
                        InputMediaPhoto(url,
                                        caption=f"🖼 Rasm {variant + 1}/{CARD_VARIANTS} — "
                                                f"maqola ichiga shu ketadi"),
                        reply_markup=preview_keyboard(post_id, variant))
                except Exception as e:
                    await query.answer(f"Xato: {e}", show_alert=True)
                conn.close()
                return
        img = await make_card_variant(post_id, text, rubrika, variant)
        try:
            await query.edit_message_media(
                InputMediaPhoto(img,
                                caption=f"🎨 Dizayn {variant + 1}/{CARD_VARIANTS} — "
                                        f"postga mos keladimi?"),
                reply_markup=preview_keyboard(post_id, variant))
        except Exception as e:
            await query.answer(f"Xato: {e}", show_alert=True)
        conn.close()
        return

    # --- 🖼 Rasm bilan chiqarish ---
    if action == "agok":
        rubrika = _post_rubrika(conn, post_id)
        try:
            if RICH_POSTS:
                url = await rich_photo_url(post_id, text, variant)
                await _send_to_channel(context, text, None, rubrika, image_url=url)
            else:
                img = await make_card_variant(post_id, text, rubrika, variant)
                await _send_to_channel(context, text, img, rubrika)
            conn.execute("UPDATE agent_posts SET status='published' WHERE id=?", (post_id,))
            conn.commit()
            await query.answer("Rasm bilan kanalga chiqdi! ✅")
            await query.edit_message_caption(caption="✅ KANALGA CHIQDI (🖼 rasm bilan)")
        except Exception as e:
            await query.answer(f"Xato: {e}", show_alert=True)
        conn.close()
        return

    # --- 📝 Rasmsiz chiqarish ---
    if action == "agtxt":
        rubrika = _post_rubrika(conn, post_id)
        try:
            await _send_to_channel(context, text, rubrika=rubrika)
            conn.execute("UPDATE agent_posts SET status='published' WHERE id=?", (post_id,))
            conn.commit()
            await query.answer("Kanalga jo'natildi! ✅")
            await query.edit_message_caption(caption="✅ KANALGA CHIQDI (📝 rasmsiz)")
        except Exception as e:
            await query.answer(f"Xato: {e}", show_alert=True)
        conn.close()
        return

    # --- ❌ Bekor (rasm bosqichidan orqaga) ---
    if action == "agno":
        try:
            await query.edit_message_caption(caption="❌ Bekor qilindi.")
            await context.bot.send_message(
                chat_id=ADMIN_ID, text=text, reply_markup=draft_keyboard(post_id))
        except Exception:
            pass
        await query.answer("Post nomzodlar qatoriga qaytdi.")
        conn.close()
        return

    # --- 🎙 Ovozli: matn + audio (eski oqim, rasm bosqichisiz) ---
    if action == "agpubv":
        rubrika = _post_rubrika(conn, post_id)
        try:
            await _send_to_channel(context, text, rubrika=rubrika)
            conn.execute("UPDATE agent_posts SET status='published' WHERE id=?", (post_id,))
            conn.commit()
        except Exception as e:
            await query.answer(f"Xato: {e}", show_alert=True)
            conn.close()
            return
        audio_note = ""
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
        await query.edit_message_text(f"✅ KANALGA CHIQDI{audio_note}\n\n{text}")
        conn.close()
        return

    # --- ❌ O'tkazib yuborish ---
    if action == "agfikr":
        _fikr_kutilmoqda[query.from_user.id] = post_id
        await query.answer()
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=("✍️ Shu postga o'z fikringizni yozing (2-3 jumla).\n\n"
                  "Nima diqqatingizni tortdi, nega muhim deb bilasiz — "
                  "o'z so'zingiz bilan.\n\n"
                  "Bekor qilish uchun: /bekor"))
        conn.close()
        return

    if action == "agskip":
        conn.execute("UPDATE agent_posts SET status='skipped' WHERE id=?", (post_id,))
        conn.commit()
        await query.answer("O'tkazib yuborildi.")
        await query.edit_message_text(f"❌ O'TKAZILDI\n\n{text}")
    conn.close()


async def cmd_bekor(update, context):
    """/bekor — fikr yozishni bekor qiladi."""
    if update.effective_user is None or update.effective_user.id != ADMIN_ID:
        return
    if _fikr_kutilmoqda.pop(update.effective_user.id, None):
        await update.message.reply_text("Bekor qilindi.")
    else:
        await update.message.reply_text("Kutilayotgan ish yo'q.")


async def on_fikr_text(update, context):
    """Admin ✍️ Fikr bosgandan keyin yozgan matnni postga qo'shadi.
    Kutilmayotgan bo'lsa — hech narsa qilmaydi, xabar boshqa modullarga o'tadi."""
    uid = update.effective_user.id if update.effective_user else None
    post_id = _fikr_kutilmoqda.get(uid)
    if post_id is None:
        return                      # bu bizga tegishli emas
    fikr = (update.message.text or "").strip()
    if not fikr:
        return
    _fikr_kutilmoqda.pop(uid, None)

    conn = db()
    row = conn.execute("SELECT text FROM agent_posts WHERE id=?", (post_id,)).fetchone()
    if not row:
        conn.close()
        await update.message.reply_text("Post topilmadi (o'chirilgan bo'lishi mumkin).")
        raise ApplicationHandlerStop
    yangi = matnga_fikr_qosh(row[0], fikr)
    conn.execute("UPDATE agent_posts SET text=? WHERE id=?", (yangi, post_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✍️ Fikringiz qo'shildi:\n\n{yangi}",
        reply_markup=draft_keyboard(post_id))
    raise ApplicationHandlerStop


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
    bugun_post = posts_today(conn)
    paused = meta_get(conn, "paused") == "1"
    conn.close()
    ochiq = [r for r in RUBRIKA_NOMI if r not in RUBRIKA_OFF]
    ochirilgan = ", ".join(sorted(RUBRIKA_OFF)) if RUBRIKA_OFF else "yo'q"
    await update.message.reply_text(
        f"📊 Agent holati\n"
        f"Holat: {'⏸ pauzada' if paused else '▶️ ishlamoqda'}\n"
        f"Bugun ko'rilgan maqolalar: {seen}\n"
        f"Kutayotgan postlar: {drafts}\n"
        f"Jami chiqarilgan: {pub}\n"
        f"Bugungi API chaqiruvlar: {calls}/{MAX_API_CALLS_PER_DAY}\n"
        f"Bugungi postlar: {bugun_post}/{MAX_POSTS_PER_DAY}\n"
        f"Taxminiy bugungi xarajat: ~${calls * 0.008:.3f}\n\n"
        f"Faol rubrikalar: {len(ochiq)} ta\n"
        f"⏹ O'chirilgan: {ochirilgan}\n"
        f"Har rubrikadan kuniga: {MAX_PER_RUBRIKA} ta")


@admin_only
async def cmd_run(update, context):
    await update.message.reply_text("🔍 Manbalarni tekshiryapman, biroz kuting...")
    n = await run_agent(context)
    conn = db()
    calls = api_calls_today(conn)
    drafts = conn.execute(
        "SELECT COUNT(*) FROM agent_posts WHERE status='draft'").fetchone()[0]
    conn.close()
    if n:
        await update.message.reply_text(
            f"✅ {n} ta yangi post-nomzod yuborildi. Hammasi: /postlar")
    elif calls >= MAX_API_CALLS_PER_DAY:
        await update.message.reply_text(
            f"⛔ Bugungi API limiti tugadi ({calls}/{MAX_API_CALLS_PER_DAY}) — "
            f"yangi postlar ertaga. Kutayotganlar: {drafts} ta → /postlar")
    else:
        await update.message.reply_text(
            f"📭 Yangi material topilmadi — manbalardagi maqolalar allaqachon "
            f"ko'rib chiqilgan (odatda bir necha soatda yangilanadi).\n"
            f"Kutayotgan postlar: {drafts} ta → /postlar")


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
async def cmd_rich_test(update, context):
    """/rich_test — rich (maqola) formatini ADMINGA yuborib sinaydi.
    Kanalga tegmaydi; faqat ko'rinishni tekshirish uchun."""
    await update.message.reply_text("🧪 Rich xabar yuborilmoqda...")
    try:
        ok, data = await send_rich_markdown(context, ADMIN_ID, RICH_TEST_MD)
    except Exception as e:
        await update.message.reply_text(f"❌ So'rov xatosi: {e}")
        return
    if ok:
        await update.message.reply_text(
            "✅ Rich xabar chiqdi — yuqoridagi ko'rinishni tekshiring.\n"
            "Sarlavha, paragraf, iqtibos, ro'yxat to'g'ri ko'rinsa — "
            "asosiy oqimga ulaymiz.")
    else:
        desc = data.get("description", "noma'lum")
        await update.message.reply_text(
            f"❌ Rich xabar chiqmadi.\nSabab: {desc}\n\n"
            f"To'liq javob (debug):\n{str(data)[:500]}")


@admin_only
async def cmd_rich_oxirgi(update, context):
    """/rich_oxirgi — bazadagi eng oxirgi postni RICH formatda ADMINGA ko'rsatadi.
    Kanalga CHIQMAYDI — haqiqiy post qanday ko'rinishini xavfsiz tekshirish uchun."""
    conn = db()
    row = conn.execute(
        "SELECT id, text FROM agent_posts ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        await update.message.reply_text(
            "Bazada post yo'q. Avval /agent_run bosing.")
        return
    post_id, text = row
    await update.message.reply_text(
        f"🧪 #{post_id} post rich (maqola) formatda ko'rsatilmoqda...")
    try:
        ok, data = await send_rich_markdown(
            context, ADMIN_ID, post_to_rich_markdown(text))
    except Exception as e:
        await update.message.reply_text(f"❌ So'rov xatosi: {e}")
        return
    if ok:
        await update.message.reply_text(
            "☝️ Kanalga aynan shunday chiqadi.\n"
            "Sarlavha, havola, hashtag va emoji joyida bo'lsa — tayyor.\n"
            "Biror joyi buzilsa — menga ayting, shablonni to'g'rilaymiz.")
    else:
        await update.message.reply_text(
            f"❌ Chiqmadi.\nSabab: {data.get('description', 'nomaʼlum')}\n\n"
            f"Debug:\n{str(data)[:400]}")


@admin_only
async def cmd_rich_rasm(update, context):
    """/rich_rasm — rasm maqola ICHIDA chiqishini sinaydi (ADMINGA, kanalga emas).
    Ochiq HTTPS havola (Pexels) ishlatiladi — Telegram o'z fayl havolasini
    qabul qilmagani aniqlandi (RICH_MESSAGE_PHOTO_NO_MEDIA_FOUND)."""
    conn = db()
    row = conn.execute(
        "SELECT id, text FROM agent_posts ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        await update.message.reply_text("Bazada post yo'q. Avval /agent_run bosing.")
        return
    post_id, text = row

    if not PEXELS_KEY:
        await update.message.reply_text("PEXELS_API_KEY yo'q — sinov o'tkazib bo'lmaydi.")
        return
    await update.message.reply_text(f"🧪 #{post_id} — ochiq havolali rasm izlanmoqda...")
    try:
        urls = await pexels_photos(ai_photo_query(text))
        if not urls:
            await update.message.reply_text("❌ Pexels rasm topmadi.")
            return
        url = urls[0]
    except Exception as e:
        await update.message.reply_text(f"❌ Pexels xatosi: {e}")
        return

    try:
        ok, data = await send_rich_markdown(
            context, ADMIN_ID, post_to_rich_markdown(text, image_url=url))
    except Exception as e:
        await update.message.reply_text(f"❌ So'rov xatosi: {e}")
        return
    if ok:
        await update.message.reply_text(
            "✅ Rasm maqola ichida chiqdi.\n\n"
            "Demak mexanizm ishlaydi, faqat rasm ochiq havolada turishi shart.\n"
            "Bu — Pexels fotosi (muqova yozuvisiz). Muqovali variantni ham "
            "ichkariga qo'yish uchun rasmni ochiq joyda saqlash kerak — "
            "buni keyingi qadamda hal qilamiz.")
    else:
        await update.message.reply_text(
            f"❌ Chiqmadi.\nSabab: {data.get('description', 'nomaʼlum')}\n\n"
            f"Debug:\n{str(data)[:400]}")


async def _rich_media_try(context, chat_id, markdown_text, image_bytes, media_obj):
    """sendRichMessage'ni multipart bilan chaqiradi (rasm bayt sifatida ketadi).
    Qaytaradi: (ok, javob) — xato matni tashxis uchun kerak."""
    url = f"https://api.telegram.org/bot{context.bot.token}/sendRichMessage"
    body = {"markdown": markdown_text, "media": [media_obj]}
    data = {"chat_id": str(chat_id), "rich_message": json.dumps(body)}
    files = {"muqova": ("muqova.png", image_bytes, "image/png")}
    async with httpx.AsyncClient(timeout=60) as cli:
        r = await cli.post(url, data=data, files=files)
    try:
        return r.json()
    except Exception:
        return {"ok": False, "description": f"HTTP {r.status_code}: {r.text[:150]}"}


# Xatodan aniqlandi: InputRichMessageMedia da "id" maydoni majburiy.
# Endi media obyekti va markdown murojaati birga sinaladi (matritsa).
# Aniqlandi: {"id": ..., "media": {"type":"photo","media":"attach://muqova"}}
# shakli TO'G'RI o'qiladi. Qolgani — markdown ichida unga murojaat shakli.
# Har element: (nom, id qiymati, markdown havolasi)
_RICH_MEDIA_CASES = [
    ("c1 id=attach",      "attach://muqova",              "attach://muqova"),
    ("c2 id=soxta url",   "https://safarov.uz/muqova.png","https://safarov.uz/muqova.png"),
    ("c3 tg://media",     "muqova",                       "tg://media?id=muqova"),
    ("c4 media://",       "muqova",                       "media://muqova"),
    ("c5 tg-id://",       "muqova",                       "tg-id://muqova"),
    ("c6 id=#muqova",     "muqova",                       "#muqova"),
]


@admin_only
async def cmd_rich_media(update, context):
    """/rich_media — brendli muqovani maqola ICHIGA havolasiz joylashni sinaydi.
    Bir necha yozilish variantini ketma-ket urinib, natijasini aytadi."""
    conn = db()
    row = conn.execute(
        "SELECT id, text FROM agent_posts ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        conn.close()
        await update.message.reply_text("Bazada post yo'q. Avval /agent_run bosing.")
        return
    post_id, text = row
    rubrika = _post_rubrika(conn, post_id)
    conn.close()

    await update.message.reply_text(f"🧪 #{post_id} — muqova tayyorlanmoqda...")
    try:
        img = await make_card_variant(post_id, text, rubrika, 0)
        if not img:
            await update.message.reply_text("❌ Muqova chiqmadi (Pillow yoki kunlik limit).")
            return
    except Exception as e:
        await update.message.reply_text(f"❌ Muqova xatosi: {e}")
        return

    hisobot = []
    for nom, id_qiymat, ref in _RICH_MEDIA_CASES:
        shape = {"id": id_qiymat,
                 "media": {"type": "photo", "media": "attach://muqova"}}
        md = post_to_rich_markdown(text, image_url=ref)
        try:
            res = await _rich_media_try(context, ADMIN_ID, md, img, shape)
        except Exception as e:
            hisobot.append(f"{nom} — so'rov xatosi: {e}")
            continue
        if res.get("ok"):
            await update.message.reply_text(
                f"✅ ISHLADI: {nom}\n(id={id_qiymat} · havola={ref})\n\n"
                "☝️ Brendli muqova maqola ichida chiqdi. "
                "Shu variantni kanal oqimiga ulaymiz.")
            return
        hisobot.append(f"{nom} — {res.get('description', '?')}")

    matn = "Hech biri ishlamadi:\n\n" + "\n".join(hisobot)
    await update.message.reply_text(matn[:3900] +
                                    "\n\nShu xatolarni menga tashlang.")


@admin_only
async def cmd_sources(update, context):
    parts = []
    for rub in ("ai", "rivojlanish", "podcast", "dunyo", "mutolaa", "uzb", "sport", "texno", "islom"):
        names = ", ".join(n for n, _, r in SOURCES if r == rub)
        parts.append(f"{RUBRIKA_EMOJI[rub]} {RUBRIKA_NOMI[rub]}: {names}")
    await update.message.reply_text("📡 Manbalar:\n" + "\n".join(parts))


# ======================================================================
# BUYRUQLAR MENYUSI (Telegram'da avtomatik ko'rinadi)
# ======================================================================
PUBLIC_COMMANDS = [
    BotCommand("zikr",    "📿 Zikr eslatmasini yoqish"),
    BotCommand("zikr_off","🔕 Zikr eslatmasini to'xtatish"),
    BotCommand("start",   "🏠 Bosh menyu"),
    BotCommand("konkurs", "🏆 Konkurs haqida"),
    BotCommand("raqam",   "🔢 Konkursdagi raqamim"),
    BotCommand("sinov",   "🧩 Bilim testi"),
    BotCommand("shaxs",   "🧠 Shaxsiyat testi"),
    BotCommand("kanallar","📣 Kanallarimiz"),
]
ADMIN_COMMANDS = [
    BotCommand("zikr",          "📿 Zikr eslatmasini yoqish"),
    BotCommand("zikr_off",      "🔕 Zikr eslatmasini to'xtatish"),
    BotCommand("panel",         "🏛 BOSHQARUV PANELI — hammasi shu yerda"),
    BotCommand("postlar",       "📥 Kutayotgan postlar ro'yxati"),
    BotCommand("agent_run",     "🔍 Agentni hozir ishga tushirish"),
    BotCommand("farosat",       "🧠 Farosatdan: 5 ta kuzatuv"),
    BotCommand("sutuur",        "📖 Sutuur: satr / adabiyot"),
    BotCommand("stats",         "📈 Bot statistikasi"),
    BotCommand("kurs_stats",    "🎓 Kurs sotuvlari"),
    BotCommand("tekshir",       "🔎 Bloklaganlarni aniqlash"),
    BotCommand("xabar",         "📢 Hammaga xabar yuborish"),
    BotCommand("agent_status",  "📊 Agent holati"),
    BotCommand("rich_test",     "🧪 Rich (maqola) format sinovi"),
    BotCommand("rich_oxirgi",   "🧪 Oxirgi postni rich formatda ko'rish"),
    BotCommand("rich_rasm",     "🧪 Rasm maqola ichida sinovi"),
    BotCommand("rich_media",    "🧪 Muqova maqola ichida (havolasiz)"),
    BotCommand("agent_sources", "📡 Agent manbalari"),
    BotCommand("agent_requeue", "♻️ Maqolalarni navbatga qaytarish"),
    BotCommand("agent_pause",   "⏸ Agentni to'xtatish"),
    BotCommand("agent_resume",  "▶️ Agentni davom ettirish"),
    BotCommand("elon2",  "📚 Konkurs e'lonini joylash"),
    BotCommand("golib2", "🎉 Konkurs g'olibini tanlash"),
    BotCommand("reset2", "🧹 Konkursni tozalash"),
] + PUBLIC_COMMANDS


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
    app.add_handler(CommandHandler("postlar", cmd_postlar))
    app.add_handler(CommandHandler("agent_pause", cmd_pause))
    app.add_handler(CommandHandler("agent_resume", cmd_resume))
    app.add_handler(CommandHandler("agent_requeue", cmd_requeue))
    app.add_handler(CommandHandler("agent_sources", cmd_sources))
    app.add_handler(CommandHandler("rich_test", cmd_rich_test))
    app.add_handler(CommandHandler("rich_oxirgi", cmd_rich_oxirgi))
    app.add_handler(CommandHandler("rich_rasm", cmd_rich_rasm))
    app.add_handler(CommandHandler("rich_media", cmd_rich_media))
    app.add_handler(CommandHandler("bekor", cmd_bekor))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(agpub|agpubv|agskip|agok|agrd|agtxt|agno|agopen|agclean|agfikr):\d+"))
    # Fikr matni: group=-1 — ustoz.py dagi matn ishlovchisidan OLDIN ishlaydi.
    # Kutilmayotgan paytda hech narsa qilmaydi, xabar odatdagidek o'tib ketadi.
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        on_fikr_text), group=-1)
    app.add_handler(MessageHandler(
        filters.VOICE & filters.User(user_id=ADMIN_ID), on_voice))

    if app.job_queue is None:
        log.error("JobQueue yo'q! requirements.txt da "
                  "python-telegram-bot[job-queue] bo'lishi kerak.")
    else:
        # Ish vaqtlari Railway Variables'dan boshqariladi:
        #   AGENT_TIMES    = "07:00" yoki "07:00,13:00,19:00" (Toshkent vaqti)
        #   REMINDER_TIME  = "20:00" — kechki eslatma (bo'sh qoldirilsa 20:00)
        times_raw = os.environ.get("AGENT_TIMES", "07:00")
        agent_times = []
        for t in times_raw.split(","):
            t = t.strip()
            try:
                h, m = map(int, t.split(":"))
                agent_times.append((h, m))
            except Exception:
                log.warning("AGENT_TIMES noto'g'ri qiymat o'tkazildi: %r", t)
        if not agent_times:
            agent_times = [(7, 0)]
        for i, (h, m) in enumerate(agent_times):
            app.job_queue.run_daily(run_agent, time=dtime(h, m, tzinfo=TZ),
                                    name=f"agent_run_{i}")
        try:
            rh, rm = map(int, os.environ.get("REMINDER_TIME", "20:00").split(":"))
        except Exception:
            rh, rm = 20, 0
        app.job_queue.run_daily(evening_reminder, time=dtime(rh, rm, tzinfo=TZ),
                                name="agent_evening")
        app.job_queue.run_once(_setup_commands, when=3, name="setup_commands")
        log.info("Agent jadvali: %s (Toshkent), eslatma: %02d:%02d",
                 ", ".join(f"{h:02d}:{m:02d}" for h, m in agent_times), rh, rm)

    log.info("AI agent ulandi: 07:00 avtomatik, /agent_run — qo'lda. Aisha TTS: %s",
             "yoqilgan 🎙" if AISHA_API_KEY else "o'chiq (AISHA_API_KEY berilmagan)")
