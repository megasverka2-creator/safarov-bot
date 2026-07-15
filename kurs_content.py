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
    6: {
        "title": "Meta Ads: pullik reklama",
        "lessons": [
            {
                "id": "6.1",
                "title": "Meta Ads: \"Boost\" tugmasi nega pulingizni yeydi",
                "free": False,
                "text": (
"📖 <b>6.1-dars. Meta Ads: \"Boost\" tugmasi nega pulingizni "
"yeydi</b>\n\n"
"Ko'pchilikning pullik reklama bilan tanishuvi bir xil boshlanadi: "
"post ostidagi ko'k \"Boost / Ko'tarish\" tugmasi bosiladi, 20-30 "
"dollar ketadi, laykllar keladi... savdo kelmaydi. Xulosa: \"reklama "
"ishlamaydi\". Aslida ishlamagan narsa reklama emas — <b>vosita "
"noto'g'ri tanlangan</b>. Boost — soddalashtirilgan rejim: Meta "
"o'zi \"faollik\" (layk, reaksiya) uchun optimallaydi, siz esa "
"savdoni xohlagansiz. Professional ish Ads Manager kabinetida "
"qilinadi — bu dars o'sha kabinetning xaritasi.\n\n"
"<b>Uch qavatli tuzilma</b>\n\n"
"Meta reklamasi uch qavatdan iborat, har qavatda bitta savolga "
"javob berasiz:\n\n"
"1. 🎯 <b>Kampaniya</b> — NIMA uchun? Bu yerda maqsad (objective) "
"tanlanadi: xabardorlik (ko'proq odam ko'rsin), trafik (havolaga "
"o'tsin), faollik, xabarlar (Direct/Telegram'ga yozsin), lidlar, "
"savdo. Meta aynan tanlangan maqsadga mos odamlarni qidiradi — "
"shuning uchun maqsadni xato tanlash = pulni xato joyga yuborish.\n"
"2. 👥 <b>Reklama to'plami (Ad set)</b> — KIMGA va QANCHAGA? "
"Auditoriya, joylashuv (Instagram lenta, stories, reels), byudjet "
"va muddat shu qavatda.\n"
"3. 🖼 <b>Reklamaning o'zi (Ad)</b> — NIMA ko'rsatamiz? Surat yoki "
"video, matn, sarlavha va tugma (CTA).\n\n"
"<b>Qaysi maqsadni tanlash kerak?</b>\n\n"
"Oddiy yo'riq: Direct'da sotadigan kichik biznes uchun — "
"\"Xabarlar\" maqsadi (odam to'g'ridan-to'g'ri yozadi, suhbatda "
"sotasiz). Saytga yoki botga olib borish kerak bo'lsa — \"Trafik\". "
"\"Xabardorlik\" faqat katta byudjetli brendlarga mos. Boshlovchining "
"eng ko'p xatosi: \"Faollik\" tanlab, layk yig'ib, savdo kutish.\n\n"
"<b>Hayotiy keys.</b> Poyabzal do'koni boost orqali oyiga 100$ "
"sarflardi: minglab layk, oyiga 3-4 savdo. Ads Manager'ga o'tib "
"\"Xabarlar\" maqsadini tanladi, o'sha 100$ bilan: laykllar kam, "
"lekin Direct'ga oyiga 90-100 ta \"narxi qancha?\" so'rovi keldi, "
"ulardan 25-30 tasi xaridga aylandi. Bir xil pul, bir xil mahsulot — "
"faqat maqsad to'g'rilandi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> Meta sizga so'raganingizni beradi. "
"Layk so'rasangiz — layk beradi, mijoz so'rasangiz — mijoz. "
"To'g'ri so'rashni o'rganish — shu haftaning maqsadi."
                ),
            },
            {
                "id": "6.2",
                "title": "Auditoriya sozlash: to'g'ri odamga to'g'ri e'lon",
                "free": False,
                "text": (
"📖 <b>6.2-dars. Auditoriya sozlash: to'g'ri odamga to'g'ri "
"e'lon</b>\n\n"
"2-haftada buyer persona yaratgan edik — endi o'sha portretni "
"reklama kabinetiga \"ko'chirish\" vaqti keldi. Auditoriya "
"sozlamalari — reklama muvaffaqiyatining kamida yarmi: eng zo'r "
"e'lon ham noto'g'ri odamga ko'rsatilsa, pul kuyadi.\n\n"
"<b>Uch xil auditoriya turi</b>\n\n"
"1. ❄️ <b>Sovuq — qiziqishlar bo'yicha</b>. Geografiya (shahar, "
"hatto radius), yosh, jins + qiziqishlar (Meta odamlarning xatti-"
"harakatidan biladi: \"bolalar mahsulotlariga qiziqadi\", \"onlayn "
"xarid qiladi\"). Sizni hali tanimaydigan yangi odamlar. Maslahat: "
"qiziqishlarni haddan tashqari toraytirib yubormang — Meta'ning "
"algoritmi keng auditoriya ichidan o'zi topishga ancha usta bo'lib "
"qolgan; asosiy ishni yosh-geo-jins va kuchli e'lon qilsin.\n"
"2. 🔥 <b>Issiq — retargeting</b>. Sizni allaqachon biladiganlar: "
"sahifangizga kirganlar, videoni ko'rganlar, direct'ga yozganlar. "
"Bu auditoriya eng arzon va eng ko'p sotib oladi — \"ko'rgan, lekin "
"hali olmagan\" odamga eslatish savdoning eng oson turi. Ko'p kichik "
"biznes shu bepul imkoniyatni umuman ishlatmaydi.\n"
"3. 👯 <b>Lookalike — o'xshashlar</b>. Meta'ga mijozlaringiz "
"ro'yxatini (yoki sahifa faollarini) berasiz, u \"shularga o'xshagan "
"yana kimlar bor\" deb topib beradi. Mijoz bazangiz 500-1000 dan "
"oshganda juda kuchli ishlaydi.\n\n"
"<b>To'g'ri ketma-ketlik</b>\n\n"
"Boshlovchi strategiyasi: avval sovuq auditoriyaga kichik byudjet "
"bilan chiqasiz → sahifa va video ko'ruvchilar yig'iladi → ularga "
"retargeting yoqasiz (\"hali ham o'ylayapsizmi? mana chegirma\") → "
"vaqt o'tib mijozlar bazasidan lookalike qurasiz. Reklama tizimi "
"bir martalik otishma emas, aylanuvchi g'ildirak.\n\n"
"<b>Bitta amaliy sir: e'lon auditoriyaga gapirsin</b>\n\n"
"Auditoriyani ajratdingizmi — e'lonni ham ajrating. Onalarga "
"boshqa surat-matn, yigitlarga boshqa. \"25-45 hamma\"ga bitta "
"e'lon — hech kimga tegmaydigan o'rtacha gap. 2-haftadagi qoida "
"shu yerda pulga aylanadi: aniq odamga aniq gap.\n\n"
"💡 <b>Esda qoladigan fikr:</b> sovuq auditoriya — tanishuv, "
"retargeting — eslatish, lookalike — ko'paytirish. Uchalasi birga "
"ishlaganda reklama tizimga aylanadi."
                ),
            },
            {
                "id": "6.3",
                "title": "Byudjet va raqamlar: reklama qachon o'zini oqlaydi",
                "free": False,
                "text": (
"📖 <b>6.3-dars. Byudjet va raqamlar: reklama qachon o'zini "
"oqlaydi</b>\n\n"
"\"Reklamaga qancha pul kerak?\" — noto'g'ri savol. To'g'ri savol: "
"\"bitta mijoz menga qanchaga tushyapti va u qancha foyda "
"keltiryapti?\" Shu ikki raqamni bilgan odam reklamani xarajat deb "
"emas, <b>investitsiya</b> deb boshqaradi.\n\n"
"<b>Uchta asosiy o'lchov</b>\n\n"
"• <b>CPM</b> — 1000 ko'rsatish narxi. Auditoriya qanchalik "
"raqobatli ekanini ko'rsatadi.\n"
"• <b>CPC</b> — bitta bosish narxi. E'lon qanchalik "
"qiziqtirayotganini ko'rsatadi: CPC baland bo'lsa, ko'pincha aybdor "
"auditoriya emas — zerikarli e'lon.\n"
"• <b>CPA</b> — bitta natija narxi (bitta xabar, bitta buyurtma). "
"Eng muhim raqam: qolgan hammasi shunga xizmat qiladi.\n\n"
"Oddiy misol: 100 000 so'm sarfladingiz, 20 ta Direct so'rovi "
"keldi → bitta so'rov 5 000 so'm. Shu 20 tadan 5 tasi sotib oldi → "
"bitta mijoz (CPA) 20 000 so'm. Agar bitta savdodan foydangiz "
"60 000 so'm bo'lsa — har 20 ming 60 ming bo'lib qaytyapti, "
"reklamani kuchaytirish kerak. Foyda 15 000 bo'lsa — reklama zarar, "
"to'xtatib sabab qidirish kerak.\n\n"
"<b>Kichik byudjet bilan qanday boshlash kerak</b>\n\n"
"Kuniga 3-5$ dan boshlash mumkin — lekin bitta shart bilan: "
"<b>sabr</b>. Meta algoritmi dastlab \"o'rganadi\" (kimga ko'rsatsa "
"yaxshi ishlashini sinaydi) — birinchi 2-3 kun natija qimmat "
"ko'rinishi normal. Eng ko'p uchraydigan xato: har kuni sozlamani "
"o'zgartirish yoki 2-kuni o'chirib qo'yish — bu algoritm o'qishini "
"har safar noldan boshlatadi.\n\n"
"<b>Test qilish madaniyati</b>\n\n"
"Professional hech qachon \"bitta eng zo'r e'lon\"ga pul tikmaydi. "
"U 2-3 variant tayyorlaydi (boshqa surat, boshqa hook), kichik "
"byudjetda yonma-yon sinaydi, 3-4 kundan keyin raqamlarga qaraydi "
"va g'olibga asosiy byudjetni beradi. Bitta o'zgaruvchini sinang: "
"ikki e'lon faqat surati bilan farq qilsin — shunda nima ishlaganini "
"aniq bilasiz.\n\n"
"⚠️ <b>Ogohlantirish:</b> \"kabinetni sozlab beraman, 100% natija "
"kafolat\" deguvchilardan ehtiyot bo'ling. Reklamada halol mutaxassis "
"jarayonni kafolatlaydi (to'g'ri sozlash, test, hisobot), natijani "
"esa bozor hal qiladi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> reklamani his emas, raqam "
"boshqarsin. CPA va foydani yonma-yon qo'ying — qolgan hamma qaror "
"o'zi chiqadi.\n\n"
"✍️ <b>Haftalik topshiriq:</b> o'z loyihangiz uchun qog'ozda "
"reklama rejasini tuzing: (1) maqsad (objective) va nima uchun "
"aynan u, (2) sovuq auditoriya tavsifi (geo, yosh, qiziqishlar), "
"(3) kunlik byudjet va \"bitta mijoz menga necha so'mgacha tushsa "
"foydali\" hisobingiz. Botga yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "\"Boost\" tugmasi bilan Ads Manager'ning asosiy farqi nimada?",
             "opts": ["Farqi yo'q, ikkalasi bir xil",
                      "Boost soddalashtirilgan bo'lib, maqsadni to'liq boshqarish imkonini bermaydi",
                      "Ads Manager faqat katta kompaniyalar uchun",
                      "Boost bepul ishlaydi"],
             "correct": 1},
            {"q": "Meta reklamasining uch qavati qaysi tartibda?",
             "opts": ["Ad → Kampaniya → Ad set",
                      "Kampaniya (maqsad) → Ad set (auditoriya, byudjet) → Ad (e'lon)",
                      "Byudjet → Surat → Matn",
                      "Auditoriya → Maqsad → Natija"],
             "correct": 1},
            {"q": "Direct orqali sotadigan kichik do'kon uchun eng mos maqsad?",
             "opts": ["Xabardorlik", "Faollik (layk uchun)", "Xabarlar", "App o'rnatish"],
             "correct": 2},
            {"q": "Retargeting kimlarga ko'rsatiladi?",
             "opts": ["Umuman yangi odamlarga",
                      "Sizni allaqachon bilganlarga (sahifaga kirgan, video ko'rgan)",
                      "Faqat raqobatchi mijozlariga",
                      "Tasodifiy auditoriyaga"],
             "correct": 1},
            {"q": "CPA nima?",
             "opts": ["1000 ko'rsatish narxi",
                      "Bitta bosish narxi",
                      "Bitta natija (xabar/buyurtma) narxi",
                      "Kunlik byudjet"],
             "correct": 2},
            {"q": "Reklama yoqilgach 2-kuni natija qimmat ko'rinsa, nima qilish kerak?",
             "opts": ["Darhol o'chirish",
                      "Har kuni sozlamalarni o'zgartirish",
                      "Algoritm o'rganishiga 3-4 kun vaqt berish, keyin raqamlarga qarab qaror qilish",
                      "Byudjetni 10 barobar oshirish"],
             "correct": 2},
        ],
    },
    7: {
        "title": "Google Ads asoslari",
        "lessons": [
            {
                "id": "7.1",
                "title": "Google vs Meta: talab yaratish va talabni tutish",
                "free": False,
                "text": (
"📖 <b>7.1-dars. Google vs Meta: talab yaratish va talabni "
"tutish</b>\n\n"
"O'tgan hafta Meta'ni o'rgandik, endi bir savol: ikkalasining tub "
"farqi nimada? Javob bitta so'zda — <b>niyat</b>.\n\n"
"Instagram'da odam dam olyapti: reklamangiz uni <i>to'xtatib</i>, "
"qiziqtirishi kerak. Siz talab <b>yaratasiz</b> — odam konditsioner "
"haqida o'ylamayotgan edi, e'loningiz o'ylatdi.\n"
"Google'da esa odam <b>o'zi qidiryapti</b>: \"konditsioner o'rnatish "
"Toshkent narxi\". U allaqachon xohlayapti — sizning vazifangiz "
"shunchaki o'sha paytda ro'parasida bo'lish. Siz tayyor talabni "
"<b>tutasiz</b>. Shu sababli Google'dan kelgan mijoz odatda "
"\"pishganroq\" bo'ladi.\n\n"
"<b>Google Ads turlari</b>\n\n"
"1. 🔍 <b>Search (qidiruv)</b> — qidiruv natijalarining tepasidagi "
"matnli e'lonlar. Eng \"issiq\" format: odam muammosini o'zi yozdi. "
"Xizmatlar (usta, klinika, yuridik, ta'lim) uchun oltin.\n"
"2. 🖼 <b>Display</b> — saytlardagi banner tarmog'i. Arzon va keng, "
"lekin niyat past: brendni eslatish va retargeting uchun yaxshi, "
"to'g'ridan-to'g'ri savdo uchun kuchsiz.\n"
"3. ▶️ <b>YouTube</b> — video reklama. O'zbekistonda YouTube "
"auditoriyasi juda katta; brend tanitish va murakkab mahsulotni "
"tushuntirish uchun kuchli.\n"
"4. 🛍 <b>Shopping</b> — mahsulot kartochkalari (rasm + narx "
"qidiruvda). Internet-do'konlar uchun, saytdagi tovar katalogiga "
"ulanadi.\n\n"
"<b>Qaysi biznesga qaysi biri?</b>\n\n"
"Oddiy test savoli: <i>odamlar sizning mahsulotingizni Google'da "
"qidiradimi?</i> \"Santexnik chaqirish\", \"ingliz tili kurslari\", "
"\"stomatolog narxlari\" — ha, qidiradi: Search birinchi tanlov. "
"\"Qo'lda tikilgan noyob sumka\" — yo'q, buni hech kim qidirmaydi, "
"buni ko'rsatish kerak: Instagram kuchliroq. Ko'p biznes uchun "
"to'g'ri javob — ikkalasi birga: Meta talab uyg'otadi, Google "
"pishgan talabni yig'ib oladi.\n\n"
"<b>Hayotiy keys.</b> Konditsioner o'rnatish xizmati Instagram'da "
"reklama berardi — qishda natija nolga yaqin edi (hech kim "
"o'ylamaydi ham). Google Search'ga o'tdi: reklama faqat "
"\"konditsioner o'rnatish\", \"konditsioner quvvati hisoblash\" kabi "
"so'rovlarga chiqadigan bo'ldi. Iyun kelganda so'rovlar portladi va "
"har bir reklama so'mi aynan izlayotgan odamga ketdi — mavsumda "
"ustalar navbatga yozadigan bo'ldi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> Meta — ehtiyoj uyg'otadi, Google — "
"ehtiyojga javob beradi. Qaysi biri sizniki ekanini mijozingizning "
"qidiruv odati aytadi."
                ),
            },
            {
                "id": "7.2",
                "title": "Kalit so'zlar: mijozning boshidagi jumlani topish",
                "free": False,
                "text": (
"📖 <b>7.2-dars. Kalit so'zlar: mijozning boshidagi jumlani "
"topish</b>\n\n"
"Search reklamasining yuragi — kalit so'zlar: odamlar Google'ga "
"yozadigan so'rovlar. Bu yerda san'at bitta narsada: mijozning "
"boshiga kirib, u <b>aynan qanday yozishini</b> topish. Siz "
"\"ortopedik matras\" deysiz, mijoz \"beli og'riganga qattiq matras\" "
"deb yozadi. Kim mijoz tilida o'ylasa — o'sha yutadi.\n\n"
"<b>Niyat (intent) bo'yicha uch daraja</b>\n\n"
"1. 🧊 <b>Ma'lumot niyati</b>: \"matras qanday tanlanadi\" — hali "
"o'rganyapti, sotib olishga uzoq. Reklamaga arzimaydi (lekin blog/"
"kontent uchun zo'r mavzu).\n"
"2. 🌡 <b>Taqqoslash niyati</b>: \"qaysi matras yaxshi ortopedik yoki "
"lateks\" — tanlayapti. O'rtacha issiq.\n"
"3. 🔥 <b>Xarid niyati</b>: \"matras narxi Toshkent\", \"matras "
"buyurtma berish\", \"arzon matras yetkazib berish\" — hamyon "
"qo'lida! Byudjetning asosiy qismi shu guruhga.\n\n"
"Belgilar: \"narxi\", \"buyurtma\", \"sotib olish\", \"yetkazib "
"berish\", \"yaqin atrofda\", shahar nomi — bularning bari xarid "
"niyatining bayroqlari.\n\n"
"<b>Moslik turlari (match types)</b>\n\n"
"Google'ga so'zni qanday \"tushunish\"ni aytish mumkin:\n"
"• <b>Keng (broad)</b> — Google o'zi \"yaqin\" deb bilgan hamma "
"so'rovga chiqaradi. Xavfli: byudjet keraksiz so'rovlarga oqishi "
"mumkin.\n"
"• <b>Ibora (phrase)</b> — so'rov ichida sizning iborangiz bo'lsa "
"chiqadi. Oltin o'rtalik, boshlovchiga tavsiya.\n"
"• <b>Aniq (exact)</b> — deyarli aynan shu so'rovga. Eng nazoratli, "
"eng tor.\n\n"
"<b>Minus-so'zlar — ko'rinmas qahramon</b>\n\n"
"Byudjetni tejaydigan eng kuchli vosita: qaysi so'rovlarga "
"<b>chiqmaslikni</b> aytish. Pullik kurs sotsangiz: \"bepul\", "
"\"skachat\", \"torrent\" — minusga. Yangi mahsulot sotsangiz: "
"\"b/u\", \"ishlatilgan\", \"remont\" — minusga. Har hafta \"qaysi "
"so'rovlarga chiqdim\" hisobotini ochib, begona so'rovlarni minusga "
"qo'shib borish — professional odat.\n\n"
"💡 <b>Esda qoladigan fikr:</b> kalit so'z tanlash — texnika emas, "
"empatiya: mijoz muammosini u yozadigan so'zlar bilan yozing. "
"Qolganini moslik turi va minus-so'zlar tartibga soladi."
                ),
            },
            {
                "id": "7.3",
                "title": "Landing page: reklama olib kelgan mehmonni kutib olish",
                "free": False,
                "text": (
"📖 <b>7.3-dars. Landing page: reklama olib kelgan mehmonni kutib "
"olish</b>\n\n"
"Reklama sozlash — ishning yarmi. Odam e'loningizni bosdi... endi "
"qayerga tushadi? Ko'p byudjetlar aynan shu nuqtada nobud bo'ladi: "
"reklama zo'r, lekin bosgan odam bosh sahifaga tushib, qidirganini "
"topolmay chiqib ketadi. Har chiqib ketgan odam — to'langan, lekin "
"foydasiz bosish.\n\n"
"<b>Message match — va'da mosligi qonuni</b>\n\n"
"Oltin qoida: <b>e'londagi va'da sahifada davom etsin</b>. E'lon "
"\"Ingliz tili: 3 oyda gapirasiz — 40% chegirma\" desa, ochilgan "
"sahifada birinchi ko'ringan narsa xuddi shu bo'lishi kerak — kurs "
"nomi va o'sha chegirma. Odam ongida uzluksizlik hosil bo'ladi: "
"\"to'g'ri joyga keldim\". E'lon boshqa, sahifa boshqa gapirsa — "
"ishonch bir soniyada sinadi.\n\n"
"<b>Yaxshi landing sahifaning skeleti</b>\n\n"
"1. <b>Sarlavha</b> — asosiy va'da (e'lon bilan mos)\n"
"2. <b>Foyda</b> — mijoz nimaga ega bo'ladi (xususiyat emas: "
"\"8 GB xotira\" emas, \"1000 ta surat sig'adi\")\n"
"3. <b>Ishonch</b> — izohlar, natijalar, raqamlar, kafolat\n"
"4. <b>Bitta aniq CTA</b> — \"Ariza qoldirish\", \"Telegram'da "
"yozish\". 4.2-darsdagi qoida shu yerda ham: bitta sahifa — bitta "
"asosiy harakat. Beshta tugma — nol qaror.\n\n"
"Va shakl (forma) qanchalik qisqa bo'lsa, shuncha ko'p ariza: ism + "
"telefon yetarli. Har qo'shimcha maydon arizalarning bir qismini "
"\"yeb qo'yadi\".\n\n"
"<b>Sayt shartmi? Yo'q.</b>\n\n"
"O'zbekiston voqeligida landing rolini ko'pincha boshqa narsalar "
"o'ynaydi: to'g'ridan-to'g'ri Telegram bot (reklama → bot → suhbat "
"→ savdo), Instagram profil (shuning uchun 3.1-darsdagi \"3 soniya "
"imtihoni\" muhim edi) yoki bitta sahifali oddiy sayt. Qoida "
"o'zgarmaydi: qayerga olib borsangiz ham, o'sha joy e'londagi "
"va'dani davom ettirsin va bitta aniq keyingi qadam taklif "
"qilsin.\n\n"
"<b>Tezlik — ko'rinmas konversiya o'g'risi</b>\n\n"
"Sahifa 3-4 soniyada ochilmasa, odamlarning katta qismi kutmaydi — "
"siz esa bosish uchun to'lab bo'lgansiz. Og'ir rasmlar va keraksiz "
"skriptlardan tozalang; telefonda tekshiring, chunki trafikning "
"mutlaq ko'pchiligi telefondan keladi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> reklama — eshik taqillatish, landing "
"— eshikni ochib kutib olish. Mehmonni ostonada yo'qotmang.\n\n"
"✍️ <b>Haftalik topshiriq:</b> o'z loyihangiz uchun (1) 10 ta kalit "
"so'z yozing va ularni niyat bo'yicha uch guruhga ajrating "
"(ma'lumot / taqqoslash / xarid), (2) kamida 5 ta minus-so'z "
"toping, (3) mijoz reklamadan qayerga tushishini va u yerda qanday "
"bitta CTA kutishini yozing. Botga yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "Google Search va Meta reklamasining tub farqi nimada?",
             "opts": ["Google arzonroq",
                      "Google'da odam o'zi qidiradi (tayyor niyat), Meta'da talab yaratiladi",
                      "Meta faqat videolar uchun",
                      "Farqi yo'q"],
             "correct": 1},
            {"q": "\"Matras narxi Toshkent yetkazib berish\" — bu qaysi niyat darajasi?",
             "opts": ["Ma'lumot niyati", "Taqqoslash niyati", "Xarid niyati", "Niyatsiz so'rov"],
             "correct": 2},
            {"q": "Boshlovchiga qaysi moslik turi tavsiya etiladi?",
             "opts": ["Keng (broad)", "Ibora (phrase)", "Faqat aniq (exact)", "Hammasi aralash"],
             "correct": 1},
            {"q": "Minus-so'zlar nima uchun kerak?",
             "opts": ["Raqobatchini bloklash uchun",
                      "Keraksiz so'rovlarga chiqmaslik va byudjetni tejash uchun",
                      "E'lonni chiroyli qilish uchun",
                      "Google talab qilgani uchun"],
             "correct": 1},
            {"q": "Message match nima?",
             "opts": ["Ikki e'lonning bir xilligi",
                      "E'londagi va'daning ochilgan sahifada davom etishi",
                      "Xabarlarga tez javob berish",
                      "Google va Meta'ni birga ishlatish"],
             "correct": 1},
            {"q": "Landing sahifada nechta asosiy CTA bo'lishi kerak?",
             "opts": ["Qancha ko'p, shuncha yaxshi", "Bitta aniq harakat", "Kamida uchta", "CTA umuman kerak emas"],
             "correct": 1},
        ],
    },
    8: {
        "title": "Analitika va metrikalar",
        "lessons": [
            {
                "id": "8.1",
                "title": "Metrikalar: qaysi raqam maqtaydi, qaysi biri gapiradi",
                "free": False,
                "text": (
"📖 <b>8.1-dars. Metrikalar: qaysi raqam maqtaydi, qaysi biri "
"gapiradi</b>\n\n"
"Marketing dunyosida raqamlar ikki xil bo'ladi. Birinchisi — "
"<b>vanity metrics</b> (bezak raqamlar): ko'rkam ko'rinadi, ko'ngilni "
"ko'taradi, lekin qaror chiqarishga yaramaydi. \"100 ming ko'rish!\" "
"— zo'r, xo'sh, nechta savdo bo'ldi? Ikkinchisi — <b>ishchi "
"raqamlar</b> (actionable): ular sizga aniq \"nima qilish "
"kerak\"ligini aytadi. Professional marketolog birinchisini "
"hisobotga, ikkinchisini qarorga ishlatadi.\n\n"
"<b>Asosiy lug'at (bir marta aniq tushunib olamiz)</b>\n\n"
"• <b>Impressions (ko'rsatishlar)</b> — kontent necha marta ekranda "
"paydo bo'ldi (bir odam 3 marta ko'rsa = 3).\n"
"• <b>Reach (qamrov)</b> — nechta <i>alohida odam</i> ko'rdi (o'sha "
"odam = 1).\n"
"• <b>ER (engagement rate)</b> — faollik: (layk + izoh + saqlash + "
"ulashish) ÷ qamrov. Kontent auditoriyaga qanchalik \"tegayotgani\"ni "
"ko'rsatadi.\n"
"• <b>CTR</b> — bosish ulushi: bosishlar ÷ ko'rsatishlar. E'lon yoki "
"havola qanchalik jalb qilayotganining o'lchovi.\n"
"• <b>Konversiya</b> — harakatga o'tganlar ulushi: 100 kirdi, 5 tasi "
"ariza qoldirdi = 5%.\n\n"
"<b>Raqamlarni zanjir qilib o'qish</b>\n\n"
"Alohida raqam kam narsa aytadi — kuch zanjirda: "
"<i>ko'rsatish → bosish → so'rov → savdo</i>. Zanjirning qayeri "
"ingichka bo'lsa, muammo o'sha yerda:\n"
"Ko'rsatish ko'p, bosish kam (past CTR) → e'lon zaif, hook "
"ishlamayapti.\n"
"Bosish ko'p, so'rov kam → landing/profil kutib ololmayapti "
"(7.3-dars esingizdami?).\n"
"So'rov ko'p, savdo kam → narx, taklif yoki suhbatda muammo.\n"
"Mana shu tashxis usuli \"reklama ishlamayapti\" degan mavhum "
"nolani aniq vazifaga aylantiradi.\n\n"
"<b>Hayotiy keys.</b> Onlayn kurs sotuvchisi \"reklamam ishlamayapti\" "
"deb keldi. Raqamlarni zanjirга terdik: CTR yaxshi (e'lon zo'r), "
"landing konversiyasi 1% (juda past). Sahifani ochsak — e'lon "
"\"3 oyda natija\" deb va'da qilgan, sahifa esa umumiy gaplar bilan "
"boshlanardi: message match buzilgan. Sarlavhani e'longa "
"moslashtirish va formani qisqartirish — konversiya 1% dan 4% ga "
"chiqdi. Reklama byudjeti o'zgarmadi, savdo 4 barobar oshdi. "
"Raqamlar aniq ko'rsatdi: muammo reklamada emas edi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> raqamlardan qo'rqmang — ular "
"ayblovchi emas, maslahatchi. To'g'ri o'qilgan bitta metrika o'nta "
"taxmindan qimmat."
                ),
            },
            {
                "id": "8.2",
                "title": "UTM: har bir so'm qayerdan kelganini bilish",
                "free": False,
                "text": (
"📖 <b>8.2-dars. UTM: har bir so'm qayerdan kelganini bilish</b>\n\n"
"Klassik holat: reklama uch joyda ketyapti — Instagram, Telegram "
"kanal, bloger. Savdo bor. Lekin <b>qaysi biridan?</b> Bilmasangiz, "
"keyingi oy byudjetni taxmin bilan taqsimlaysiz — ehtimol, "
"ishlamayotganiga quyib. Bu muammoning yechimi arzon va oddiy: "
"UTM belgilari.\n\n"
"<b>UTM nima?</b>\n\n"
"Havola oxiriga qo'shiladigan \"pasport\": odam qayerdan kelganini "
"aytib turadi. Oddiy havola:\n"
"<code>mysite.uz/kurs</code>\n"
"UTM bilan:\n"
"<code>mysite.uz/kurs?utm_source=instagram&utm_medium=reels&"
"utm_campaign=iyul_aksiya</code>\n\n"
"Uch asosiy parametr:\n"
"• <b>utm_source</b> — qayerdan (instagram, telegram, bloger_nomi)\n"
"• <b>utm_medium</b> — qanday turdagi (reels, stories, post, "
"reklama)\n"
"• <b>utm_campaign</b> — qaysi aksiya (iyul_aksiya, yangi_kurs)\n\n"
"Endi analitika tizimida har manbadan nechta odam kelgani va "
"nechtasi ariza qoldirgani <b>alohida-alohida</b> ko'rinadi. "
"Havolani qo'lda yozish shart emas — internetdagi bepul \"UTM "
"builder\"lar 10 soniyada yasab beradi.\n\n"
"<b>Sayt yo'q bo'lsa-chi? Promo-kod usuli</b>\n\n"
"O'zbekistonda ko'p savdo Direct va Telegram suhbatida bo'ladi — u "
"yerda UTM ko'rinmaydi. Yechim eskicha va ishonchli: <b>har kanalga "
"o'z promo-kodi yoki so'zi</b>. Blogerga: \"AZIZA so'zini aytganlarga "
"chegirma\". Telegram reklamasiga boshqa so'z. Endi mijozning "
"birinchi xabari o'zi manbani aytib turadi. Yoki eng oddiy usul — "
"so'rab qolish odati: \"Bizni qayerdan topdingiz?\" — va javobni "
"jadvalga yozib borish. Ilmiy emas, lekin nolga qaraganda yuz "
"barobar yaxshi.\n\n"
"<b>Google Analytics haqida ikki og'iz</b>\n\n"
"Saytingiz bo'lsa, Google Analytics (bepul) o'rnatilishi shart: u "
"UTM'larni o'zi o'qiydi, qaysi manba qancha odam va qancha "
"konversiya berganini jadval qilib beradi. Chuqur o'rganish alohida "
"kurs mavzusi, lekin boshlanish uchun bitta hisobot yetadi: "
"<i>Trafik manbalari → konversiyalar</i>. Haftada bir marta ochib "
"qarash odati — byudjetingizning eng yaxshi qo'riqchisi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> o'lchanmagan kanal — qorong'i xona: "
"pul sarflayapsiz, natijani ko'rmayapsiz. UTM yoki promo-kod — "
"chiroqni yoqish."
                ),
            },
            {
                "id": "8.3",
                "title": "ROI, CAC, LTV: biznesning uch harfli haqiqatlari",
                "free": False,
                "text": (
"📖 <b>8.3-dars. ROI, CAC, LTV: biznesning uch harfli "
"haqiqatlari</b>\n\n"
"Bu dars — kursning \"kalkulyator\" darsi. To'rtta formula bor, "
"hammasi maktab arifmetikasi darajasida, lekin aynan shular "
"marketingni \"his\"dan \"biznes\"ga aylantiradi.\n\n"
"<b>1. CAC — mijoz olish narxi</b>\n"
"<i>CAC = marketing sarfi ÷ kelgan yangi mijozlar soni</i>\n"
"Oyiga 2 mln so'm sarflab 40 mijoz oldingizmi — bitta mijoz 50 000 "
"so'mga tushdi.\n\n"
"<b>2. LTV — mijozning umr bo'yi qiymati</b>\n"
"<i>LTV = o'rtacha xarid foydasi × xaridlar soni</i>\n"
"Mijoz o'rtacha 60 000 foyda qoldirib, yiliga 4 marta qaytsa: "
"LTV = 240 000 so'm. Mana shu raqam ko'p narsani o'zgartiradi: "
"birinchi savdoda 50 000 CAC \"qimmat\" tuyulgan edi — LTV yonida "
"esa juda arzon. <b>Oltin nisbat: LTV kamida 3 × CAC.</b> Shu "
"nisbat buzilmasa, biznes sog'lom.\n\n"
"<b>3. ROAS — reklama qaytimi</b>\n"
"<i>ROAS = reklamadan kelgan tushum ÷ reklama sarfi</i>\n"
"1 mln sarflab 4 mln tushum = ROAS 4. Tez, kunlik nazorat uchun "
"qulay o'lchov.\n\n"
"<b>4. ROI — sof foyda qaytimi</b>\n"
"<i>ROI = (foyda − sarf) ÷ sarf × 100%</i>\n"
"ROAS'dan farqi: tushum emas, <b>foyda</b> hisoblanadi (tannarx, "
"yetkazish — hammasi ayirilgan holda). ROAS 4 bo'lsa-yu, mahsulot "
"marjasi past bo'lsa, ROI minus chiqishi mumkin — \"savdo ko'p, pul "
"yo'q\" degan sirli holatning javobi ko'pincha shu yerda.\n\n"
"<b>Hayotiy keys.</b> Ikki mahsulotli do'kon: A mahsulot reklamasi "
"ROAS 5 beradi, B mahsulot — ROAS 3. Egasi byudjetni A'ga quyayotgan "
"edi. ROI hisoblanganda rasm teskari chiqdi: A'ning marjasi 15% "
"(ROI past), B'niki 55% (ROI baland). Byudjet B'ga ko'chirildi — "
"oylik <b>foyda</b> sezilarli o'sdi, garchi \"tushum\" kamaygandek "
"ko'rinsa ham. ROAS chiroyli gapirdi, ROI haqiqatni aytdi.\n\n"
"<b>Oddiy hisobot odati</b>\n\n"
"Oyiga bir marta, bitta jadval, beshta ustun: kanal · sarf · "
"mijozlar · CAC · foyda. 15 daqiqalik ish. Uch oy yig'ilsa, "
"byudjet qarorlarini siz emas — jadval qabul qila boshlaydi.\n\n"
"💡 <b>Esda qoladigan fikr:</b> marketing ijodkorlikdan boshlanadi, "
"lekin arifmetikada g'alaba qozonadi.\n\n"
"✍️ <b>Haftalik topshiriq:</b> hayoliy (yoki real) raqamlar bilan "
"hisoblang: oylik reklama 1,5 mln so'm, kelgan mijozlar 30 ta, "
"o'rtacha xarid foydasi 80 000 so'm, mijoz yiliga o'rtacha 3 marta "
"qaytadi. CAC, LTV va LTV/CAC nisbatini toping — bu biznes "
"sog'lommi? Javob va hisob-kitobingizni botga yuboring!"
                ),
            },
        ],
        "test": [
            {"q": "Vanity metric (bezak raqam)ga misol qaysi?",
             "opts": ["Bitta mijoz olish narxi (CAC)",
                      "Umumiy ko'rishlar soni, savdoga bog'lanmagan holda",
                      "Landing konversiyasi",
                      "Reklama qaytimi (ROAS)"],
             "correct": 1},
            {"q": "Reach va Impressions farqi nimada?",
             "opts": ["Farqi yo'q",
                      "Reach — alohida odamlar, Impressions — jami ko'rsatishlar",
                      "Reach faqat Instagram'da bo'ladi",
                      "Impressions — faqat pullik reklamada"],
             "correct": 1},
            {"q": "CTR yaxshi, lekin so'rovlar kam — muammo qayerda bo'lishi ehtimol?",
             "opts": ["E'londa", "Landing/qabul qiluvchi sahifada", "Auditoriyada", "Byudjetda"],
             "correct": 1},
            {"q": "utm_source parametri nimani bildiradi?",
             "opts": ["Aksiya nomini", "Trafik qayerdan kelganini", "Reklama narxini", "Sayt tezligini"],
             "correct": 1},
            {"q": "CAC qanday hisoblanadi?",
             "opts": ["Tushum ÷ sarf",
                      "Marketing sarfi ÷ yangi mijozlar soni",
                      "Foyda × mijozlar soni",
                      "Sarf × 100%"],
             "correct": 1},
            {"q": "Sog'lom biznes uchun oltin nisbat qaysi?",
             "opts": ["LTV kamida 3 barobar CAC'dan katta",
                      "CAC kamida 3 barobar LTV'dan katta",
                      "ROAS har doim 10 dan yuqori",
                      "CAC = LTV bo'lishi kerak"],
             "correct": 0},
        ],
    },
    9: {"title": "Funnel, email va influencer marketing", "lessons": [], "test": []},
    10: {"title": "Strategiya va yakuniy loyiha", "lessons": [], "test": []},
}
