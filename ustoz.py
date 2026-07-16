# -*- coding: utf-8 -*-
"""
ustoz.py — AI Ustoz moduli (@safarovblog_bot marketing kursi uchun).

Nima qiladi:
  * /topshiriq — o'quvchi haftalik topshiriqni yuboradi, AI (gpt-4o-mini)
    dars mazmuni asosida batafsil fikr bildiradi. Admin nusxa oladi.
  * /savol — kurs bo'yicha savolga AI ustoz javob beradi.
  * Kurs a'zosi shunchaki uzun matn yuborsa ham bot o'zi so'raydi:
    "Bu topshiriqmi yoki savol?" — darslardagi "botga yuboring" ko'rsatmasi
    endi jonli ishlaydi.
  * Kunlik limitlar: 5 ta tekshiruv, 10 ta savol (har foydalanuvchiga).

Talab: OPENAI_API_KEY (agent bilan bir xil kalit).
bot.py ga ulash:  import ustoz  →  ustoz.register(app)
"""

import json
import logging
import os
import re
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ContextTypes, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters)

import kurs
from kurs_content import WEEKS

log = logging.getLogger("ustoz")

DATA_DIR = os.environ.get("DATA_DIR", "/data")
USTOZ_FILE = os.path.join(DATA_DIR, "ustoz.json")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
MODEL = "gpt-4o-mini"
DAILY_TASKS = 5      # kuniga nechta topshiriq tekshiriladi
DAILY_QUESTIONS = 10  # kuniga nechta savolga javob

_ai = None
def ai_client():
    global _ai
    if _ai is None:
        from openai import OpenAI
        _ai = OpenAI()
    return _ai


# ---------------- Limitlar hisobi ----------------
def _load():
    try:
        with open(USTOZ_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(USTOZ_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

def _quota(uid, kind):
    """True = ruxsat bor (va hisobga yoziladi), False = limit tugagan."""
    d = _load()
    today = time.strftime("%Y-%m-%d")
    u = d.setdefault(str(uid), {})
    if u.get("date") != today:
        u.update({"date": today, "tasks": 0, "qs": 0})
    limit = DAILY_TASKS if kind == "tasks" else DAILY_QUESTIONS
    if u.get(kind, 0) >= limit and uid != ADMIN_ID:
        return False
    u[kind] = u.get(kind, 0) + 1
    _save(d)
    return True


# ---------------- Kurs kontenti yordamchilari ----------------
def _strip_html(s):
    return re.sub(r"<[^>]+>", "", s)

def _week_context(n):
    """AI uchun hafta darslari matni (HTML'siz, qisqartirilgan)."""
    w = WEEKS.get(n)
    if not w or not w["lessons"]:
        return ""
    parts = [f"{n}-HAFTA: {w['title']}"]
    for l in w["lessons"]:
        parts.append(_strip_html(l["text"])[:2500])
    return "\n\n".join(parts)[:8000]

def _course_outline():
    return "\n".join(f"{n}-hafta: {WEEKS[n]['title']}" for n in sorted(WEEKS))

def _current_week(uid):
    """O'quvchining joriy haftasi: darsi tugatilgan eng oxirgi hafta."""
    d = kurs._load()
    u = d["users"].get(str(uid), {})
    done = set(u.get("done", []))
    cur = 1
    for n in sorted(WEEKS):
        if any(l["id"] in done for l in WEEKS[n]["lessons"]):
            cur = n
    return cur

def _is_paid(uid):
    d = kurs._load()
    u = kurs._user(d, uid)
    return u.get("paid", False)


# ---------------- AI chaqiruvlari ----------------
TASK_PROMPT = """Sen "Marketing kursi: noldan amaliyotgacha" kursining tajribali, \
samimiy ustozisan. O'quvchi {week}-hafta topshirig'ini yubordi. Quyida shu \
haftaning dars materiallari va o'quvchi javobi berilgan.

Vazifang — do'stona, rag'batlantiruvchi, lekin halol fikr bildirish. Javob \
tuzilishi (aynan shu tartibda, sarlavhalarsiz, tabiiy matn qilib):
1. Qisqa samimiy kirish (1 gap).
2. 💪 Kuchli tomonlar: 2-3 ta aniq jihat (nima yaxshi chiqqan va nega).
3. 🔧 Yaxshilash uchun: 2-3 ta aniq taklif — umumiy gap emas, o'quvchining \
o'z matnidan misol olib, qanday qilishni ko'rsat.
4. Baho: X/10 va bitta gap xulosa.
5. Ruhlantiruvchi yakun (1 gap).

Qoidalar: faqat o'zbek tilida, sodda va iliq tilda, 250 so'zdan oshma. \
Dars materiallariga tayangan holda baho ber. O'quvchini hech qachon kamsitma — \
zaif ishda ham avval urinishni qadrlab, keyin yo'l ko'rsat.

=== DARS MATERIALLARI ===
{context}

=== O'QUVCHI JAVOBI ===
{answer}"""

QA_PROMPT = """Sen "Marketing kursi: noldan amaliyotgacha" kursining tajribali, \
samimiy ustozisan. Kurs dasturi:
{outline}

O'quvchi hozir {week}-haftada. Uning savoliga o'zbek tilida, sodda va aniq \
javob ber (150 so'zgacha). Iloji bo'lsa kursning qaysi haftasida bu mavzu \
chuqur o'tilishini eslat. Marketing va biznesga aloqasi yo'q savol bo'lsa, \
muloyimlik bilan kurs mavzulariga qaytar. Aniq bilmagan narsangni to'qima.

Savol: {question}"""

def ai_check_task(week, answer):
    resp = ai_client().chat.completions.create(
        model=MODEL, max_tokens=700, temperature=0.7,
        messages=[{"role": "user", "content": TASK_PROMPT.format(
            week=week, context=_week_context(week), answer=answer[:4000])}])
    return resp.choices[0].message.content.strip()

def ai_answer_question(uid, question):
    resp = ai_client().chat.completions.create(
        model=MODEL, max_tokens=500, temperature=0.7,
        messages=[{"role": "user", "content": QA_PROMPT.format(
            outline=_course_outline(), week=_current_week(uid),
            question=question[:1500])}])
    return resp.choices[0].message.content.strip()


# ---------------- Klaviaturalar ----------------
def _weeks_kb():
    btns = [InlineKeyboardButton(str(n), callback_data=f"ust_w:{n}")
            for n in sorted(WEEKS) if WEEKS[n]["lessons"]]
    rows = [btns[i:i + 5] for i in range(0, len(btns), 5)]
    return InlineKeyboardMarkup(rows)


# ---------------- Buyruqlar ----------------
async def cmd_ustoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _is_paid(uid):
        await update.message.reply_text(
            "🎓 AI Ustoz — kurs a'zolari uchun shaxsiy murabbiy: "
            "topshiriqlaringizni tekshiradi va savollaringizga javob beradi.\n\n"
            "Kursga qo'shilish: /kurs")
        return
    await update.message.reply_text(
        "🎓 <b>AI Ustoz xizmatida!</b>\n\n"
        "📝 /topshiriq — haftalik topshiriqni tekshirtirish\n"
        "❓ /savol — kurs bo'yicha savol berish\n\n"
        "Yoki shunchaki topshiriq matningizni yozib yuboring — o'zim "
        "tushunib olaman. 😊", parse_mode="HTML")

async def cmd_topshiriq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _is_paid(uid):
        await update.message.reply_text("Bu bo'lim kurs a'zolari uchun: /kurs")
        return
    cur = _current_week(uid)
    context.user_data["ustoz"] = {"mode": "task_pick"}
    await update.message.reply_text(
        f"📝 Qaysi hafta topshirig'ini tekshiraman? "
        f"(Siz hozir {cur}-haftadasiz)", reply_markup=_weeks_kb())

async def cmd_savol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not _is_paid(uid):
        await update.message.reply_text("Bu bo'lim kurs a'zolari uchun: /kurs")
        return
    context.user_data["ustoz"] = {"mode": "question"}
    await update.message.reply_text(
        "❓ Savolingizni yozing — ustoz sifatida javob beraman.")


# ---------------- Tugmalar ----------------
async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data

    if data.startswith("ust_w:"):
        week = int(data.split(":")[1])
        st = context.user_data.get("ustoz") or {}
        pending = st.get("pending")
        context.user_data["ustoz"] = {"mode": "task", "week": week}
        await q.answer()
        if pending:  # matn allaqachon yuborilgan edi — darhol tekshiramiz
            await q.edit_message_text(f"📝 {week}-hafta topshirig'i qabul qilindi.")
            await _process_task(update.effective_user, pending, week, context)
            context.user_data.pop("ustoz", None)
        else:
            await q.edit_message_text(
                f"📝 {week}-hafta tanlandi. Endi topshiriq javobingizni "
                f"bitta xabar qilib yuboring.")
        return

    if data == "ust_q":
        st = context.user_data.get("ustoz") or {}
        pending = st.get("pending")
        await q.answer()
        if pending:
            await q.edit_message_text("❓ Savol qabul qilindi.")
            await _process_question(update.effective_user, pending, context)
        context.user_data.pop("ustoz", None)
        return

    if data == "ust_no":
        context.user_data.pop("ustoz", None)
        await q.answer()
        await q.edit_message_text("👌 Tushundim, e'tiborsiz qoldirdim.")
        return


# ---------------- Matn qabul qilish ----------------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = (update.message.text or "").strip()
    st = context.user_data.get("ustoz") or {}
    mode = st.get("mode")

    if mode == "task" and st.get("week"):
        context.user_data.pop("ustoz", None)
        await _process_task(update.effective_user, text, st["week"], context)
        return

    if mode == "question":
        context.user_data.pop("ustoz", None)
        await _process_question(update.effective_user, text, context)
        return

    if mode == "task_pick":
        # Hafta tanlanmasdan matn keldi — matnni saqlab, hafta so'raymiz
        context.user_data["ustoz"] = {"mode": "task_pick", "pending": text}
        await update.message.reply_text(
            "Avval haftani tanlang 👇", reply_markup=_weeks_kb())
        return

    # Rejimsiz kelgan uzun matn — kurs a'zosidan bo'lsa, o'zimiz so'raymiz
    if len(text) > 120 and _is_paid(uid):
        context.user_data["ustoz"] = {"mode": "ask", "pending": text}
        cur = _current_week(uid)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📝 Ha, {cur}-hafta topshirig'i",
                                  callback_data=f"ust_w:{cur}")],
            [InlineKeyboardButton("📅 Boshqa hafta topshirig'i",
                                  callback_data="ust_pick"),
             InlineKeyboardButton("❓ Bu savol", callback_data="ust_q")],
            [InlineKeyboardButton("❌ Hech qaysi", callback_data="ust_no")],
        ])
        await update.message.reply_text(
            "Matningizni oldim! Bu nima edi? 😊", reply_markup=kb)


async def on_pick_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    st = context.user_data.get("ustoz") or {}
    context.user_data["ustoz"] = {"mode": "task_pick",
                                  "pending": st.get("pending")}
    await q.answer()
    await q.edit_message_text("📅 Haftani tanlang:", reply_markup=_weeks_kb())


# ---------------- Asosiy ishlov ----------------
async def _process_task(user, text, week, context):
    if len(text) < 40:
        await context.bot.send_message(
            user.id, "Topshiriq juda qisqa ekan 😊 Batafsilroq yozib, "
                     "qayta yuboring — shunda foydali fikr bera olaman.")
        return
    if not _quota(user.id, "tasks"):
        await context.bot.send_message(
            user.id, f"Bugungi tekshiruv limiti tugadi ({DAILY_TASKS} ta). "
                     f"Ertaga davom etamiz! 😊")
        return
    await context.bot.send_message(user.id, "🎓 Ustoz o'qiyapti... (10-20 soniya)")
    try:
        feedback = ai_check_task(week, text)
    except Exception as e:
        log.exception("Ustoz xatosi: %s", e)
        await context.bot.send_message(
            user.id, "Texnik xatolik bo'ldi, birozdan keyin qayta urinib ko'ring.")
        return
    # Bajarilganini kursda belgilash
    d = kurs._load()
    u = kurs._user(d, user.id)
    u.setdefault("tasks", {})[str(week)] = True
    kurs._save(d)
    await context.bot.send_message(
        user.id, f"🎓 <b>Ustoz fikri ({week}-hafta topshirig'i):</b>\n\n{feedback}",
        parse_mode="HTML")
    # Admin nusxasi
    if ADMIN_ID and user.id != ADMIN_ID:
        try:
            uname = f"@{user.username}" if user.username else ""
            await context.bot.send_message(
                ADMIN_ID,
                f"📝 Yangi topshiriq — {user.full_name} {uname} "
                f"({week}-hafta):\n\n{text[:800]}\n\n"
                f"— — —\n🤖 AI bahosi:\n{feedback[:800]}")
        except Exception:
            pass


async def _process_question(user, text, context):
    if not _quota(user.id, "qs"):
        await context.bot.send_message(
            user.id, f"Bugungi savollar limiti tugadi ({DAILY_QUESTIONS} ta). "
                     f"Ertaga bemalol davom etamiz! 😊")
        return
    await context.bot.send_message(user.id, "🎓 O'ylayapman...")
    try:
        answer = ai_answer_question(user.id, text)
    except Exception as e:
        log.exception("Savol xatosi: %s", e)
        await context.bot.send_message(
            user.id, "Texnik xatolik bo'ldi, birozdan keyin qayta urinib ko'ring.")
        return
    await context.bot.send_message(
        user.id, f"🎓 <b>Ustoz javobi:</b>\n\n{answer}", parse_mode="HTML")


# ---------------- Ro'yxatga olish ----------------
def register(app):
    if not os.environ.get("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY yo'q — AI Ustoz o'chirilgan.")
        return
    app.add_handler(CommandHandler("ustoz", cmd_ustoz))
    app.add_handler(CommandHandler("topshiriq", cmd_topshiriq))
    app.add_handler(CommandHandler("savol", cmd_savol))
    app.add_handler(CallbackQueryHandler(on_pick_other, pattern=r"^ust_pick$"))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^ust_"))
    # group=1: bot.py'dagi boshqa handlerlar bilan to'qnashmaslik uchun
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text),
                    group=1)
    log.info("AI Ustoz moduli ulandi.")
