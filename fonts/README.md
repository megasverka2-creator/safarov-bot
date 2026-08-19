# fonts/

Bu papkadagi shriftlar botning ichida ishlatiladi: subtitr (ffmpeg/libass
`fontsdir` orqali) va kartalar (Pillow orqali). Railway'da tizim shriftlari
kafolatlanmagani uchun shriftlar repo bilan birga boradi.

| Fayl | Nima uchun | Litsenziya |
|---|---|---|
| `Montserrat-ExtraBold.ttf` | Subtitr va karta sarlavhalari | SIL OFL 1.1 — `OFL-Montserrat.txt` |
| `Montserrat-SemiBold.ttf` | Karta ikkinchi darajali matni | SIL OFL 1.1 — `OFL-Montserrat.txt` |
| `TTDrugs-BoldItalic.ttf` | Brend yozuvi (video ustidagi @kanal) | — |

Montserrat fayllari Google Fonts'dagi variable shriftdan `fonttools`
yordamida qat'iy og'irlikda (800 va 600) ajratib olingan. Shu sababli
libass'ga soxta qalinlashtirish (`Bold=1`) kerak emas — harflar allaqachon
qalin, sun'iy qalinlashtirish esa chekkalarni buzadi.

Shrift oilasining nomi fayl nomiga emas, ichidagi metama'lumotga bog'liq:
`Montserrat ExtraBold` va `Montserrat SemiBold`. `force_style=FontName=...`
da aynan shu nom yoziladi.

Yangi shrift qo'shish: `.ttf` faylni shu papkaga tashlang, keyin
`/shriftlar` buyrug'i botdagi mavjud nomlarni ko'rsatadi.
