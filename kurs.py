# -*- coding: utf-8 -*-
"""
kurs.py — Marketing kursi moduli (@safarovblog_bot uchun).

Imkoniyatlar:
  • /kurs — kurs sahifasi; 1.1-dars bepul, to'liq kurs 100 ⭐ (Telegram Stars)
  • To'lov: send_invoice(currency="XTR") — bank/karta kerak emas
  • Darslar ketma-ket ochiladi, jarayon foizi ko'rinadi
  • Har hafta oxirida test, kurs oxirida shaxsiy sertifikat (Pillow)
  • Admin: /kurs_stats — sotuvlar hisobi

bot.py ga ulash:  import kurs  →  kurs.register(app)
"""

import json
import logging
import os
import time
from io import BytesIO

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      LabeledPrice)
from telegram.ext import (ContextTypes, CommandHandler, CallbackQueryHandler,
                          PreCheckoutQueryHandler, MessageHandler, filters)

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None

from kurs_content import COURSE_TITLE, COURSE_INTRO, WEEKS

log = logging.getLogger("kurs")

DATA_DIR = os.environ.get("DATA_DIR", "/data")
KURS_FILE = os.path.join(DATA_DIR, "kurs.json")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
PRICE_STARS = 100
PAYLOAD = "marketing_kurs_100"


# ---------------- Ma'lumotlar ----------------
def _load():
    try:
        with open(KURS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}

def _save(d):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KURS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False)

def _user(d, uid):
    return d["users"].setdefault(str(uid), {"paid": False, "done": [], "scores": {}})

def _weeks_with_content():
    return [n for n in sorted(WEEKS) if WEEKS[n]["lessons"]]

def _total_lessons():
    return sum(len(WEEKS[n]["lessons"]) for n in WEEKS)

def _progress(u):
    total = _total_lessons()
    return round(len(u["done"]) / total * 100) if total else 0


# ---------------- Klaviaturalar ----------------
def kb_home(paid):
    rows = [[InlineKeyboardButton("🔓 1-darsni bepul o'qish", callback_data="krs_l:1:0")]]
    if paid:
        rows = [[InlineKeyboardButton("📚 Darslarga o'tish", callback_data="krs_menu")]]
    else:
        rows.append([InlineKeyboardButton(f"⭐ Kursni olish — {PRICE_STARS} Stars",
                                          callback_data="krs_buy")])
    return InlineKeyboardMarkup(rows)

def kb_weeks(u):
    rows = []
    for n in sorted(WEEKS):
        w = WEEKS[n]
        if w["lessons"]:
            done = sum(1 for l in w["lessons"] if l["id"] in u["done"])
            mark = "✅" if done == len(w["lessons"]) else f"{done}/{len(w['lessons'])}"
            rows.append([InlineKeyboardButton(
                f"{n}-hafta. {w['title']} · {mark}", callback_data=f"krs_w:{n}")])
        else:
            rows.append([InlineKeyboardButton(
                f"🔜 {n}-hafta. {w['title']} (tez orada)", callback_data="krs_soon")])
    return InlineKeyboardMarkup(rows)

def kb_week(u, n):
    w = WEEKS[n]
    rows = []
    for i, l in enumerate(w["lessons"]):
        if l["id"] in u["done"]:
            label = f"✅ {l['id']} {l['title']}"
        elif _unlocked(u, n, i):
            label = f"▶️ {l['id']} {l['title']}"
        else:
            label = f"🔒 {l['id']} {l['title']}"
        rows.append([InlineKeyboardButton(label, callback_data=f"krs_l:{n}:{i}")])
    if w["test"]:
        all_done = all(l["id"] in u["done"] for l in w["lessons"])
        t_label = (f"🧠 Haftalik test ({u['scores'].get(str(n), '—')}/"
                   f"{len(w['test'])})" if str(n) in u["scores"]
                   else "🧠 Haftalik test")
        rows.append([InlineKeyboardButton(
            t_label if all_done else "🔒 Test (avval darslarni tugating)",
            callback_data=f"krs_t:{n}" if all_done else "krs_locked")])
    rows.append([InlineKeyboardButton("⬅️ Haftalar", callback_data="krs_menu")])
    return InlineKeyboardMarkup(rows)

def _unlocked(u, n, i):
    """Dars ochiqmi: birinchi dars ochiq, qolganlari oldingisi o'qilgach."""
    w = WEEKS[n]
    if i == 0:
        # hafta ochiq bo'lishi uchun oldingi haftaning hamma darsi o'qilgan bo'lsin
        prev = [m for m in _weeks_with_content() if m < n]
        if not prev:
            return True
        pw = WEEKS[prev[-1]]
        return all(l["id"] in u["done"] for l in pw["lessons"])
    return w["lessons"][i - 1]["id"] in u["done"]


# ---------------- Asosiy oqim ----------------
async def cmd_kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = _load()
    u = _user(d, update.effective_user.id)
    intro = COURSE_INTRO
    if u["paid"]:
        intro += f"\n\n📊 Sizning jarayoningiz: <b>{_progress(u)}%</b>"
    await update.message.reply_text(intro, parse_mode="HTML",
                                    reply_markup=kb_home(u["paid"]))

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    d = _load()
    u = _user(d, uid)
    data = q.data

    if data == "krs_soon":
        await q.answer("Bu hafta darslari tez orada qo'shiladi! 🔜", show_alert=True)
        return
    if data == "krs_locked":
        await q.answer("Avval shu haftaning barcha darslarini o'qing 😊", show_alert=True)
        return

    if data == "krs_buy":
        await q.answer()
        await context.bot.send_invoice(
            chat_id=uid,
            title=COURSE_TITLE[:32],
            description="10 haftalik amaliy marketing kursi: darslar, "
                        "testlar, topshiriqlar va sertifikat. Umrbod kirish.",
            payload=PAYLOAD,
            provider_token="",          # Stars uchun bo'sh qoldiriladi
            currency="XTR",             # Telegram Stars valyutasi
            prices=[LabeledPrice("Marketing kursi", PRICE_STARS)],
        )
        return

    if data == "krs_menu":
        await q.answer()
        if not u["paid"]:
            await q.edit_message_text(COURSE_INTRO, parse_mode="HTML",
                                      reply_markup=kb_home(False))
            return
        await q.edit_message_text(
            f"📚 <b>{COURSE_TITLE}</b>\n\nJarayon: <b>{_progress(u)}%</b>\n"
            f"Haftani tanlang:", parse_mode="HTML", reply_markup=kb_weeks(u))
        return

    if data.startswith("krs_w:"):
        n = int(data.split(":")[1])
        if not u["paid"]:
            await q.answer("Bu bo'lim kurs a'zolari uchun ⭐", show_alert=True)
            return
        await q.answer()
        w = WEEKS[n]
        await q.edit_message_text(
            f"📅 <b>{n}-hafta. {w['title']}</b>\n\nDarsni tanlang:",
            parse_mode="HTML", reply_markup=kb_week(u, n))
        return

    if data.startswith("krs_l:"):
        _, n, i = data.split(":")
        n, i = int(n), int(i)
        lesson = WEEKS[n]["lessons"][i]
        if not lesson.get("free") and not u["paid"]:
            await q.answer("Bu dars kurs a'zolari uchun. 1.1-dars bepul! ⭐",
                           show_alert=True)
            return
        if u["paid"] and not _unlocked(u, n, i) and lesson["id"] not in u["done"]:
            await q.answer("Avval oldingi darsni tugating 😊", show_alert=True)
            return
        await q.answer()
        rows = []
        if lesson["id"] not in u["done"] and u["paid"]:
            rows.append([InlineKeyboardButton("✅ O'qib bo'ldim",
                                              callback_data=f"krs_done:{n}:{i}")])
        if not u["paid"]:
            rows.append([InlineKeyboardButton(
                f"⭐ To'liq kursni olish — {PRICE_STARS} Stars",
                callback_data="krs_buy")])
        else:
            rows.append([InlineKeyboardButton("⬅️ Hafta darslari",
                                              callback_data=f"krs_w:{n}")])
        await q.edit_message_text(lesson["text"], parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(rows))
        return

    if data.startswith("krs_done:"):
        _, n, i = data.split(":")
        n, i = int(n), int(i)
        lesson = WEEKS[n]["lessons"][i]
        if lesson["id"] not in u["done"]:
            u["done"].append(lesson["id"])
            _save(d)
        await q.answer(f"Barakalla! Jarayon: {_progress(u)}% 🎉")
        await q.edit_message_text(
            f"✅ <b>{lesson['id']}-dars tugatildi!</b>\n\n"
            f"Jarayon: <b>{_progress(u)}%</b>",
            parse_mode="HTML", reply_markup=kb_week(u, n))
        return

    # ---- Test oqimi ----
    if data.startswith("krs_t:"):
        n = int(data.split(":")[1])
        context.user_data["kurs_test"] = {"w": n, "q": 0, "score": 0}
        await q.answer()
        await _send_question(q, n, 0)
        return

    if data.startswith("krs_a:"):
        _, n, qi, opt = data.split(":")
        n, qi, opt = int(n), int(qi), int(opt)
        st = context.user_data.get("kurs_test")
        if not st or st["w"] != n or st["q"] != qi:
            await q.answer("Test qaytadan boshlang.", show_alert=True)
            return
        test = WEEKS[n]["test"]
        correct = test[qi]["correct"]
        if opt == correct:
            st["score"] += 1
            await q.answer("To'g'ri! ✅")
        else:
            await q.answer(f"Noto'g'ri. To'g'ri javob: "
                           f"{test[qi]['opts'][correct]}", show_alert=True)
        st["q"] += 1
        if st["q"] < len(test):
            await _send_question(q, n, st["q"])
        else:
            u["scores"][str(n)] = st["score"]
            _save(d)
            context.user_data.pop("kurs_test", None)
            done_all = _course_completed(u)
            extra = ("\n\n🏆 <b>Tabriklaymiz — mavjud darslarni to'liq "
                     "tugatdingiz!</b> Sertifikatingizni oling 👇") if done_all else ""
            rows = [[InlineKeyboardButton("⬅️ Hafta darslari",
                                          callback_data=f"krs_w:{n}")]]
            if done_all:
                rows.insert(0, [InlineKeyboardButton(
                    "🎓 Sertifikatni olish", callback_data="krs_cert")])
            await q.edit_message_text(
                f"🧠 <b>Test yakunlandi!</b>\n\n"
                f"Natija: <b>{st['score']}/{len(test)}</b>{extra}",
                parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))
        return

    if data == "krs_cert":
        await q.answer("Sertifikat tayyorlanmoqda... 🎓")
        name = q.from_user.full_name or "Kurs bitiruvchisi"
        img = make_certificate(name)
        if img:
            await context.bot.send_photo(
                chat_id=uid, photo=img,
                caption=f"🎓 Tabriklaymiz, {name}!\n"
                        f"«{COURSE_TITLE}» kursini muvaffaqiyatli tugatdingiz. "
                        f"Sertifikatni saqlab qo'ying va ulashing! 🎉\n\n"
                        f"@safaroov_blog")
        else:
            await context.bot.send_message(
                chat_id=uid, text=f"🎓 Tabriklaymiz, {name}! Kursni tugatdingiz!")
        return

def _course_completed(u):
    weeks = _weeks_with_content()
    if not weeks:
        return False
    for n in weeks:
        if not all(l["id"] in u["done"] for l in WEEKS[n]["lessons"]):
            return False
        if WEEKS[n]["test"] and str(n) not in u["scores"]:
            return False
    return True

async def _send_question(q, n, qi):
    test = WEEKS[n]["test"]
    item = test[qi]
    rows = [[InlineKeyboardButton(opt, callback_data=f"krs_a:{n}:{qi}:{j}")]
            for j, opt in enumerate(item["opts"])]
    await q.edit_message_text(
        f"🧠 <b>{n}-hafta testi</b> · savol {qi + 1}/{len(test)}\n\n{item['q']}",
        parse_mode="HTML", reply_markup=InlineKeyboardMarkup(rows))


# ---------------- To'lov ----------------
async def on_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pcq = update.pre_checkout_query
    await pcq.answer(ok=(pcq.invoice_payload == PAYLOAD))

async def on_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sp = update.message.successful_payment
    if sp.invoice_payload != PAYLOAD:
        return
    uid = update.effective_user.id
    d = _load()
    u = _user(d, uid)
    u["paid"] = True
    u["paid_at"] = time.strftime("%Y-%m-%d %H:%M")
    u["charge_id"] = sp.telegram_payment_charge_id
    _save(d)
    await update.message.reply_text(
        "🎉 <b>To'lov qabul qilindi — kursga xush kelibsiz!</b>\n\n"
        "Endi barcha darslar sizga ochiq. Darslar ketma-ket ochilib boradi — "
        "har birini o'qib, «✅ O'qib bo'ldim» bosing. Omad! 💪",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📚 Darslarni boshlash", callback_data="krs_menu")]]))
    if ADMIN_ID:
        try:
            await context.bot.send_message(
                ADMIN_ID, f"💰 Yangi kurs xaridi!\n"
                          f"👤 {update.effective_user.full_name} "
                          f"(@{update.effective_user.username})\n"
                          f"⭐ {PRICE_STARS} Stars")
        except Exception:
            pass

async def cmd_paysupport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "To'lov bo'yicha savol yoki muammo bo'lsa, adminга yozing: "
        "@safaroov_blog kanalidagi aloqa orqali. Har bir murojaat ko'rib chiqiladi.")

async def cmd_kurs_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    d = _load()
    buyers = [u for u in d["users"].values() if u.get("paid")]
    total = len(buyers) * PRICE_STARS
    finished = sum(1 for u in buyers if _course_completed(u))
    avg = (round(sum(_progress(u) for u in buyers) / len(buyers)) if buyers else 0)
    await update.message.reply_text(
        f"🎓 <b>Kurs statistikasi</b>\n\n"
        f"👥 Xaridorlar: <b>{len(buyers)}</b>\n"
        f"⭐ Jami tushum: <b>{total} Stars</b> (~${total * 0.013:.0f})\n"
        f"📊 O'rtacha jarayon: <b>{avg}%</b>\n"
        f"🏆 Tugatganlar: <b>{finished}</b>", parse_mode="HTML")


# ---------------- Sertifikat (Pillow) ----------------
_FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

def _font(size):
    for p in _FONTS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()

def make_certificate(name):
    if Image is None:
        return None
    W, H = 1400, 990
    img = Image.new("RGB", (W, H), (250, 247, 240))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, W - 40, H - 40], outline=(31, 111, 92), width=6)
    d.rectangle([56, 56, W - 56, H - 56], outline=(212, 175, 55), width=2)

    def center(text, y, font, fill):
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=fill)

    center("SERTIFIKAT", 130, _font(84), (31, 111, 92))
    center("Ushbu sertifikat bilan", 280, _font(34), (90, 90, 90))
    center(name[:40], 350, _font(64), (40, 40, 40))
    center("«Marketing kursi: noldan amaliyotgacha»", 470, _font(38), (90, 90, 90))
    center("kursini muvaffaqiyatli tamomlagani tasdiqlanadi", 530, _font(34), (90, 90, 90))
    from datetime import datetime
    center(datetime.now().strftime("%d.%m.%Y"), 660, _font(32), (120, 120, 120))
    center("SAFAROV BLOG", 780, _font(44), (31, 111, 92))
    center("t.me/safaroov_blog", 840, _font(28), (150, 130, 60))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------- Ro'yxatga olish ----------------
def register(app):
    app.add_handler(CommandHandler("kurs", cmd_kurs))
    app.add_handler(CommandHandler("kurs_stats", cmd_kurs_stats))
    app.add_handler(CommandHandler("paysupport", cmd_paysupport))
    app.add_handler(CallbackQueryHandler(on_callback, pattern=r"^krs_"))
    app.add_handler(PreCheckoutQueryHandler(on_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_paid))
    log.info("Kurs moduli ulandi: %s ta hafta, %s ta tayyor dars",
             len(WEEKS), _total_lessons())
