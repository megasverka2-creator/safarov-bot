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
    3: {
        "title": "SMM: Instagram va Telegram",
        "lessons": [
            {
                "id": "3.1",
                "title": "Platformalar xaritasi: qaysi biznes qayerda yashaydi",
                "free": False,
                "text": (
"📖 <b>3.1-dars. Platformalar xaritasi: qaysi biznes qayerda "
"yashaydi</b>\n\n"
"Yangi biznesning odatiy xatosi: \"hamma joyda bo'lishimiz kerak!\" "
"— va to'rtta platformada to'rtta o'lik sahifa paydo bo'ladi. "
"Professional yondashuv teskari: <b>mijozingiz qayerda bo'lsa, bor "
"kuchni o'sha yerga qarating</b>. Bitta jonli sahifa to'rtta "
"o'likdan yuz barobar kuchli.\n\n"
"<b>O'zbekiston bozorida platformalar taqsimoti</b>\n\n"
"📸 <b>Instagram</b> — vizual savdo maydoni. Kiyim, taom, go'zallik, "
"dekor, sovg'alar — ko'z bilan tanlanadigan hamma narsa shu yerda. "
"Auditoriya keng, ayollar ulushi yuqori. Kuchli tomoni: reels orqali "
"bepul yangi auditoriyaga chiqish mumkin.\n\n"
"✈️ <b>Telegram</b> — O'zbekistonning \"ikkinchi interneti\". Bu yerda "
"odamlar yangilik o'qiydi, kanalga obuna bo'ladi, botdan buyurtma "
"beradi. Kuchli tomoni: obunachi bilan to'g'ridan-to'g'ri, "
"algoritmsiz aloqa — post yozsangiz, deyarli hamma ko'radi. Ta'lim, "
"xizmatlar, ekspert brendlar uchun eng yaxshi uy.\n\n"
"🎵 <b>TikTok</b> — yosh auditoriya va portlovchi organik o'sish. "
"Bitta video million ko'rishga chiqishi mumkin — bepul. Lekin "
"auditoriya \"sovuq\": ko'radi, kuladi, har doim ham sotib olmaydi. "
"Brend tanilishi uchun zo'r, to'g'ridan-to'g'ri savdo uchun "
"kuchsizroq.\n\n"
"📘 <b>Facebook</b> — O'zbekistonda yoshi kattaroq auditoriya va... "
"reklama kabineti. Ko'p biznes Facebook'da sahifa yuritmaydi, lekin "
"Instagram reklamasi aynan Facebook (Meta) kabineti orqali "
"sozlanadi — buni 6-haftada o'rganamiz.\n\n"
"<b>To'g'ri formula: 1 + 1</b>\n\n"
"Kichik biznes uchun oltin qoida: bitta <b>asosiy</b> platforma "
"(kontentning bosh manzili) + bitta <b>yordamchi</b> (asosiyga "
"trafik haydaydi yoki auditoriyani \"qulflaydi\"). Klassik juftlik: "
"Instagram (ko'rsatish, jalb qilish) + Telegram (ushlab qolish, "
"sotish). Reels yangi odamni topadi, Telegram uni doimiy mijozga "
"aylantiradi.\n\n"
"<b>Profil — 3 soniyalik imtihon</b>\n\n"
"Yangi odam profilingizga kirib 3 soniyada uchta savolga javob "
"topishi kerak: bu kim? menga nima beradi? keyin nima qilay? "
"Shundan kelib chiqib: profil rasmi — aniq va sifatli (logotip yoki "
"yuz), bio — kim ekaningiz + foydangiz + harakatga chaqiriq "
"(\"👇 Katalog botda\"), highlight'lar — narxlar, izohlar, yetkazish. "
"Bio'da \"eng yaxshi, sifatli, arzon\" degan quruq so'zlar o'rniga "
"aniqlik: \"3 yildan beri 4000+ ona bizdan oladi\".\n\n"
"💡 <b>Esda qoladigan fikr:</b> platforma tanlash — moda emas, "
"strategiya. Mijozingiz qayerda vaqt o'tkazsa, sizning \"do'koningiz\" "
"o'sha yerda bo'lsin."
                ),
            },
            {
                "id": "3.2",
                "title": "Algoritm qanday o'ylaydi va unga qanday yoqish mumkin",
                "free": False,
                "text": (
"📖 <b>3.2-dars. Algoritm qanday o'ylaydi va unga qanday yoqish "
"mumkin</b>\n\n"
"\"Postlarim hech kimga ko'rinmayapti, algoritm meni bosdi!\" — "
"tanish gapmi? Yaxshi yangilik: algoritm hech kimni \"bosmaydi\". "
"Uning bitta vazifasi bor: <b>odamni platformada uzoqroq ushlab "
"turish</b>. Kontentingiz odamlarni ushlab tursa — algoritm uni "
"o'zi tarqatadi, tekinga. Ushlamasa — hech qanday hiyla yordam "
"bermaydi.\n\n"
"<b>Algoritm nimalarni o'lchaydi (signallar)</b>\n\n"
"1. <b>Ko'rish davomiyligi (watch time)</b> — reels'ni oxirigacha "
"ko'rishdimi? Qayta ko'rishdimi? Eng kuchli signal. Shuning uchun "
"birinchi 1-2 soniya hal qiluvchi: qiziqtirmasa, barmoq keyingisiga "
"o'tadi.\n"
"2. <b>Saqlash (save)</b> — \"keyin kerak bo'ladi\" degani. Foydali "
"kontent belgisi: retseptlar, ro'yxatlar, maslahatlar ko'p "
"saqlanadi.\n"
"3. <b>Ulashish (share)</b> — \"buni do'stim ko'rsin\". Eng qimmat "
"signal: bitta share o'nta laykdan kuchli, chunki sizga yangi "
"auditoriya olib keladi.\n"
"4. <b>Izohlar</b> — suhbat boshlandi degani. Savol bilan tugaydigan "
"postlar izohni ko'paytiradi.\n"
"Layk esa... eng arzon signal. \"Layk yig'ish\"ga emas, saqlash va "
"ulashishga o'ynang.\n\n"
"<b>Amaliy xulosa: kontentni signal ostiga qurish</b>\n\n"
"Post tayyorlashdan oldin bitta savol bering: <i>\"Odam buni nega "
"saqlaydi yoki kimga yuboradi?\"</i> Javob yo'q bo'lsa — post ham "
"kuchsiz. Ishlaydigan formatlar: \"5 ta xato\" ro'yxatlari "
"(saqlashadi), \"buni bilarmidingiz\" faktlari (ulashishadi), "
"munozarali savollar (izoh yozishadi), hayotiy sahna ortlari "
"(oxirigacha ko'rishadi).\n\n"
"<b>Bitta muhim ogohlantirish</b>\n\n"
"Algoritmni \"aldash\" yo'llari (layk chatlari, sotib olingan "
"obunachi, giveaway'dan yig'ilgan olomon) qisqa muddatda son "
"beradi, uzoq muddatda sahifani ko'madi: algoritm kontentingizni "
"qiziqmagan odamlarga ko'rsatib ko'radi, ular o'tkazib yuboradi, "
"tizim \"bu kontent yoqmayapti\" deb xulosa qiladi va tarqatishni "
"to'xtatadi. 10 000 o'lik obunachidan 500 jonli obunachi qimmat.\n\n"
"💡 <b>Esda qoladigan fikr:</b> algoritm — dushman emas, u shunchaki "
"auditoriyaning ko'zgusi. Odamlarga yoqsangiz, algoritmga ham "
"yoqasiz."
                ),
            },
            {
                "id": "3.3",
                "title": "Telegram marketingi: O'zbekistonning oltin kanali",
                "free": False,
                "text": (
"📖 <b>3.3-dars. Telegram marketingi: O'zbekistonning oltin "
"kanali</b>\n\n"
"Dunyoning ko'p mamlakatlarida Telegram — oddiy messenjer. "
"O'zbekistonda esa u to'laqonli media-makon: yangiliklar, do'konlar, "
"ta'lim, ish e'lonlari — hammasi shu yerda. Shuning uchun bizda "
"Telegram marketingi alohida dars: bu bilimsiz o'zbek bozorida SMM "
"to'liq emas.\n\n"
"<b>Uch qurol: kanal, guruh, bot</b>\n\n"
"📣 <b>Kanal</b> — sizning minbaringiz: siz gapirasiz, obunachi "
"o'qiydi. Kontent va ishonch qurish uchun. Instagram'dan farqi: "
"algoritm yo'q, postingiz obunachining lentasiga <b>kafolatlangan</b> "
"yetib boradi.\n"
"👥 <b>Guruh</b> — davra suhbati: mijozlar bir-biri bilan "
"gaplashadi. Jamoa va sodiqlik uchun kuchli, lekin moderatsiya "
"talab qiladi.\n"
"🤖 <b>Bot</b> — avtomatik xodim: buyurtma qabul qiladi, savolga "
"javob beradi, konkurs o'tkazadi, hatto kurs sotadi (hozir siz "
"aynan botda o'qiyapsiz 😉).\n\n"
"Professional sxema uchalasini bog'laydi: kanal ishonch quradi → "
"bot sotadi → guruh ushlab qoladi.\n\n"
"<b>Kanalni nima o'stiradi</b>\n\n"
"Telegram'da reels yo'q — \"tasodifiy\" topib olishmaydi. O'sish "
"manbalari: boshqa platformalardan trafik (Instagram bio, reels'da "
"\"davomi Telegramda\"), o'zaro reklama (auditoriyasi mos kanallar "
"bilan almashinuv), reklama postlari (boshqa kanallarda pullik "
"e'lon — obunachi narxini hisoblab olish: sarf ÷ kelganlar soni), "
"va eng barqarori — <b>ulashiladigan kontent</b>: odam postingizni "
"do'stiga yuborsa, u sizning bepul reklama agentingiz.\n\n"
"<b>Ko'rsatkichlarni qanday o'qish kerak</b>\n\n"
"Kanalda ikkita asosiy raqam bor: ERR (post ko'rishlari ÷ obunachilar) "
"— 30% dan yuqori bo'lsa kanal \"tirik\"; va reaksiya-repostlar "
"dinamikasi. Obunachi soni katta-yu, ko'rishlar past bo'lsa — kanal "
"\"o'lik yuk\" yig'gan, bunday auditoriya reklama beruvchini ham, "
"sizni ham aldaydi.\n\n"
"<b>Hayotiy keys.</b> Bir ta'lim loyihasi Instagram'da 40 ming "
"obunachiga ega edi, lekin har postda algoritm pastga urib, savdo "
"tushib ketardi. Ular oddiy qadam qo'ydi: har reels oxirida \"to'liq "
"darslik Telegram kanalda\" deb takrorladi va bio'ga havola qo'ydi. "
"Olti oyda Telegram'da 8 ming obunachi yig'ildi — va qizig'i: savdoning "
"70% i endi shu 8 mingdan keladi, 40 minglik Instagram'dan emas. "
"Sabab: Telegram'da xabar kafolatlangan yetib boradi, Instagram'da "
"esa algoritmdan omad tilab o'tirasiz.\n\n"
"💡 <b>Esda qoladigan fikr:</b> Instagram — ov maydoni, Telegram — "
"omborxona. Ovni maydonda qiling, boylikni omborda saqlang.\n\n"
"✍️ <b>Haftalik topshiriq:</b> o'z loyihangiz uchun \"1+1\" formulani "
"yozing (asosiy + yordamchi platforma va nima uchun), hamda 3 ta "
"post g'oyasini yozing — har biri bitta algoritm signaliga "
"mo'ljallangan bo'lsin (biri saqlash, biri ulashish, biri izoh "
"uchun). Botga yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "Kichik biznes uchun platformalar bo'yicha to'g'ri strategiya qaysi?",
             "opts": ["Barcha platformalarda birdek faol bo'lish",
                      "Bitta asosiy + bitta yordamchi platformaga fokus",
                      "Faqat TikTok — u eng tez o'sadi",
                      "Platformaning ahamiyati yo'q"],
             "correct": 1},
            {"q": "Algoritmning asosiy maqsadi nima?",
             "opts": ["Kichik sahifalarni bosish",
                      "Reklama sotish",
                      "Odamni platformada uzoqroq ushlab turish",
                      "Eng chiroyli kontentni tanlash"],
             "correct": 2},
            {"q": "Qaysi signal algoritm uchun eng qimmatli hisoblanadi?",
             "opts": ["Layk", "Ulashish (share)", "Profilga kirish", "Obuna bo'lish"],
             "correct": 1},
            {"q": "Telegram kanalning Instagram'dan asosiy farqi nimada?",
             "opts": ["Telegram'da rasm joylash mumkin emas",
                      "Post obunachiga algoritmsiz, kafolatlangan yetib boradi",
                      "Telegram'da reklama qilish taqiqlangan",
                      "Farqi yo'q"],
             "correct": 1},
            {"q": "Kanal \"tirikligi\"ni qaysi ko'rsatkich ko'rsatadi?",
             "opts": ["Obunachilar soni",
                      "Kanal yoshi",
                      "Post ko'rishlarining obunachilarga nisbati (ERR)",
                      "Postlar soni"],
             "correct": 2},
            {"q": "Sotib olingan obunachilar nega zararli?",
             "opts": ["Ular pul so'raydi",
                      "Algoritm kontentni qiziqmaganlarga ko'rsatib, tarqatishni to'xtatadi",
                      "Telegram akkauntni bloklaydi",
                      "Aslida zararli emas, foydali"],
             "correct": 1},
        ],
    },
    4: {
        "title": "Kontent strategiyasi va copywriting",
        "lessons": [
            {
                "id": "4.1",
                "title": "Kontent turlari: nega \"faqat sotuvchi post\" sahifani o'ldiradi",
                "free": False,
                "text": (
"📖 <b>4.1-dars. Kontent turlari: nega \"faqat sotuvchi post\" "
"sahifani o'ldiradi</b>\n\n"
"Tasavvur qiling: bir tanishingiz har uchrashganda faqat bitta gap "
"aytadi — \"mendan sotib ol\". Uchinchi uchrashuvda undan qocha "
"boshlaysiz. Ijtimoiy tarmoqda ham xuddi shunday: faqat \"oling, "
"chegirma, buyurtma bering\" deb turadigan sahifadan odamlar jimgina "
"chiqib ketadi. Professional sahifa esa suhbatdoshga o'xshaydi: goh "
"o'rgatadi, goh kuldiradi, goh isbot ko'rsatadi — va o'rni kelganda "
"sotadi.\n\n"
"<b>To'rt tur kontent va ularning vazifasi</b>\n\n"
"1. 🎓 <b>Ta'limiy</b> — foyda beradi: maslahat, qo'llanma, xatolar "
"tahlili. Vazifasi: \"bu odam o'z ishini biladi\" degan ishonch. "
"Saqlanadi, demak algoritm ham yaxshi ko'radi.\n"
"2. 😄 <b>Ko'ngilochar</b> — his beradi: hazil, sahna orti, hayotiy "
"lavhalar. Vazifasi: brendni \"jonli odam\"ga aylantirish. Eng ko'p "
"ulashiladi.\n"
"3. ⭐ <b>Ijtimoiy isbot</b> — dalil beradi: mijoz izohlari, "
"natijalar (oldin/keyin), raqamlar. Vazifasi: \"boshqalar olgan, "
"demak menga ham bo'ladi\" degan xotirjamlik.\n"
"4. 🛒 <b>Sotuvchi</b> — taklif beradi: mahsulot, narx, aksiya, aniq "
"harakat chaqirig'i. Vazifasi: qaror qildirishning oxirgi turtkisi.\n\n"
"<b>Muvozanat formulasi</b>\n\n"
"Ishlaydigan taxminiy nisbat: 40% ta'limiy, 30% ko'ngilochar, 20% "
"ijtimoiy isbot, 10% sotuvchi. Ha, sotuvchi post — eng kami! "
"Paradoks shundaki, qolgan 90% aynan shu 10% ishlashi uchun zamin "
"tayyorlaydi: o'rgatgan va ishontirgan sahifaning \"oling\" degani "
"buyruq emas, do'st maslahatidek eshitiladi.\n\n"
"<b>Hayotiy keys.</b> Bir stomatologiya klinikasi sahifasida faqat "
"aksiya postlari turardi — oyiga 2-3 murojaat kelardi. SMM'chi "
"strategiyani o'zgartirdi: haftasiga 2 ta ta'limiy post (\"bolada "
"tish qachon olinadi\", \"og'riqsiz davolash qanday ishlaydi\"), 1 ta "
"shifokor hayotidan lavha, 1 ta mijoz natijasi, va faqat 1 ta "
"sotuvchi post. Uch oyda murojaatlar oyiga 40 tadan oshdi — reklama "
"byudjeti o'zgarmagan holda. O'zgargan narsa — ishonch.\n\n"
"💡 <b>Esda qoladigan fikr:</b> kontent — sotuvdan oldingi suhbat. "
"Suhbat qanchalik samimiy bo'lsa, sotuv shunchalik oson bo'ladi."
                ),
            },
            {
                "id": "4.2",
                "title": "Copywriting: birinchi qator hamma narsani hal qiladi",
                "free": False,
                "text": (
"📖 <b>4.2-dars. Copywriting: birinchi qator hamma narsani hal "
"qiladi</b>\n\n"
"Copywriting — chiroyli yozish emas, <b>natija uchun yozish</b>: "
"o'qigan odam biror harakat qilsin. Va bu yo'lda eng katta to'siq "
"shundaki, hech kim sizning matningizni o'qishga majbur emas. "
"O'quvchining barmog'i lentani varaqlayapti — sizda uni to'xtatish "
"uchun 1-2 soniya bor.\n\n"
"<b>Hook — birinchi qator san'ati</b>\n\n"
"Hook (ilgak) — matnning birinchi jumlasi. Uning bitta vazifasi bor: "
"ikkinchi jumlani o'qitish. Ishlaydigan ilgak turlari:\n\n"
"• <b>Savol</b>: \"Reklamaga pul quyib, natija ko'rmayapsizmi?\"\n"
"• <b>Raqam</b>: \"Mijozlarning 70% i birinchi javob tezligiga qarab "
"tanlaydi.\"\n"
"• <b>Qarama-qarshilik</b>: \"Obunachi ko'p — savdo yo'q. Tanishmi?\"\n"
"• <b>Xato</b>: \"Bio'ngizdagi mana bu bitta so'z mijozni "
"qochiryapti.\"\n"
"• <b>Hikoya boshi</b>: \"Kecha bir mijoz yig'lab qo'ng'iroq "
"qildi...\"\n\n"
"Yomon boshlanish: \"Assalomu alaykum, hurmatli obunachilar! Bugun "
"sizlarga...\" — bu birinchi 2 soniyani isrof qilish. Salomlashish "
"yomon emas, lekin u ilgakdan <i>keyin</i> kelsin.\n\n"
"<b>Matn tanasi: soddalik qonuni</b>\n\n"
"Qisqa jumlalar. Har xatboshida bitta fikr. Murakkab so'z o'rniga "
"sodda so'z: \"amalga oshiramiz\" emas — \"qilamiz\". O'zingizni "
"tekshirish usuli: matnni ovoz chiqarib o'qing — tilingiz "
"qoqilgan joyda o'quvchi ham qoqiladi, o'sha jumlani qayta yozing.\n"
"Va \"biz\" emas, \"siz\" tilida yozing: \"Bizda katta assortiment "
"bor\" emas — \"Siz 200 xil modeldan tanlaysiz\".\n\n"
"<b>CTA — harakatga chaqiriq</b>\n\n"
"Matn oxirida o'quvchiga aniq bitta qadam ayting: \"Direktga «narx» "
"deb yozing\", \"Havolani bosing\", \"Do'stingizga yuboring\". "
"Qoidalar: bitta postda bitta CTA (ikkita chaqiriq — ikkilanish "
"demakdir), va chaqiriq qanchalik oson bo'lsa, shunchalik ko'p odam "
"bajaradi (\"saytga kirib ro'yxatdan o'ting\"dan ko'ra \"+ belgisini "
"yozib qoldiring\" yengil).\n\n"
"💡 <b>Esda qoladigan fikr:</b> odamlar matn o'qimaydi — o'zlariga "
"tegishli narsani o'qiydi. Vazifangiz: birinchi qatordayoq \"bu men "
"haqimda\" degan hisni berish."
                ),
            },
            {
                "id": "4.3",
                "title": "Storytelling: hikoya sotadi, ma'lumot esa unutiladi",
                "free": False,
                "text": (
"📖 <b>4.3-dars. Storytelling: hikoya sotadi, ma'lumot esa "
"unutiladi</b>\n\n"
"Ikkita postni solishtiring. Birinchisi: \"Mahsulotimiz sifatli, "
"3 yil kafolat beramiz.\" Ikkinchisi: \"O'tgan hafta bir ota kirib "
"keldi: o'g'liga olgan velosipedning pedali olti oyda singan, boshqa "
"do'kon 'kafolat tugagan' debdi. Bizdan olgan velosipedga 3 yil "
"kafolat yozib berdik — ota ishonmay qayta so'radi.\" Ikkalasi bir "
"narsani aytyapti. Lekin birinchisini 2 soniyada unutasiz, "
"ikkinchisi esa esda qoladi. Farq — hikoyada.\n\n"
"Miya shunday qurilgan: quruq faktni \"ma'lumot\" bo'limiga tashlaydi, "
"hikoyani esa <b>his</b> bilan birga saqlaydi. Odam esa qaror qilganda "
"aynan hisga tayanadi.\n\n"
"<b>Uch qismli hikoya skeleti</b>\n\n"
"Har qanday sotuvchi hikoya uchta ustunda turadi:\n\n"
"1. <b>Muammo</b> — qahramon qiynalayapti (o'quvchi o'zini tanishi "
"kerak: \"e, bu men-ku!\")\n"
"2. <b>Yo'l</b> — qidiruv, urinishlar, burilish nuqtasi (shu yerda "
"mahsulotingiz tabiiy paydo bo'ladi — reklama sifatida emas, yechim "
"sifatida)\n"
"3. <b>Natija</b> — o'zgarish, imkon qadar raqam bilan (\"3 oyda "
"mijozlar 2 barobar oshdi\")\n\n"
"Muhim: qahramon — <b>mijozingiz</b>, siz emas. Siz hikoyada "
"\"yo'lboshlovchi\" rolidasiz. \"Biz qanday zo'rmiz\" hikoyasi emas, "
"\"mijozimiz qanday yutdi (bizning yordamda)\" hikoyasi ishlaydi.\n\n"
"<b>Hikoyani qayerdan olish mumkin?</b>\n\n"
"Hammasi atrofingizda: mijozning birinchi shubhasi va keyingi "
"minnatdorchiligi, ishlab chiqarishdagi kulgili voqea, o'zingizning "
"xatoingiz va undan olgan saboq (halollik ishonchni portlatadi — "
"eng yaxshi ma'noda), \"nega bu ishni boshlaganman\" hikoyasi. "
"Kichik biznesning kuchi aynan shunda: korporatsiyada bunday jonli "
"hikoyalar yo'q, sizda har kuni bor.\n\n"
"<b>Bitta ogohlantirish:</b> hikoya to'qimang. Bo'rttirilgan yoki "
"yolg'on hikoya bir marta fosh bo'lsa, yillab yig'ilgan ishonch bir "
"kunda ketadi. Haqiqiy kichik hikoya to'qilgan katta hikoyadan "
"kuchli.\n\n"
"💡 <b>Esda qoladigan fikr:</b> faktlar ishontiradi, hikoyalar "
"harakatga keltiradi. Ikkalasini birga ishlating: hikoya + raqam = "
"eng kuchli post.\n\n"
"✍️ <b>Haftalik topshiriq:</b> bitta mahsulot yoki xizmatingiz uchun "
"3 xil post yozing: (1) ta'limiy — auditoriyangizga foydali bitta "
"maslahat, (2) hikoya — muammo-yo'l-natija skeletida mijoz voqeasi, "
"(3) sotuvchi — kuchli hook va bitta aniq CTA bilan. Uchalasini "
"botga yuboring — bu haftaning eng muhim mashqi!"
                ),
            },
        ],
        "test": [
            {"q": "Kontentda sotuvchi postlarning tavsiya etilgan ulushi qancha?",
             "opts": ["Taxminan 10%", "Kamida 50%", "100% — sahifa sotish uchun ochilgan", "0% — hech qachon sotmaslik kerak"],
             "correct": 0},
            {"q": "Ta'limiy kontentning asosiy vazifasi nima?",
             "opts": ["Kuldirish", "\"Bu odam ishini biladi\" degan ishonch qurish", "Narxni e'lon qilish", "Obunachini chalg'itish"],
             "correct": 1},
            {"q": "Hook (ilgak)ning vazifasi nima?",
             "opts": ["Postni chiroyli yakunlash", "O'quvchini ikkinchi jumlaga o'tkazish", "Hashtag qo'shish", "Salomlashish"],
             "correct": 1},
            {"q": "CTA bo'yicha to'g'ri qoida qaysi?",
             "opts": ["Bitta postda qancha ko'p chaqiriq bo'lsa, shuncha yaxshi",
                      "CTA umuman kerak emas",
                      "Bitta postda bitta aniq va oson chaqiriq",
                      "CTA faqat sotuvchi postda bo'ladi"],
             "correct": 2},
            {"q": "Sotuvchi hikoyada qahramon kim bo'lishi kerak?",
             "opts": ["Kompaniya rahbari", "Mahsulotning o'zi", "Mijoz (siz — yo'lboshlovchi)", "Raqobatchi"],
             "correct": 2},
            {"q": "Hikoya skeletining to'g'ri ketma-ketligi qaysi?",
             "opts": ["Natija → Narx → Chegirma",
                      "Muammo → Yo'l → Natija",
                      "Salomlashish → Mahsulot → Xayrlashish",
                      "Raqam → Fakt → Xulosa"],
             "correct": 1},
        ],
    },
    5: {
        "title": "Vizual kontent va kontent kalendari",
        "lessons": [
            {
                "id": "5.1",
                "title": "Vizual uslub: dizayner bo'lmasdan professional ko'rinish",
                "free": False,
                "text": (
"📖 <b>5.1-dars. Vizual uslub: dizayner bo'lmasdan professional "
"ko'rinish</b>\n\n"
"Yaxshi yangilik: professional ko'rinish uchun dizayner bo'lish "
"shart emas. Yomon yangilik: <b>qoidasiz</b> ishlash — sahifani "
"havaskorona ko'rsatadigan yagona narsa. Dizayn iste'dod emas, "
"bir necha qoidaga rioya qilish masalasi.\n\n"
"<b>Rang: 60-30-10 qoidasi</b>\n\n"
"Uchta rang tanlang va nisbatni saqlang: 60% asosiy rang (fon, "
"tinch), 30% ikkinchi rang (qo'shimcha), 10% aksent (tugma, muhim "
"so'z — eng yorqini). Rang tanlashda psixologiyani hisobga oling: "
"yashil — ishonch va tabiiylik (siz o'qiyotgan shu kurs kanali ham "
"yashilda 😉), ko'k — professionallik (banklar sevadi), qizil — "
"energiya va shoshilinch (chegirmalar), sariq-to'q sariq — iliqlik "
"(taom, bolalar). Qoida: bir marta tanlang va <b>hamma joyda</b> "
"ishlating — Instagram, Telegram, vizitka, qadoq.\n\n"
"<b>Shrift: ikkitadan oshmasin</b>\n\n"
"Bitta shrift sarlavhaga, bitta matnga — tamom. Uch va undan ortiq "
"shrift bir rasmda — vizual shovqin. Va o'qilishi qiyin \"chiroyli\" "
"shriftlardan qoching: odam 2 soniyada o'qiy olmasa, o'qimaydi.\n\n"
"<b>Kompozitsiya: havo qoidasi</b>\n\n"
"Havaskor dizaynning 1-belgisi: hamma joy to'ldirilgan — matn, "
"stiker, ramka, yulduzcha... Professional dizaynning siri esa "
"<b>bo'sh joy</b> (white space): elementlar \"nafas oladi\", ko'z "
"muhim narsaga o'zi boradi. Shubha qilsangiz — olib tashlang, "
"qo'shmang.\n\n"
"<b>Amaliy vositalar</b>\n\n"
"Canva — tayyor shablonlar, brend rang-shriftni bir marta sozlab "
"olasiz; telefonning o'zi — mahsulot suratlari uchun yetarli, sir "
"yorug'likda: tabiiy kunduzgi yorug'lik har qanday lampadan zo'r, "
"deraza yoniga oling; bitta fon uslubi — mahsulot suratlarini bir "
"xil fonda oling, lenta darrov \"jamlangan\" ko'rinadi.\n\n"
"<b>Hayotiy keys.</b> Uy shirinliklari sotadigan bir opa suratlarni "
"oshxonada, har xil fonda olardi — sahifa tartibsiz ko'rinardi. "
"Bitta o'zgarish: deraza yonida bitta yog'och taxta + oq mato fon. "
"Hamma surat shu joyda. Ikki haftada sahifa \"do'kon\" ko'rinishiga "
"kirdi, direktda \"narxi qancha\" so'rovlari sezilarli oshdi — "
"mahsulot o'zgarmadi, taqdimot o'zgardi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> vizual izchillik — mahorat emas, "
"intizom. 3 rang, 2 shrift, 1 uslub — va sahifangiz brendga "
"o'xshaydi."
                ),
            },
            {
                "id": "5.2",
                "title": "Kontent kalendari: ilhom kutmaydigan tizim",
                "free": False,
                "text": (
"📖 <b>5.2-dars. Kontent kalendari: ilhom kutmaydigan tizim</b>\n\n"
"SMM'dagi eng katta yolg'on: \"ilhom kelganda post qilaman\". Ilhom "
"haftada bir keladi, algoritm esa har kuni ovqat so'raydi. "
"Professional va havaskorni ajratadigan narsa iste'dod emas — "
"<b>tizim</b>. Tizimning nomi: kontent kalendari.\n\n"
"<b>Kontent ustunlari (content pillars)</b>\n\n"
"Kalendar tuzishdan oldin 3-5 ta doimiy mavzu ustunini belgilang. "
"Masalan, bolalar kiyimi do'koni uchun: (1) mahsulot va yangi "
"kelganlar, (2) onalarga foydali maslahatlar, (3) mijozlar "
"natijalari va izohlar, (4) sahna orti va jamoa. Ustunlar nima "
"beradi? Har post \"nima yozsam ekan\" degan azobdan emas, tayyor "
"katakdan boshlanadi. 4.1-darsdagi kontent turlari bilan "
"birlashtirsangiz — mashina tayyor.\n\n"
"<b>Haftalik jadval namunasi</b>\n\n"
"Du — ta'limiy post (hafta foydali boshlanadi)\n"
"Se — mahsulot / yangilik\n"
"Chor — hikoya yoki sahna orti\n"
"Pay — mijoz izohi / natija\n"
"Ju — sotuvchi post (hafta oxiri — xarid kayfiyati)\n"
"Shan — yengil / ko'ngilochar kontent\n\n"
"Bu qolip emas, boshlang'ich nuqta — o'z auditoriyangizga qarab "
"o'zgartirasiz. Muhimi: jadval <b>oldindan</b> to'ldirilgan bo'lsin.\n\n"
"<b>Partiyalab tayyorlash (batching)</b>\n\n"
"Eng samarali usul: haftada bir kun 2-3 soat ajratib, butun hafta "
"kontentini birdaniga tayyorlash — suratlar bir seansda, matnlar "
"ketma-ket. Har kuni \"endi nima qilay\" deb o'tirishdan 3-4 barobar "
"tez. Qolgan kunlar faqat joylaysiz va izohlarga javob berasiz.\n\n"
"<b>Qachon joylash kerak?</b>\n\n"
"Universal javob yo'q, lekin O'zbekistonda ishlaydigan oraliqlar: "
"ertalab 8-10 (ishga borishda), tushlik 13-14, kechqurun 20-22 "
"(eng faol vaqt). Aniq javobni statistikangiz beradi: bir oy turli "
"vaqtda joylab, qaysi soat ko'proq ko'rish berganini yozib boring. "
"<b>Muntazamlik vaqtdan muhim</b>: har kuni 21:00da chiqadigan post "
"tasodifiy \"zo'r vaqt\"dagi postdan kuchli — auditoriya sizni "
"kutishga o'rganadi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> kontent kalendari ijodni "
"o'ldirmaydi — u ijodga vaqt bo'shatadi. Tizim oddiy kunlarni "
"ushlab turadi, ilhom esa ustiga bonus bo'lib keladi."
                ),
            },
            {
                "id": "5.3",
                "title": "UGC: mijozlaringiz — eng ishonchli marketologlaringiz",
                "free": False,
                "text": (
"📖 <b>5.3-dars. UGC: mijozlaringiz — eng ishonchli "
"marketologlaringiz</b>\n\n"
"Savol: qaysi gapga ko'proq ishonasiz — do'kon \"mahsulotimiz zo'r\" "
"desami, yoki tanishingiz \"shu yerdan oldim, juda yoqdi\" desami? "
"Javob aniq. UGC (User Generated Content) — mijozlar yaratgan "
"kontent: ularning suratlari, videolari, izohlari, stories'lari. "
"Bu reklamaning eng ishonchli turi, chunki uni <b>manfaatdor "
"bo'lmagan odam</b> aytyapti.\n\n"
"<b>Nega UGC bunchalik kuchli</b>\n\n"
"Birinchidan, ishonch: odamlar reklamaga emas, odamlarga ishonadi. "
"Ikkinchidan, tekinlik: mijoz kontentni o'zi yaratadi. Uchinchidan, "
"ko'paytiruvchi effekt: mijoz stories'ida sizni belgilasa, uning "
"barcha obunachilari — sizning bepul auditoriyangiz. To'rtinchidan, "
"kontent zaxirasi: 20 ta mijoz surati — 20 ta tayyor post.\n\n"
"<b>Mijozni kontent yaratishga qanday undash mumkin</b>\n\n"
"Hech kim o'z-o'zidan yozmaydi — sharoit yaratish kerak:\n\n"
"1. <b>So'rang</b> — eng oddiy va eng unutiladigan usul. Buyurtma "
"topshirilgach: \"Yoqsa, stories'da belgilab qo'ysangiz, xursand "
"bo'lamiz!\" So'ragan oladi.\n"
"2. <b>Rag'batlantiring</b> — \"belgilagan mijozlarga keyingi "
"xaridga 10% chegirma\" yoki oylik o'yin: belgilaganlar orasidan "
"sovg'a.\n"
"3. <b>Sharoit yarating</b> — chiroyli qadoq odamning o'zini "
"suratga tortadi; qadoq ichiga \"bizni belgilang: @...\" yozuvli "
"kichik kartochka soling.\n"
"4. <b>E'zozlang</b> — mijoz kontentini o'z sahifangizda repost "
"qiling (ruxsati bilan) va minnatdorchilik bildiring. Boshqalar "
"buni ko'rib \"meni ham chiqarishar ekan\" deb harakat qiladi.\n\n"
"<b>Hayotiy keys.</b> Milliy taomlar yetkazadigan kichik oshxona "
"har buyurtmaga qo'lda yozilgan bitta jumla qo'shdi: \"Yoqdimi? "
"Bizni stories'da belgilang — keyingi buyurtmada shirinlik bizdan!\" "
"Natija: haftasiga o'rtacha 15-20 ta belgilash, va yangi mijozlarning "
"\"sizni falonchining storiesida ko'rdim\" deb kelishi odatiy holga "
"aylandi. Reklama xarajati: qo'lda yozilgan kartochka va shirinlik.\n\n"
"⚠️ Muhim: soxta izoh sotib olmang va o'zingizga o'zingiz izoh "
"yozmang. Fosh bo'lishi oson, narxi — butun ishonch.\n\n"
"💡 <b>Esda qoladigan fikr:</b> eng zo'r reklama — mijozning "
"tabassumi, kadrda. Sizning vazifangiz — o'sha kadr uchun sabab va "
"sharoit yaratish.\n\n"
"✍️ <b>Haftalik topshiriq:</b> (1) brendingiz uchun 3 rang + 2 "
"shrift tanlang va nima uchunligini yozing, (2) o'z ustunlaringiz "
"asosida 2 haftalik kontent kalendari tuzing (kamida 10 post "
"g'oyasi), (3) mijozni UGC'ga undaydigan bitta mexanika o'ylab "
"toping. Hammasini botga yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "60-30-10 qoidasi nimani anglatadi?",
             "opts": ["Byudjet taqsimoti",
                      "Ranglar nisbati: asosiy, ikkinchi, aksent",
                      "Post chiqarish vaqtlari",
                      "Chegirma foizlari"],
             "correct": 1},
            {"q": "Bitta dizaynda nechta shrift ishlatish tavsiya etiladi?",
             "opts": ["Ko'pi bilan 2 ta", "Kamida 4 ta", "Faqat 1 ta, hamma joyda", "Cheklov yo'q"],
             "correct": 0},
            {"q": "Kontent ustunlari (content pillars) nima beradi?",
             "opts": ["Ko'proq obunachi",
                      "Har post uchun tayyor mavzu yo'nalishi — \"nima yozsam\" azobidan qutqaradi",
                      "Algoritmda ustunlik",
                      "Bepul reklama"],
             "correct": 1},
            {"q": "Post joylash vaqti bo'yicha eng to'g'ri tamoyil qaysi?",
             "opts": ["Faqat yarim tunda joylash kerak",
                      "Vaqtning umuman ahamiyati yo'q",
                      "Muntazamlik aniq vaqtdan muhimroq, aniq vaqtni esa statistika aytadi",
                      "Har soatda bittadan joylash kerak"],
             "correct": 2},
            {"q": "UGC nima?",
             "opts": ["Pullik reklama turi",
                      "Mijozlar yaratgan kontent (surat, video, izoh)",
                      "Google'ning reklama xizmati",
                      "Dizayn dasturi"],
             "correct": 1},
            {"q": "Nega soxta izoh sotib olish xavfli?",
             "opts": ["Qimmat turadi",
                      "Fosh bo'lsa, yig'ilgan butun ishonch ketadi",
                      "Algoritm darhol bloklaydi",
                      "Aslida xavfli emas"],
             "correct": 1},
        ],
    },
    6: {"title": "Meta Ads: pullik reklama", "lessons": [], "test": []},
    7: {"title": "Google Ads asoslari", "lessons": [], "test": []},
    8: {"title": "Analitika va metrikalar", "lessons": [], "test": []},
    9: {"title": "Funnel, email va influencer marketing", "lessons": [], "test": []},
    10: {"title": "Strategiya va yakuniy loyiha", "lessons": [], "test": []},
}
