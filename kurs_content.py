# -*- coding: utf-8 -*-
"""
kurs_content.py — Marketing kursi kontenti.
1-hafta to'liq tayyor; qolgan haftalar matni bosqichma-bosqich qo'shiladi
(WEEKS[n]["lessons"] bo'sh bo'lsa, bot "Tez orada" deb ko'rsatadi).
"""

COURSE_TITLE = "Marketing kursi: noldan amaliyotgacha"
COURSE_INTRO = (
    "🎓 <b>Marketing kursi: noldan amaliyotgacha</b>\n\n"
    "10 haftalik amaliy kurs — marketing asoslaridan to'liq strategiya "
    "tuzishgacha. Har hafta: 3 ta dars, amaliy topshiriq va test.\n\n"
    "📚 <b>Dasturda:</b> marketing asoslari, auditoriya va brend, SMM "
    "(Instagram + Telegram), copywriting, vizual kontent, Meta Ads, "
    "Google Ads, analitika, funnel va yakuniy loyiha.\n\n"
    "✅ Darslar toza o'zbek tilida, O'zbekiston bozori misollari bilan\n"
    "🔓 Birinchi dars — <b>bepul</b>, sinab ko'ring\n"
    "🏆 Kursni tugatganlarga shaxsiy sertifikat\n\n"
    "Narx: <b>{price} ⭐</b> (bir martalik, umrbod kirish)"
)

WEEKS = {
    1: {
        "title": "Marketing asoslari",
        "lessons": [
            {
                "id": "1.1",
                "title": "Marketing nima va u nima uchun kerak",
                "free": True,
                "text": (
"📖 <b>1.1-dars. Marketing nima va u nima uchun kerak</b>\n\n"
"Ko'pchilik marketingni reklama deb o'ylaydi. Bu — eng keng tarqalgan "
"xato. Reklama — marketingning faqat bitta, eng ko'rinadigan qismi. "
"Marketing esa butun jarayon: <b>kimga</b> nima kerakligini tushunish, "
"<b>nima</b> taklif qilishni hal qilish, <b>qanday</b> yetkazishni "
"topish va <b>qancha</b>ga sotishni belgilash.\n\n"
"Oddiy misol. Toshkentda ikkita nonvoyxona bor. Birinchisi shunchaki "
"non yopadi va kutadi. Ikkinchisi esa avval so'rab bildi: atrofda "
"ofislar ko'p, odamlar ertalab shoshiladi. U ertalabki soatlarda "
"issiq somsa va qahvani birga taklif qildi, Telegram orqali oldindan "
"buyurtma qabul qildi. Ikkalasi ham non yopadi — lekin ikkinchisi "
"marketing qilyapti.\n\n"
"<b>Marketing va reklamaning farqi</b>\n\n"
"Reklama: \"Bizning mahsulot zo'r, sotib oling!\" deb baqirish.\n"
"Marketing: odamga nima kerakligini bilib, aynan shuni, aynan unga "
"qulay joyda va vaqtda taklif qilish. Yaxshi marketing bo'lsa, "
"reklamaga kamroq pul ketadi — chunki mahsulotning o'zi \"o'zini "
"sotadi\".\n\n"
"<b>Marketing qanday o'zgardi</b>\n\n"
"Ilgari: gazeta, televizor, banner — kompaniya gapiradi, mijoz "
"eshitadi. Bir tomonlama.\n"
"Hozir: Instagram, Telegram, TikTok — mijoz javob qaytaradi, izoh "
"yozadi, do'stiga yuboradi. Ikki tomonlama suhbat. Shuning uchun "
"bugungi marketolog \"e'lon beruvchi\" emas, <b>suhbat quruvchi</b>.\n\n"
"Bu o'zgarish kichik biznes uchun ulkan imkoniyat: endi televizorga "
"million to'lash shart emas. Telefon, ozgina bilim va to'g'ri "
"strategiya — boshlash uchun yetarli. Aynan shu bilimni ushbu kursda "
"olasiz.\n\n"
"💡 <b>Esda qoladigan fikr:</b> marketing — sotish emas, mijozni "
"tushunish san'ati. Sotish — to'g'ri marketingning tabiiy natijasi."
                ),
            },
            {
                "id": "1.2",
                "title": "4P modeli: marketingning tayanch formulasi",
                "free": False,
                "text": (
"📖 <b>1.2-dars. 4P modeli: marketingning tayanch formulasi</b>\n\n"
"Har qanday marketing strategiyasi 4 ta savolga javobdan boshlanadi. "
"Bu savollar 4P deb ataladi — ingliz tilidagi to'rt so'zning bosh "
"harflari:\n\n"
"<b>1. Product (Mahsulot) — nima sotyapsiz?</b>\n"
"Faqat buyumning o'zi emas: sifati, qadoqlanishi, kafolati, xizmati. "
"Mijoz aslida mahsulotni emas, <i>muammosining yechimini</i> sotib "
"oladi. Parda sotayotgan do'kon aslida \"uyning shinamligi\"ni sotadi.\n\n"
"<b>2. Price (Narx) — qanchaga?</b>\n"
"Narx — pozitsiya. Arzon narx \"ommabop\", qimmat narx \"premium\" "
"degan xabar beradi. Xato: hammadan arzon bo'lishga urinish — bu "
"poygada har doim yutqazuvchi bor. To'g'ri: narxga qiymat qo'shish "
"(yetkazib berish, kafolat, xizmat).\n\n"
"<b>3. Place (Joy) — qayerda sotasiz?</b>\n"
"Bugun \"joy\" — bu faqat do'kon emas: Instagram-sahifa, Telegram-bot, "
"marketpleys, veb-sayt. Qoida oddiy: <b>mijozingiz qayerda bo'lsa, "
"siz o'sha yerda bo'ling</b>. O'zbekistonda bu ko'pincha Telegram va "
"Instagram degani.\n\n"
"<b>4. Promotion (Ilgari surish) — qanday bildirasiz?</b>\n"
"Reklama, aksiyalar, blogerlar, kontent — mijoz sizni qanday bilib "
"oladi. Muhim qoida: promotion 4P'ning oxirgisi. Avval mahsulot, "
"narx va joy to'g'ri bo'lsin — yomon mahsulotni zo'r reklama "
"qutqarmaydi, aksincha tezroq \"ko'madi\".\n\n"
"<b>Xizmat sohasi uchun +3P</b>\n\n"
"Xizmat sotsangiz (salon, ta'lim, klinika) yana uchta P qo'shiladi: "
"<b>People</b> (xodimlar — mijoz bilan kim gaplashadi), <b>Process</b> "
"(jarayon — buyurtmadan natijagacha qanchalik silliq) va <b>Physical "
"evidence</b> (moddiy dalil — interyer, brend materiallari, "
"sertifikatlar).\n\n"
"💡 <b>Amaliyotda:</b> biror tanish biznesni oling va 4 savolga javob "
"yozing. Qaysi \"P\" eng zaif? Odatda muammo aynan bitta P'da "
"yashiringan bo'ladi — va uni topish strategiyaning yarmi."
                ),
            },
            {
                "id": "1.3",
                "title": "Marketing kanallari: pullik, organik va sizniki",
                "free": False,
                "text": (
"📖 <b>1.3-dars. Marketing kanallari: pullik, organik va sizniki</b>\n\n"
"Mahsulot tayyor, narx bor — endi mijozga qanday yetib boramiz? "
"Barcha yo'llar uch guruhga bo'linadi. Bu bo'linishni bilish sizga "
"byudjetni to'g'ri taqsimlashni o'rgatadi.\n\n"
"<b>1. Owned media — o'zingizniki</b>\n"
"Telegram-kanalingiz, Instagram-sahifangiz, veb-saytingiz, mijozlar "
"bazangiz. Bu — sizning mulkingiz: hech kim tortib ololmaydi, har "
"post bepul. Eng qimmatli aktiv, chunki bir marta yig'ilgan "
"auditoriyaga qayta-qayta bepul murojaat qilasiz.\n\n"
"<b>2. Paid media — pullik</b>\n"
"Instagram reklamasi, Google Ads, blogerga to'lov, Telegram'dagi "
"reklama postlari. Afzalligi: tez natija. Kamchiligi: pul tugadi — "
"oqim ham tugadi. Pullik kanal \"ijaradagi uy\" kabi: yashash mumkin, "
"lekin sizniki emas.\n\n"
"<b>3. Earned media — mehnat bilan topilgan</b>\n"
"Mijozlarning tavsiyalari, repostlar, izohlar, OAV maqolalari. Eng "
"ishonchli turi — chunki odamlar reklamaga emas, boshqa odamlarga "
"ishonadi. Buni sotib bo'lmaydi, faqat yaxshi mahsulot va xizmat "
"bilan \"topib olinadi\".\n\n"
"<b>To'g'ri strategiya — uchtasining kombinatsiyasi</b>\n\n"
"Yangi biznes odatiy xatosi: bor pulni pullik reklamaga quyish. "
"Reklama trafik beradi, lekin u qayerga kelsin? Avval owned media "
"(kanal, sahifa) tayyorlanadi — \"uy\" quriladi. Keyin paid media "
"o'sha uyga mehmon olib keladi. Mehmonlar rozi bo'lsa, earned media "
"o'zi ishlay boshlaydi — ular do'stlarini boshlab keladi.\n\n"
"O'zbekiston misolida: ko'plab muvaffaqiyatli do'konlar avval "
"Instagram'da kontent bilan auditoriya yig'adi (owned), keyin "
"targetlangan reklama yoqadi (paid), mijozlar \"stories\"da ulashadi "
"(earned). Uchala g'ildirak birga aylanganda marketing arzon va "
"barqaror bo'ladi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> pullik reklama — gugurt, owned media — "
"o'tin. Gugurtni o'tinsiz yoqib bo'lmaydi.\n\n"
"✍️ <b>Haftalik topshiriq:</b> o'zingiz tanlagan (real yoki hayoliy) "
"biznes uchun 4P tahlilini yozing va uning owned/paid/earned "
"kanallarini sanab chiqing. Javobingizni shu botga oddiy xabar qilib "
"yuboring — ko'rib chiqamiz!"
                ),
            },
        ],
        "test": [
            {"q": "Marketing va reklamaning asosiy farqi nimada?",
             "opts": ["Farqi yo'q, ikkalasi bir narsa",
                      "Reklama — marketingning bir qismi xolos",
                      "Marketing faqat katta bizneslar uchun",
                      "Reklama marketingdan kengroq tushuncha"],
             "correct": 1},
            {"q": "4P modelida \"Place\" nimani anglatadi?",
             "opts": ["Ofis joylashuvi",
                      "Mahsulot ishlab chiqarilgan joy",
                      "Mijoz mahsulotni topadigan/sotib oladigan joy",
                      "Reklama joylashtirilgan joy"],
             "correct": 2},
            {"q": "Xizmat sohasi uchun qo'shimcha 3P qaysilar?",
             "opts": ["People, Process, Physical evidence",
                      "Price, Product, Promotion",
                      "Plan, Profit, Power",
                      "Platform, Post, Person"],
             "correct": 0},
            {"q": "Telegram-kanalingiz qaysi media turiga kiradi?",
             "opts": ["Paid media", "Earned media", "Owned media", "Hech qaysisiga"],
             "correct": 2},
            {"q": "Mijoz tavsiyasi va repostlar — bu...",
             "opts": ["Owned media", "Earned media", "Paid media", "Spam"],
             "correct": 1},
            {"q": "Yangi biznes uchun to'g'ri ketma-ketlik qaysi?",
             "opts": ["Avval pullik reklama, keyin sahifa ochish",
                      "Faqat pullik reklama yetarli",
                      "Avval owned media tayyorlash, keyin paid bilan trafik olib kelish",
                      "Faqat earned media'ga tayanish"],
             "correct": 2},
        ],
    },
    2: {
        "title": "Target auditoriya va brend",
        "lessons": [
            {
                "id": "2.1",
                "title": "Target auditoriya: \"hamma\" degan mijoz yo'q",
                "free": False,
                "text": (
"📖 <b>2.1-dars. Target auditoriya: \"hamma\" degan mijoz yo'q</b>\n\n"
"Yangi tadbirkordan \"mijozingiz kim?\" deb so'rasangiz, eng ko'p "
"eshitiladigan javob: \"Hamma!\" Bu — marketingdagi eng qimmat xato. "
"Hammaga gapirgan hech kimga gapirmaydi: reklamangiz hech kimning "
"yuragiga tegmaydi, pul esa sovuriladi.\n\n"
"<b>Hayotiy keys.</b> Toshkentdagi bir bolalar kiyimi do'koni "
"reklamaga oyiga 3 mln so'm sarflab, \"18-55 yosh, Toshkent\" degan "
"keng auditoriyaga ko'rsatardi — natija: 1 so'm reklamadan 2 so'm "
"savdo. Keyin auditoriyani toraytirdi: \"25-40 yoshli onalar, "
"farzandi 0-7 yosh, o'rtacha daromad\". Reklama matnini ham onalar "
"tiliga o'zgartirdi (\"yuvishga chidamli, terga qichitmaydi\"). O'sha "
"byudjet bilan natija: 1 so'mdan 7 so'm. Auditoriya torayai — daromad "
"o'sdi. Bu paradoks emas, qoida.\n\n"
"<b>Segmentatsiya: auditoriyani qanday bo'lish mumkin</b>\n\n"
"1. <b>Demografik</b> — yosh, jins, daromad, kasb. Eng oddiy, lekin "
"yuzaki.\n"
"2. <b>Geografik</b> — shahar, tuman, hatto mahalla. Mahalliy biznes "
"uchun oltin: Chilonzordagi go'zallik saloniga Sergeli reklamasi "
"befoyda.\n"
"3. <b>Psixografik</b> — qadriyatlar, turmush tarzi, qo'rquvlar, "
"orzular. Eng chuqur va eng kuchli daraja: \"25-40 yoshli ona\" emas, "
"\"bolam sog'lom kiyinsin deb sifat qidiradigan, vaqti tig'iz ona\".\n\n"
"<b>Buyer persona — mijozning \"portreti\"</b>\n\n"
"Professional marketologlar auditoriyani jonli odam qiyofasiga "
"keltiradi. Formula: ism + yosh + kasb + kunlik hayoti + muammosi + "
"orzusi + qayerda \"yashaydi\" (qaysi ijtimoiy tarmoq) + sotib olishga "
"nima to'sqinlik qiladi.\n\n"
"Misol: <i>\"Nilufar, 32 yosh, ikki farzandli ona, bankda ishlaydi. "
"Kechqurun 30 daqiqa Instagram ko'radi. Muammosi: bolaga sifatli "
"kiyimni qidirishga vaqt yo'q. Qo'rquvi: internetdan olsa o'lchami "
"to'g'ri kelmasligi. Uni ishontirvchi narsa: real onalarning "
"videolari va oson almashtirish kafolati.\"</i>\n\n"
"Endi e'tibor bering: shu portret qo'lda bo'lsa, reklama matni ham, "
"kontent ham, hatto qaytarish siyosati ham o'z-o'zidan aniq bo'lib "
"qoladi. Persona — barcha marketing qarorlarining kompasi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> auditoriyani toraytirish — mijozlarni "
"yo'qotish emas. Bu \"aynan menga aytilgan\" degan hisni yaratish, va "
"odamlar aynan shunday joyga pul to'laydi."
                ),
            },
            {
                "id": "2.2",
                "title": "Brend: nima uchun bir xil mahsulot har xil narxda sotiladi",
                "free": False,
                "text": (
"📖 <b>2.2-dars. Brend: nima uchun bir xil mahsulot har xil narxda "
"sotiladi</b>\n\n"
"Ikki sotuvchi bir xil tog' asalini sotadi. Birinchisi bankaga quyib "
"\"Asal, 1 kg\" deb yozadi — 80 ming so'mga zo'rg'a oladi. Ikkinchisi "
"chiroyli idishga quyadi, asalarichining otasi bilan suratini "
"qo'yadi, \"Bobomning 40 yillik asalarichilik an'anasi\" deb hikoya "
"yozadi, har buyurtmaga qo'lda yozilgan rahmat xati qo'shadi — 150 "
"mingga navbat bilan sotadi. Mahsulot bitta. Farq — brendda.\n\n"
"<b>Brend nima (va nima emas)</b>\n\n"
"Brend — logo emas. Brend — odamlar sizni eslaganda paydo bo'ladigan "
"<b>his va ishonch</b>. Logo, ranglar, nom — bular brendning "
"ko'rinadigan qismi (identifikatsiya). Ko'rinmaydigan qismi esa "
"muhimroq: va'dangiz (\"bizdan olsangiz — xotirjamsiz\") va uni har "
"safar bajarishingiz. Brend har bir mijoz tajribasidan g'isht-g'isht "
"quriladi: javob tezligingiz, qadoqlashingiz, xatoni qanday "
"to'g'irlashingiz.\n\n"
"<b>Brend ovozi (tone of voice)</b>\n\n"
"Brendingiz \"gapirsa\", qanday gapiradi? Rasmiy va ishonchli "
"(klinika, bank)? Samimiy va do'stona (kafe, bolalar mahsulotlari)? "
"Qat'iy qoida: <b>ovoz hamma joyda bir xil bo'lsin</b> — postda "
"hazilkash, direktda quruq rasmiy bo'lsangiz, mijoz ongida ikki xil "
"odam paydo bo'ladi va ishonch sinadi.\n\n"
"Ovozni aniqlashning sodda usuli — 3 ta sifat tanlang va hamma matnni "
"shunga solishtiring. Masalan: \"samimiy, sodda, g'amxo'r\" yoki "
"\"professional, aniq, ishonchli\". Shu uch so'z sizning tahririy "
"qoidangiz bo'ladi.\n\n"
"<b>Vizual izchillik</b>\n\n"
"Odamlar brendni ongsiz taniydi: rang, shrift, rasm uslubi. Qoida "
"oddiy: 2-3 asosiy rang, 1-2 shrift, bitta rasm uslubi — va hamma "
"joyda bir xil. Instagram profilingizga qarang: 9 ta post bir "
"\"oiladan\"mi yoki 9 xil do'kondan yig'ilgandekmi? Izchillik "
"professionallikning birinchi belgisi va u bepul.\n\n"
"💡 <b>Esda qoladigan fikr:</b> odamlar mahsulotga pul to'laydi, "
"brendga esa <b>ko'proq</b> pul to'laydi. Brend — narxingizga "
"qo'shiladigan ishonch foizi."
                ),
            },
            {
                "id": "2.3",
                "title": "Raqobatchilar tahlili: bepul razvedka san'ati",
                "free": False,
                "text": (
"📖 <b>2.3-dars. Raqobatchilar tahlili: bepul razvedka san'ati</b>\n\n"
"Ko'p tadbirkorlar raqobatchidan qo'rqadi yoki uni mensimaydi. "
"Ikkalasi ham xato. Professional yondashuv: raqobatchi — sizga bepul "
"ishlayotgan tajriba laboratoriyasi. U allaqachon pul sarflab nima "
"ishlashini va nima ishlamasligini sinab bo'lgan — sizga faqat "
"kuzatish qoladi.\n\n"
"<b>Nimalarni kuzatamiz (razvedka ro'yxati)</b>\n\n"
"Asosiy 3-5 raqobatchining: qaysi postlari eng ko'p izoh-layk "
"olganini (bu — auditoriya nimani xohlashining bepul xaritasi), "
"narxlari va aksiyalarini, mijozlar izohlaridagi <b>shikoyatlarni</b> "
"— mana bu oltin kon: ularning zaif joyi sizning imkoniyatingiz. "
"Raqibning mijozi \"yetkazib berish sekin\" deb yozayaptimi? Sizning "
"reklamangiz tayyor: \"24 soatda yetkazamiz\".\n\n"
"<b>SWOT — tahlilni tartibga soluvchi jadval</b>\n\n"
"To'rt katakli sodda usul, o'zingizni raqobat muhitida ko'rish uchun:\n\n"
"S — <b>Kuchli tomonlar</b>: nimada raqiblardan ustunsiz? (tajriba, "
"narx, joylashuv, xizmat)\n"
"W — <b>Zaif tomonlar</b>: nimada orqadasiz? (halol yozing — bu "
"ro'yxat rivojlanish rejangiz)\n"
"O — <b>Imkoniyatlar</b>: bozorda qanday ochiq eshiklar bor? "
"(raqiblar e'tibor bermayotgan segment, yangi platforma)\n"
"T — <b>Tahdidlar</b>: nima xavf solishi mumkin? (yangi raqib, "
"narxlar urushi, ta'minot muammosi)\n\n"
"<b>Hayotiy keys.</b> Toshkentda tort buyurtma qiladigan kichik "
"studiya SWOT o'tkazdi. Kuchli tomoni: qo'lda ishlangan noyob "
"dizayn. Zaifi: narxi raqiblardan 30% qimmat. Imkoniyat: raqiblar "
"izohlarida \"aytilgan rasmga o'xshamadi\" degan shikoyat ko'p "
"uchrardi. Studiya strategiyani shunga qurdi: \"rasmdagidek "
"chiqmasa — pulni qaytaramiz\" kafolati. Qimmat narx endi kamchilik "
"emas, sifat belgisiga aylandi — chunki kafolat unga asos berdi. "
"Zaif tomonni kuchli tomon bilan yopish — SWOT'ning asl mohiyati "
"shu.\n\n"
"💡 <b>Esda qoladigan fikr:</b> raqobatchini ko'chirmang — uning "
"xatolaridan o'rganing. Ko'chirgan doim ikkinchi bo'ladi.\n\n"
"✍️ <b>Haftalik topshiriq:</b> o'z biznesingiz (yoki tanlagan "
"loyihangiz) uchun bitta buyer persona yozing (ism, yosh, muammo, "
"qo'rquv, qayerda \"yashaydi\") va 2 ta raqobatchining izohlaridan "
"kamida 3 ta shikoyat toping. Javobni shu botga xabar qilib "
"yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "\"Bizning mijoz — hamma\" degan yondashuv nega xato?",
             "opts": ["Chunki hamma pul topa olmaydi",
                      "Hammaga qaratilgan xabar hech kimga ta'sir qilmaydi",
                      "Reklama tizimlari bunga ruxsat bermaydi",
                      "Aslida xato emas, to'g'ri yondashuv"],
             "correct": 1},
            {"q": "\"Qadriyatlar, qo'rquvlar va turmush tarzi bo'yicha bo'lish\" — bu qaysi segmentatsiya?",
             "opts": ["Demografik", "Geografik", "Psixografik", "Iqtisodiy"],
             "correct": 2},
            {"q": "Buyer persona nima?",
             "opts": ["Eng ko'p pul to'lagan mijoz",
                      "Ideal mijozning jonli, batafsil portreti",
                      "Kompaniya rahbarining tavsifi",
                      "Reklama kabinetidagi sozlama nomi"],
             "correct": 1},
            {"q": "Brend — bu birinchi navbatda...",
             "opts": ["Chiroyli logo va ranglar",
                      "Qimmat narx",
                      "Odamlardagi his va ishonch",
                      "Ro'yxatdan o'tgan tovar belgisi"],
             "correct": 2},
            {"q": "Tone of voice bo'yicha to'g'ri qoida qaysi?",
             "opts": ["Har platformada boshqacha ohang bo'lishi kerak",
                      "Ohang hamma joyda bir xil bo'lishi kerak",
                      "Faqat rasmiy ohang ishlaydi",
                      "Ohangning ahamiyati yo'q"],
             "correct": 1},
            {"q": "Raqobatchi mijozlarining shikoyatlari nega qimmatli?",
             "opts": ["Ularni raqibga qarshi ishlatish uchun",
                      "Ularning zaif joyi — sizning imkoniyatingiz",
                      "Shikoyatlarning ahamiyati yo'q",
                      "Ularni o'z sahifangizga ko'chirish uchun"],
             "correct": 1},
        ],
    },
    3: {"title": "SMM: Instagram va Telegram", "lessons": [], "test": []},
    4: {"title": "Kontent strategiyasi va copywriting", "lessons": [], "test": []},
    5: {"title": "Vizual kontent va kontent kalendari", "lessons": [], "test": []},
    6: {"title": "Meta Ads: pullik reklama", "lessons": [], "test": []},
    7: {"title": "Google Ads asoslari", "lessons": [], "test": []},
    8: {"title": "Analitika va metrikalar", "lessons": [], "test": []},
    9: {"title": "Funnel, email va influencer marketing", "lessons": [], "test": []},
    10: {"title": "Strategiya va yakuniy loyiha", "lessons": [], "test": []},
}
