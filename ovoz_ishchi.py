#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OVOZ ISHCHISI — Mac'da ishlaydi, botga o'zbekcha ovoz yasab beradi
==================================================================
Bot videoni ovozli qilganda har bir ibora uchun "ish" navbatga qo'yadi.
Bu skript botdan ishni so'raydi, VoiceStudio'da (shu Mac'ning o'zida)
ovoz yasaydi va natijani botga yuklaydi.

NEGA SHUNDAY (teskari yo'nalish): VoiceStudio'ni internetga ochish
xavfli — tunnel orqali kelgan so'rovni u "shu kompyuterdan" deb o'ylaydi
va kalit so'ramaydi. Bu skript esa faqat CHIQUVCHI so'rov yuboradi:
Mac'da hech qanday port ochilmaydi, VoiceStudio faqat shu kompyuterga
ko'rinadi.

TALABLAR: Python 3.8+ (Mac'da bor), qo'shimcha kutubxona SHART EMAS.

ISHGA TUSHIRISH (Terminal):
    caffeinate -i python3 ovoz_ishchi.py https://<bot-domeni> <kalit>

    <bot-domeni>  — Railway'dagi bot manzili (Settings → Domains)
    <kalit>       — Railway Variables'dagi OVOZ_ISHCHI_KALIT
    caffeinate -i — Mac uxlab qolmasin (skript ishlab turganda)

QAYSI OVOZ: Railway'dagi VOICESTUDIO_VOICE. VoiceStudio'da ovozingizni
klonlab, unga nom bering (masalan "Muslim") va o'sha NOMNI yozing —
skript uni o'zi VoiceStudio'ning ichki ID'siga aylantiradi. Yozilmasa
yoki topilmasa — standart ovoz. Ishga tushganda mavjud ovozlar ro'yxati
chiqadi.

Ixtiyoriy (atrof-muhit o'zgaruvchilari):
    VOICESTUDIO=http://127.0.0.1:3900   VoiceStudio manzili
To'xtatish: Ctrl+C
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

VS = os.environ.get("VOICESTUDIO", "http://127.0.0.1:3900").rstrip("/")
UZUN_SOROV = 40          # bot 25 s gacha kutadi — zaxira bilan
VS_TIMEOUT = 600         # CPU'da uzun ibora sekin chiqishi mumkin


def _soat():
    return time.strftime("%H:%M:%S")


def ayt(matn):
    print(f"[{_soat()}] {matn}", flush=True)


def _sorov(url, usul="GET", malumot=None, sarlavhalar=None, timeout=30):
    req = urllib.request.Request(url, data=malumot, method=usul,
                                 headers=sarlavhalar or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _ssl_maslahat(e):
    """Mac'dagi eng ko'p uchraydigan muammo: python.org dan o'rnatilgan
    Python sertifikatlarni topmaydi. Tekshiruvni O'CHIRMAYMIZ — to'g'ri
    yo'lini aytamiz."""
    if isinstance(getattr(e, "reason", None), ssl.SSLError) or "CERTIFICATE" in str(e):
        ayt("⚠️  SSL sertifikat xatosi. Finder → Programs (Applications) → "
            "Python 3.x papkasidagi 'Install Certificates.command' ni bir marta "
            "ishga tushiring, keyin qayta urinib ko'ring.")
        return True
    return False


def voicestudio_tirikmi():
    try:
        kod, _ = _sorov(VS + "/health", timeout=5)
        return kod == 200
    except Exception:
        return False


# ----------------------------------------------------------------------
# OVOZ NOMI -> ID
# ----------------------------------------------------------------------
# VoiceStudio /v1/audio/speech faqat profilning ICHKI ID'sini taniydi
# (uzun, "3f2a9c1e-..." ko'rinishida). Noma'lum satr kelsa u JIMGINA
# standart ovozga o'tadi — ya'ni "Muslim" deb yozgan odam o'z ovozini
# eshitmay, nima uchunligini ham bilmay qolardi. Shuning uchun nomni shu
# yerda, Mac'ning o'zida, ro'yxatdan topamiz.
_ovozlar = {"vaqt": 0.0, "royxat": []}
_ogohlantirilgan = set()


def ovozlar_royxati(yangila=False):
    """VoiceStudio'dagi klonlangan ovozlar: [{"voice_id", "name"}, ...]."""
    if yangila or time.time() - _ovozlar["vaqt"] > 60:
        try:
            _, tana = _sorov(VS + "/v1/audio/voices", timeout=10)
            d = json.loads(tana)
            _ovozlar["royxat"] = [v for v in (d.get("voices") or [])
                                  if v.get("type") == "profile" and v.get("voice_id")]
            _ovozlar["vaqt"] = time.time()
        except Exception:
            pass                       # eski ro'yxat bilan davom etamiz
    return _ovozlar["royxat"]


def _qidir(nom, royxat):
    for v in royxat:
        if v["voice_id"] == nom:
            return nom
    past = nom.strip().lower()
    for v in royxat:
        if (v.get("name") or "").strip().lower() == past:
            return v["voice_id"]
    return None


def ovozni_top(nom):
    """Nom yoki ID -> VoiceStudio ID. Topilmasa — 'default' (bir marta
    ogohlantiriladi)."""
    nom = (nom or "").strip()
    if not nom or nom == "default":
        return "default"
    topildi = _qidir(nom, ovozlar_royxati())
    if topildi is None:                # hozirgina klonlangan bo'lishi mumkin
        topildi = _qidir(nom, ovozlar_royxati(yangila=True))
    if topildi:
        return topildi
    if nom not in _ogohlantirilgan:
        _ogohlantirilgan.add(nom)
        bor = ", ".join(v.get("name") or v["voice_id"] for v in ovozlar_royxati())
        ayt(f"⚠️  '{nom}' degan ovoz VoiceStudio'da topilmadi — standart ovoz "
            f"ishlatiladi. Mavjud ovozlar: {bor or 'hali yo`q'}")
    return "default"


def ovoz_yasa(ish):
    """VoiceStudio'ning OpenAI bilan bir xil /v1/audio/speech yo'li."""
    tana = json.dumps({
        "model": ish.get("model") or "omnivoice",
        "voice": ovozni_top(ish.get("ovoz")),
        "input": ish["matn"],
        "language": ish.get("til") or "uz",
        "response_format": "wav",
    }).encode("utf-8")
    kod, wav = _sorov(VS + "/v1/audio/speech", "POST", tana,
                      {"Content-Type": "application/json"}, VS_TIMEOUT)
    if kod != 200 or not wav:
        raise RuntimeError(f"VoiceStudio javobi {kod}")
    return wav


def xato_matni(e):
    """VoiceStudio xatosini qisqa va tushunarli qiladi."""
    if isinstance(e, urllib.error.HTTPError):
        try:
            tana = json.loads(e.read().decode("utf-8", "replace"))
            xabar = (tana.get("error") or {}).get("message") or tana.get("detail")
            if xabar:
                return f"VoiceStudio {e.code}: {str(xabar)[:200]}"
        except Exception:
            pass
        return f"VoiceStudio {e.code}"
    return str(e)[:200]


def main():
    args = sys.argv[1:]
    bot = (args[0] if len(args) > 0 else os.environ.get("BOT_URL", "")).rstrip("/")
    kalit = args[1] if len(args) > 1 else os.environ.get("OVOZ_ISHCHI_KALIT", "")
    if not bot.startswith("http") or not kalit:
        print(__doc__)
        sys.exit(2)
    bot_sarlavha = {"Authorization": f"Bearer {kalit}"}

    ayt(f"Bot: {bot}")
    ayt(f"VoiceStudio: {VS}")
    while not voicestudio_tirikmi():
        ayt("⏳ VoiceStudio javob bermayapti — ilova ochiqmi? 10 s dan keyin "
            "yana tekshiraman...")
        time.sleep(10)
    ayt("✅ VoiceStudio tayyor.")
    royxat = ovozlar_royxati(yangila=True)
    if royxat:
        ayt("🎙 Klonlangan ovozlar: "
            + ", ".join(v.get("name") or v["voice_id"] for v in royxat))
        ayt("   Railway'dagi VOICESTUDIO_VOICE ga shu nomlardan birini yozing.")
    else:
        ayt("🎙 Klonlangan ovoz yo'q — standart ovoz ishlatiladi.")
    ayt("Botdan ish kutilmoqda... (Ctrl+C — to'xtatish)")

    bajarildi, xatolar, tarmoq_xato = 0, 0, False
    while True:
        # --- 1) botdan ish so'raymiz ---
        try:
            kod, tana = _sorov(bot + "/api/ovoz/ish", sarlavhalar=bot_sarlavha,
                               timeout=UZUN_SOROV)
            if tarmoq_xato:
                ayt("✅ Bot bilan aloqa tiklandi.")
                tarmoq_xato = False
        except urllib.error.HTTPError as e:
            if e.code == 401:
                ayt("❌ Kalit noto'g'ri — Railway'dagi OVOZ_ISHCHI_KALIT bilan solishtiring.")
                sys.exit(1)
            if e.code == 404:
                ayt("❌ Botda ishchi yoqilmagan: Railway'da OVOZ_ISHCHI_KALIT yo'q "
                    "yoki 24 belgidan qisqa. Yoki bot manzili noto'g'ri.")
                sys.exit(1)
            ayt(f"⚠️  Bot xatosi {e.code} — 10 s dan keyin qayta.")
            time.sleep(10)
            continue
        except Exception as e:
            if not tarmoq_xato:
                if not _ssl_maslahat(e):
                    ayt(f"⚠️  Botga ulanib bo'lmadi ({str(e)[:80]}) — qayta urinaman...")
                tarmoq_xato = True
            time.sleep(5)
            continue

        if kod == 204 or not tana:
            continue                                    # ish yo'q — yana so'raymiz
        ish = json.loads(tana)

        # --- 2) ovoz yasaymiz ---
        t0 = time.time()
        try:
            wav = ovoz_yasa(ish)
        except Exception as e:
            xatolar += 1
            sabab = xato_matni(e)
            ayt(f"❌ Ibora ovozlanmadi: {sabab}")
            try:
                _sorov(f"{bot}/api/ovoz/ish/{ish['id']}/xato", "POST",
                       json.dumps({"sabab": sabab}).encode("utf-8"),
                       {**bot_sarlavha, "Content-Type": "application/json"})
            except Exception:
                pass
            if not voicestudio_tirikmi():
                ayt("⏳ VoiceStudio yopilib qoldi — qayta ochilishini kutaman...")
                while not voicestudio_tirikmi():
                    time.sleep(10)
                ayt("✅ VoiceStudio qaytdi.")
            continue

        # --- 3) botga yuklaymiz ---
        try:
            _sorov(f"{bot}/api/ovoz/ish/{ish['id']}", "POST", wav,
                   {**bot_sarlavha, "Content-Type": "audio/wav"}, timeout=60)
            bajarildi += 1
            qisqa = ish["matn"][:50] + ("…" if len(ish["matn"]) > 50 else "")
            ayt(f"✓ {bajarildi}. ({time.time() - t0:.1f} s) {qisqa}")
        except urllib.error.HTTPError as e:
            # 409 — bot bu iborani kutmay qo'ygan (vaqti o'tgan). Zararsiz.
            ayt(f"⚠️  Natija qabul qilinmadi ({e.code}) — ibora eskirgan bo'lishi mumkin.")
        except Exception as e:
            ayt(f"⚠️  Natijani yuklab bo'lmadi: {str(e)[:80]}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        ayt("To'xtatildi.")
