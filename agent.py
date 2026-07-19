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
MAX_POSTS_PER_DAY = 12         # kunlik post-nomzodlar (5 rubrika uchun)
MAX_PER_RUBRIKA = 2            # bitta yo'nalish kunni bosib ketmasligi uchun
MAX_API_CALLS_PER_DAY = 150    # 15 manba uchun; baribir kuniga ~$0.03 atrofida
SCORING_RESERVE = MAX_POSTS_PER_DAY  # post yozish uchun doim zaxira chaqiruv qoladi
ARTICLE_CHAR_LIMIT = 8000
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) AppleWebKit/537.36"

# Rubrikalar: ai · rivojlanish · podcast · dunyo (jahon yangiliklari) · mutolaa (kitob)
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
    # --- 📚 Kitob va mutolaa ---
    ("Literary Hub",  "https://lithub.com/feed/",                                      "mutolaa"),
    ("Austin Kleon",  "https://austinkleon.com/feed/",                                 "mutolaa"),
    ("Ryan Holiday",  "https://ryanholiday.net/feed/",                                 "mutolaa"),
]

RUBRIKA_EMOJI = {"ai": "🗞", "rivojlanish": "🌱", "podcast": "🎧",
                 "dunyo": "🌍", "mutolaa": "📚", "uzb": "🇺🇿", "sport": "⚽", "texno": "📱"}
RUBRIKA_NOMI = {"ai": "AI va marketing", "rivojlanish": "Shaxsiy rivojlanish",
                "podcast": "Podcast va video", "dunyo": "Dunyo yangiliklari",
                "mutolaa": "Kitob va mutolaa",
                "uzb": "O'zbekiston", "sport": "Sport", "texno": "Texno olami"}

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
SCORE_PROMPT = """Sen @safaroov_blog Telegram kanalining kuratorisan. Kanal yo'nalishlari: \
(1) AI va marketing, (2) shaxsiy rivojlanish, (3) muhim jahon yangiliklari, \
(4) kitob va mutolaa, (5) podcast, (6) O'zbekiston yangiliklari, (7) sport \
(ayniqsa futbol va O'zbekistonga aloqador voqealar), (8) texno olami — \
gadjetlar, yangi qurilmalar, harbiy texnologiyalar. Auditoriya: O'zbekistondagi marketologlar, kichik \
biznes egalari, o'z ustida ishlaydigan yoshlar. Auditoriyaning asosiy qismi musulmonlar — \
material hurmatli va ishonchli bo'lishi shart.

Quyidagi material sarlavhasi va annotatsiyasiga qarab baho ber.
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
4. Kompaniya, mahsulot, model va odam nomlari asl holicha qoladi.
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

O'Z-O'ZINI TEKSHIRISH (majburiy yakuniy qadam): postni yozib bo'lgach, har \
jumlani ovoz chiqarib o'qiyotgandek tekshir: (1) o'zbek suhbatida shunday \
deyiladimi? (2) bitta jumlada ikki "uchun"/"tomonidan"/"ushbu" yo'qmi? \
(3) jumla 20 so'zdan oshmadimi? Muammoli jumlani QAYTA yoz, keyin yakuniy \
matnni qaytar.
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
}


def ai_score(conn, title, summary):
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return None
    api_call_inc(conn)
    resp = ai_client().chat.completions.create(
        model=MODEL,
        response_format={"type": "json_object"},
        max_completion_tokens=100,
        messages=[
            {"role": "system", "content": SCORE_PROMPT},
            {"role": "user", "content": f"Sarlavha: {title}\nAnnotatsiya: {summary[:1000]}"},
        ],
    )
    try:
        return int(json.loads(resp.choices[0].message.content).get("score", 0))
    except (json.JSONDecodeError, ValueError, TypeError):
        return 0


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

TEGMA: emoji, tuzilma (qatorlar tartibi), havolalar, hashtag, manba nomi, \
raqamlar, atoqli otlar (kompaniya/odam/tashabbus nomlari asl holicha).
FAQAT tuzatilgan matnni qaytar, izohsiz."""

def ai_polish(conn, post_text):
    """Ikkinchi o'tish: tayyor postni faqat til jihatidan tozalaydi."""
    if api_calls_today(conn) >= MAX_API_CALLS_PER_DAY:
        return post_text
    try:
        api_call_inc(conn)
        resp = ai_client().chat.completions.create(
            model=MODEL_SMART, max_completion_tokens=700,
            messages=[{"role": "system", "content": EDIT_PROMPT},
                      {"role": "user", "content": post_text}])
        polished = resp.choices[0].message.content.strip()
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
    return ai_polish(conn, draft)   # ikkinchi o'tish: til tahriri


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
    """Post-nomzod tugmalari. Aisha kaliti bo'lsa 🎙 ham chiqadi."""
    row = [InlineKeyboardButton("✅ Kanalga", callback_data=f"agpub:{post_id}")]
    if AISHA_API_KEY:
        row.append(InlineKeyboardButton("🎙 Ovozli", callback_data=f"agpubv:{post_id}"))
    row.append(InlineKeyboardButton("❌", callback_data=f"agskip:{post_id}"))
    return InlineKeyboardMarkup([row])


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
    d.text((70, CARD_H - 96), "SAFAROV BLOG", font=f_b, fill=(255, 255, 255))
    sana = datetime.now(TZ).strftime("%d.%m.%Y")
    handle = "t.me/safaroov_blog"
    d.text((70, CARD_H - 50), handle, font=f_s, fill=accent)
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


def make_photo_card(photo_bytes, post_text, rubrika, cover=None):
    """Pexels suratini blog uslubiga keltiradi: qoraytirish + sarlavha + brend."""
    if Image is None:
        return None
    pal = CARD_PALETTES.get(rubrika, CARD_PALETTES["ai"])
    accent = _hex_rgb(pal[0][2])

    src = Image.open(BytesIO(photo_bytes)).convert("RGB")
    # Cover-crop: 1280x720 ga to'ldirib kesish
    k = max(CARD_W / src.width, CARD_H / src.height)
    src = src.resize((int(src.width * k) + 1, int(src.height * k) + 1))
    x = (src.width - CARD_W) // 2
    y = (src.height - CARD_H) // 2
    img = src.crop((x, y, x + CARD_W, y + CARD_H))

    d = ImageDraw.Draw(img, "RGBA")
    # Pastdan yuqoriga qorong'i gradient (matn o'qilishi uchun)
    for i in range(CARD_H):
        alpha = int(200 * max(0, (i - CARD_H * 0.35) / (CARD_H * 0.65)))
        d.line([(0, i), (CARD_W, i)], fill=(10, 12, 16, alpha))
    d.rectangle([0, 0, CARD_W, CARD_H], fill=(10, 12, 16, 55))  # yengil umumiy dim

    # === MUQOVA USLUBI (techno.kun.uz kabi): markazda katta sarlavha + yorliq ===
    title, badge = cover if cover else (
        _card_title(post_text).upper()[:28],
        RUBRIKA_NOMI.get(rubrika, "YANGILIK").upper())

    # Katta markaziy sarlavha (1-2 qator)
    for fsize in (100, 86, 72, 60):
        f_t = _card_font(fsize)
        lines = _wrap(d, title, f_t, CARD_W - 160)
        if len(lines) <= 2:
            break
    lh = int(fsize * 1.12)
    badge_h = 66
    total_h = lh * len(lines) + 22 + badge_h
    y0 = CARD_H - 120 - total_h
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=f_t)
        x = (CARD_W - w) / 2
        # yengil soya — o'qilishi uchun
        d.text((x + 3, y0 + i * lh + 3), ln, font=f_t, fill=(0, 0, 0, 170))
        d.text((x, y0 + i * lh), ln, font=f_t, fill=(255, 255, 255))

    # Kategoriya-yorliq (oq pilyulya, qora matn)
    f_bdg = _card_font(30)
    bw = d.textlength(badge, font=f_bdg)
    bx = (CARD_W - bw - 56) / 2
    by = y0 + lh * len(lines) + 22
    d.rounded_rectangle([bx, by, bx + bw + 56, by + badge_h], radius=badge_h // 2,
                        fill=(245, 245, 245, 235))
    d.text((bx + 28, by + 16), badge, font=f_bdg, fill=(20, 22, 26))

    # Brend (yuqori chapda, mayda) va sana (pastda, mayda)
    f_s = _card_font(24)
    d.text((70, 64), "SAFAROV BLOG", font=f_s, fill=(255, 255, 255, 230))
    d.text((70, 98), "t.me/safaroov_blog", font=_card_font(20), fill=accent)
    sana = datetime.now(TZ).strftime("%d.%m.%Y")
    sw = d.textlength(sana, font=f_s)
    d.text((CARD_W - 70 - sw, CARD_H - 54), sana, font=f_s,
           fill=(255, 255, 255, 180))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

async def make_card_variant(post_id, text, rubrika, variant):
    """Variant 0-1: Pexels foto-karta (kalit bo'lsa), 2-3: gradient karta."""
    if PEXELS_KEY and variant < 2 and Image is not None:
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

def _post_rubrika(conn, post_id):
    row = conn.execute(
        "SELECT COALESCE(a.rubrika,'ai') FROM agent_posts p "
        "LEFT JOIN agent_articles a ON a.url = p.article_url "
        "WHERE p.id=?", (post_id,)).fetchone()
    return row[0] if row else "ai"

async def _send_to_channel(context, text, image_bytes=None):
    """Kanalga chiqarish: rasm bo'lsa rasm+matn, bo'lmasa faqat matn."""
    if image_bytes:
        if len(text) <= 1024:
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=image_bytes,
                                         caption=text)
        else:  # caption limiti — rasm alohida, matn alohida
            await context.bot.send_photo(chat_id=CHANNEL_ID, photo=image_bytes)
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text)
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=text)


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
                    chat_id=CHANNEL_ID, audio=audio, filename="post.wav",
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
    sent_count = 0
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
        img = await make_card_variant(post_id, text, rubrika, 0)
        if not img:  # Pillow yo'q — eski usul: to'g'ridan-to'g'ri matn
            try:
                await _send_to_channel(context, text)
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
        img = await make_card_variant(post_id, text, rubrika, variant)
        try:
            await _send_to_channel(context, text, img)
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
        try:
            await _send_to_channel(context, text)
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
        try:
            await _send_to_channel(context, text)
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
    if action == "agskip":
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
async def cmd_sources(update, context):
    parts = []
    for rub in ("ai", "rivojlanish", "podcast", "dunyo", "mutolaa", "uzb", "sport", "texno"):
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
    app.add_handler(CommandHandler("postlar", cmd_postlar))
    app.add_handler(CommandHandler("agent_pause", cmd_pause))
    app.add_handler(CommandHandler("agent_resume", cmd_resume))
    app.add_handler(CommandHandler("agent_requeue", cmd_requeue))
    app.add_handler(CommandHandler("agent_sources", cmd_sources))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(agpub|agpubv|agskip|agok|agrd|agtxt|agno|agopen|agclean):\d+"))
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
