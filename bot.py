import os
import logging
import uuid
import httpx
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile

# ============ ЗАГРУЗКА ТОКЕНОВ ============
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_AUTH = os.getenv("GIGACHAT_KEY")

os.environ["SSL_CERT_FILE"] = os.path.expanduser("~/Documents/legaltech/russian_ca.crt")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ============ GIGACHAT ============
def get_gigachat_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH}"
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    r = httpx.post(url, headers=headers, data=data, verify=False, timeout=30)
    return r.json().get("access_token")

def ask_gigachat(messages):
    try:
        token = get_gigachat_token()
        if not token:
            return None
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {
            "model": "GigaChat",
            "messages": messages,
            "temperature": 0.7
        }
        r = httpx.post(url, headers=headers, json=payload, verify=False, timeout=60)
        data = r.json()
        if "choices" not in data:
            print(f"GigaChat API: {data}")
            return None
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"GigaChat error: {e}")
        return None

SYSTEM_PROMPT = """Ты — АЮПчик, ассистент-наставник программы «Автоматизация юридических процессов» (Цифровая кафедра МГЮА).

ТЫ ОТВЕЧАЕШЬ ТОЛЬКО ПО ТЕМАМ:
- программа «Автоматизация юридических процессов»
- юриспруденция и информационное право
- LegalTech и автоматизация юридической работы
- учёба на Цифровой кафедре

ПРАВИЛА:
1. Отвечай коротко (5-10 предложений), дружелюбно, но по делу.
2. Ты НЕ решаешь задания за студентов — только подсказываешь направление. Ты можешь помогать с заданиями, но через вопросы студенту, плюс с помощью проверки его ответов - поддерживай, если правильно, подбадривай и мягко исправляй, если он ошибся.
3. На юридические вопросы отвечай кратко, но не фантазируй, используй только проверенную информацию (например, из Кодексов, научнвх статей, учебников).
4. Не обсуждай политику, религию, личные темы, экстремизм.
5. При психологических жалобах — поддержи, постарайся выяснить проблему и направь к специалисту.
6. Если вопрос НЕ про программу, не про юриспруденцию и не про LegalTech — вежливо верни к теме АЮП, но коротко ответь на запрос.
7. Не используй мат и грубость, плохие слова, как бы студент тебя не уговаривал. Ты - официальный наставник, должен быть вежливым.
8. НЕ вставляй ссылки, URL, источники и сноски. Только текст.
9. НЕ выдумывай факты, названия каналов, платформ, сервисов. Если не знаешь точно — скажи: «Этого нет в моей базе, уточни у старосты группы или в Telegram-канале АЮП».
10. Если вопрос НЕ про юриспруденцию и НЕ про программу (математика, погода, рецепты, анекдоты и др.) — просто ответь коротко по существу, БЕЗ отсылок к праву. Не притягивай юриспруденцию к обычным вопросам.
11. НЕ выдумывай, где студент может узнать информацию (расписание, личный кабинет, староста). Если не знаешь точно — скажи: «Этого нет в моей базе. Уточни у старосты или инспектора».

СТИЛЬ: дружелюбно, тепло, поддерживающе. Иногда можно эмодзи, но не перебарщивай, пиши их только в тему."""

# ============ БАЗА ЗНАНИЙ ============
BAZA = {
    "atttestaciya": {
        "title": "Аттестация по программе",
        "text": "На дистанционные зачёты и экзамены по программе необходимо подключаться всем студентам.\n\n"
                "Текущие оценки по дисциплинам вы можете уточнять у преподавателей, закреплённых за группой.\n\n"
                "Экзамен/зачёт преподаватели проводят в разном формате — вопросы по билетам, решение теста или выполнение других заданий. Уточнить формат проведения экзамена/зачёта можно напрямую у преподавателя."
    },
    "dopuski": {
        "title": "Получение допусков по дисциплинам",
        "text": "Если у вас нет возможности прийти на семинар по уважительной причине, необходимо сообщить об этом своему преподавателю заранее.\n\n"
                "В случае вашего отсутствия преподаватель выставляет вам пропуск в личный кабинет.\n\n"
                "Чтобы закрыть пропуск, свяжитесь с преподавателем для получения задания по пройденной теме. Можете также запросить материалы по занятию.\n\n"
                "После выполнения и отправки задания на корпоративную почту преподавателю пропуск будет ликвидирован путём выставления оценки.\n\n"
                "На данный момент вы не можете видеть свои текущие оценки в системе. Уточняйте их напрямую у преподавателей."
    },
    "raspisanie": {
        "title": "Расписание занятий",
        "text": "Расписание занятий появляется в Личном кабинете обучающегося МГЮА.\n\n"
                "Расписание лекций составлено для всего потока и находится в файле, который публикуется на официальном канале Цифровой кафедры в Max и Telegram.\n\n"
                "Там же доступны записи всех пройденных лекций."
    },
    "plan": {
        "title": "Учебный план",
        "text": "📚 Алгоритмика — 6 лекций, 17 семинаров, экзамен во 2 семестре\n\n"
                "📚 Анализ и моделирование бизнес-процессов организации — 5 лекций, 7 семинаров, экзамен во 2 семестре\n\n"
                "📚 Управление ИТ-проектами — 5 лекций, 8 семинаров, зачёт во 2 семестре\n\n"
                "📚 Методология разработки ПО — 7 лекций, 4 семинара, зачёт во 2 семестре\n\n"
                "📚 Автоматизация юридической работы (LegalTech) — 7 лекций, зачёт в 1 семестре\n\n"
                "Оценки по всем дисциплинам будут указаны в дипломе о профессиональной переподготовке."
    },
    "lekcii": {
        "title": "Лекционные и семинарские занятия",
        "text": "Все занятия проводятся на платформе МТС Link. Ссылка на подключение подкреплена к занятию в Личном кабинете.\n\n"
                "❓ Что делать при пропуске:\n"
                "Напишите на корпоративную почту преподавателю, предупредите о пропуске и уточните домашнее задание для отработки.\n\n"
                "❓ Нужны ли доп. программы:\n"
                "Нет, достаточно стандартного набора. Также есть доступ к программам через систему «Цифровой университет».\n\n"
                "❓ Можно ли посмотреть запись лекции:\n"
                "Да, записи выкладываются на Яндекс.Диск — ссылка в разделе «🔗 Ссылки».\n\n"
                "❓ Можно ли присутствовать с другим потоком:\n"
                "Да. Актуальная информация — в Telegram-канале АЮП.\n\n"
                "❓ Продолжительность занятия:\n"
                "2 академических часа (1 час 20 минут)."
    },
    "proekt": {
        "title": "Итоговый проект",
        "text": "Итоговая аттестация проходит в форме защиты проекта. Студенты демонстрируют цифровые компетенции, полученные в процессе освоения программы.\n\n"
                "В течение обучения студенты в группах разрабатывают и готовят проект под руководством преподавателя.\n\n"
                "Защита сопровождается презентацией с комментариями об этапах реализации проекта и демонстрацией прототипа.\n\n"
                "Защита проходит с участием представителей профильных индустриальных партнёров.\n\n"
                "По итогам защиты комиссия выставляет оценку, которая отражается в дипломе. Оценки за итоговую аттестацию не влияют на оценки в дипломе по основной программе."
    },
    "stazhirovka": {
        "title": "Стажировка (практика)",
        "text": "Стажировка предусмотрена программой и проходит дистанционно.\n\n"
                "Первый этап — установочные лекции с компаниями-партнёрами.\n"
                "Второй этап — выполнение заданий от партнёров. Кейсы можно использовать как основу для итогового проекта.\n\n"
                "Компании предоставляют доступ к своему ПО на несколько месяцев. Лекции партнёров доступны в записи.\n\n"
                "По окончании стажировки нужно подготовить отчёт по шаблону (шаблон — в разделе «📄 Шаблоны»). Форма отчёта — свободная."
    },
    "partnery": {
        "title": "Компании-партнёры программы",
        "text": "Программа реализуется при участии ведущих отраслевых компаний:\n\n"
                "🔹 Гарант\n"
                "🔹 КонсультантПлюс\n"
                "🔹 Докзилла\n"
                "🔹 ПравоТех\n"
                "🔹 Директум (СофтСноу)\n"
                "🔹 Актион\n"
                "🔹 Кодекс\n"
                "🔹 Турбоконтракт\n\n"
                "Партнёры проводят установочные лекции, предоставляют доступ к своему ПО и выдают задания для стажировки. Кейсы можно использовать при подготовке итогового проекта."
    },
    "resheniya": {
        "title": "Что автоматизируется на программе",
        "text": "В рамках программы осваиваются:\n\n"
                "🔧 Конструкторы договоров — подготовка документа за минуты вместо часов.\n\n"
                "🔧 Сервисы проверки контрагентов — анализ данных из ФНС, судов и санкционных списков.\n\n"
                "🔧 Интеллектуальный поиск правовой информации — доступ к практике за секунды.\n\n"
                "🔧 Системы централизованного хранения — единый источник правды вместо флешек и почты.\n\n"
                "🔧 Инструменты планирования — управление сроками и ресурсами проекта.\n\n"
                "Всё это помогает юристу тратить меньше времени на рутину и больше — на сложные задачи."
    },
    "cel": {
        "title": "Цель программы",
        "text": "Цель проекта «Цифровые кафедры» — обеспечение приоритетных отраслей экономики высококвалифицированными кадрами с цифровыми компетенциями.\n\n"
                "Проект направлен на поддержание баланса спроса и предложения на рынке труда ИТ-отрасли. Формирует у обучающихся цифровые компетенции в области создания алгоритмов и компьютерных программ, а также навыки использования цифровых компетенций для нового вида профессиональной деятельности."
    },
    "documents": {
        "title": "Документы и сертификаты",
        "text": "❓ Какой документ я получу по окончании:\n"
                "Диплом о профессиональной переподготовке государственного образца.\n\n"
                "❓ Когда я получу диплом:\n"
                "По окончании обучения и успешном прохождении итоговой аттестации.\n"
                "Важно: обязательное условие — наличие диплома о высшем образовании. Если обучение завершено раньше, диплом ПП выдаётся одновременно с дипломом о ВО.\n\n"
    },
    "discipliny": {
        "title": "Дисциплины",
        "text": "В программе 5 дисциплин:\n\n"
                "1️⃣ Алгоритмика — базовая компьютерная грамотность, алгоритмическое мышление.\n\n"
                "2️⃣ Анализ и моделирование бизнес-процессов организации — моделирование и оптимизация процессов.\n\n"
                "3️⃣ Управление ИТ-проектами — управление проектами в IT-сфере, постановка требований, контроль.\n\n"
                "4️⃣ Методология разработки ПО — понимание процессов создания программ, коммуникация с IT-специалистами.\n\n"
                "5️⃣ Автоматизация юридической работы (LegalTech) — рынок LegalTech, оценка ПО, внедрение решений.\n\n"
                "Программирование НЕ изучается. Но по просьбе группы преподаватели могут дать доп. материалы."
    },
    "obuchenie": {
        "title": "Обучение",
        "text": "❓ Продолжительность: 9 месяцев.\n\n"
                "❓ Объём программы: 398 академических часов.\n\n"
                "❓ Начало/конец: старт — первая неделя октября, завершение — июнь, день защиты итогого аттестационного проекта.\n\n"
                "❓ Формат: все занятия дистанционно. Очное присутствие — только на защите итоговых проектов.\n"
                "❗ Отсутствие на итоговой аттестации без уважительной причины = отчисление без диплома.\n\n"
                "Посещение семинаров фиксируется в электронном журнале."
    },
    "zachislenie": {
        "title": "Зачисление",
        "text": "❓ Документы для зачисления:\n"
                "Заявление на зачисление и согласие на обработку персональных данных (в письменном виде).\n"
                "Шаблоны можно скачать в этом боте — кнопки ниже.\n\n"
                "❓ Кто может участвовать:\n"
                "Студенты бакалавриата, специалитета, магистратуры.\n\n"
                "✅ Формы обучения: только очная и очно-заочная (вечерняя).\n"
                "❌ Заочная форма обучения НЕ участвует в программе.\n\n"
                "✅ Курсы:\n"
                "— Бакалавриат и специалитет: только с 3 курса.\n"
                "— 1 и 2 курсы бакалавриата и специалитета — НЕ допускаются.\n"
                "— Магистратура: с 1 курса.\n"
                "— Заявления 4 курса бакалавриата и магистратуры — в индивидуальном порядке.\n"
                "— 5 курс очно-заочной формы — не принимается.\n\n"
                "❗ Один обучающийся может получить ИТ-квалификацию на «цифровой кафедре» только один раз.\n\n"
                "❓ Сколько стоит: полностью бесплатно.\n\n"
                "❓ Нужна ли математика: нет, углублённые технические знания не требуются."
    },
    "vremya": {
        "title": "Время занятий",
        "text": "Занятия по программе проводятся:\n\n"
                "📅 По будням в вечернее время:\n"
                "— 16:30–17:50\n"
                "— 18:40–20:00\n"
                "— 20:10–21:30\n\n"
                "📅 В субботу — в свободное от основной программы время."
    },
}

# ============ КЛАВИАТУРЫ ============
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Я обучаюсь", callback_data="menu_learn"),
         InlineKeyboardButton(text="🎓 Хочу учиться", callback_data="menu_want")],
        [InlineKeyboardButton(text="📄 Шаблоны", callback_data="menu_templates"),
         InlineKeyboardButton(text="🔗 Ссылки", callback_data="menu_links")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts")],
    ])

def learn_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Аттестация", callback_data="info_atttestaciya")],
        [InlineKeyboardButton(text="Допуски", callback_data="info_dopuski")],
        [InlineKeyboardButton(text="Расписание", callback_data="info_raspisanie")],
        [InlineKeyboardButton(text="Учебный план", callback_data="info_plan")],
        [InlineKeyboardButton(text="Лекции и семинары", callback_data="info_lekcii")],
        [InlineKeyboardButton(text="Итоговый проект", callback_data="info_proekt")],
        [InlineKeyboardButton(text="Стажировка", callback_data="info_stazhirovka")],
        [InlineKeyboardButton(text="Компании-партнёры", callback_data="info_partnery")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def want_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Цель программы", callback_data="info_cel")],
        [InlineKeyboardButton(text="Документы и сертификаты", callback_data="info_documents")],
        [InlineKeyboardButton(text="Дисциплины", callback_data="info_discipliny")],
        [InlineKeyboardButton(text="Обучение", callback_data="info_obuchenie")],
        [InlineKeyboardButton(text="Зачисление", callback_data="info_zachislenie")],
        [InlineKeyboardButton(text="Время занятий", callback_data="info_vremya")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def templates_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Презентация (красная)", callback_data="tpl_pres_red")],
        [InlineKeyboardButton(text="📊 Презентация (синяя)", callback_data="tpl_pres_blue")],
        [InlineKeyboardButton(text="📝 Отчёт о стажировке", callback_data="tpl_otchet")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def links_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Telegram-канал", url="https://t.me/ajpmsal")],
        [InlineKeyboardButton(text="🎥 Записи лекций", url="https://disk.360.yandex.ru/i/WQoyXs_CfuJ8Xw")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

# ============ КОМАНДЫ ============
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот Цифровой кафедры МГЮА.\n\n"
        "Помогу с вопросами по программе «Автоматизация юридических процессов».\n\n"
        "Выбери раздел или просто напиши свой вопрос.",
        reply_markup=main_menu()
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("Выбери раздел:", reply_markup=main_menu())

# ============ КНОПКИ ============
@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text("Выбери раздел:", reply_markup=main_menu())

@dp.callback_query(F.data == "menu_learn")
async def menu_learn(callback: CallbackQuery):
    await callback.message.edit_text("📚 Раздел «Я обучаюсь»\n\nВыбери тему:", reply_markup=learn_menu())

@dp.callback_query(F.data == "menu_want")
async def menu_want(callback: CallbackQuery):
    await callback.message.edit_text("🎓 Раздел «Хочу учиться»\n\nВыбери тему:", reply_markup=want_menu())

@dp.callback_query(F.data == "menu_templates")
async def menu_templates(callback: CallbackQuery):
    await callback.message.edit_text("📄 Шаблоны\n\nВыбери нужный:", reply_markup=templates_menu())

@dp.callback_query(F.data == "menu_links")
async def menu_links(callback: CallbackQuery):
    await callback.message.edit_text("🔗 Полезные ссылки:", reply_markup=links_menu())

@dp.callback_query(F.data == "menu_contacts")
async def menu_contacts(callback: CallbackQuery):
    text = (
        "📞 Контакты Цифровой кафедры\n\n"
        "👤 Руководитель проекта — Соловьева Екатерина Владимировна\n"
        "✉️ evsoloveva@msal.ru\n"
        "📱 +7 (499) 244-88-88 (доб. 8058)\n\n"
        "👤 Старший инспектор — Манюгина Виктория Алексеевна\n"
        "✉️ vamanyugina@msal.ru\n"
        "📱 +7 (499) 244-88-88 (доб. 071)\n\n"
        "👤 Инспектор — Кузьмина Елизавета Евгеньевна\n"
        "✉️ eekuzmina@msal.ru\n"
        "📱 +7 (499) 244-88-88 (доб. 8059)\n\n"
        "👤 Инспектор — Быкова Ксения Ивановна\n"
        "✉️ kibykova@msal.ru\n"
        "📱 +7 (499) 244-88-88 (доб. 0258)"
    )
    await callback.message.edit_text(text, reply_markup=back_kb())

@dp.callback_query(F.data.startswith("info_"))
async def show_info(callback: CallbackQuery):
    key = callback.data.replace("info_", "")
    if key in BAZA:
        item = BAZA[key]

        if key == "zachislenie":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Скачать заявление", callback_data="doc_zayavlenie")],
                [InlineKeyboardButton(text="📥 Скачать согласие", callback_data="doc_soglasie")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
            ])
        else:
            kb = back_kb()

        await callback.message.edit_text(
            f"**{item['title']}**\n\n{item['text']}",
            reply_markup=kb,
            parse_mode="Markdown"
        )

@dp.callback_query(F.data == "doc_zayavlenie")
async def doc_zayavlenie(callback: CallbackQuery):
    try:
        file = FSInputFile("files/zayavlenie.docx")
        await callback.message.answer_document(file, caption="📄 Заявление на зачисление")
    except FileNotFoundError:
        await callback.message.answer("Файл не найден. Напиши инспектору.")
    await callback.answer()

@dp.callback_query(F.data == "doc_soglasie")
async def doc_soglasie(callback: CallbackQuery):
    try:
        file = FSInputFile("files/soglasie.docx")
        await callback.message.answer_document(file, caption="📄 Согласие на обработку ПДн")
    except FileNotFoundError:
        await callback.message.answer("Файл не найден. Напиши инспектору.")
    await callback.answer()

@dp.callback_query(F.data == "tpl_pres_red")
async def tpl_pres_red(callback: CallbackQuery):
    try:
        file = FSInputFile("files/pres_red.pptx")
        await callback.message.answer_document(file, caption="📊 Шаблон презентации (красный)")
    except FileNotFoundError:
        await callback.message.answer("Файл не найден. Напиши инспектору.")
    await callback.answer()

@dp.callback_query(F.data == "tpl_pres_blue")
async def tpl_pres_blue(callback: CallbackQuery):
    try:
        file = FSInputFile("files/pres_blue.pptx")
        await callback.message.answer_document(file, caption="📊 Шаблон презентации (синий)")
    except FileNotFoundError:
        await callback.message.answer("Файл не найден. Напиши инспектору.")
    await callback.answer()

@dp.callback_query(F.data == "tpl_otchet")
async def tpl_otchet(callback: CallbackQuery):
    try:
        file = FSInputFile("files/otchet.docx")
        await callback.message.answer_document(file, caption="📝 Шаблон отчёта о стажировке")
    except FileNotFoundError:
        await callback.message.answer("Файл не найден. Напиши инспектору.")
    await callback.answer()

# ============ СВОБОДНЫЙ ТЕКСТ ============
@dp.message(F.text)
async def handle_text(message: Message):
    text = message.text.lower().strip()

    # 1. Мат
    bad_words = ["хуй", "пизд", "бля", "еба", "сук", "мраз", "гандон", "нахуй", "ахуе", "долбоеб"]
    if any(word in text for word in bad_words):
        await message.answer("Давай общаться уважительно 🙏\n\nЯ здесь, чтобы помочь с программой АЮП.\n\n🔙 В меню: /menu")
        return

    # 2. Политика, религия
    taboo = ["политик", "президент", "путин", "навальн", "религи", "бог", "церковь", "ислам", "христиан", "молитв"]
    if any(word in text for word in taboo):
        await message.answer("Я не обсуждаю политику и религию — это вне моей компетенции 🙌\n\nЯ помогаю по программе «Автоматизация юридических процессов».\n\n🔙 В меню: /menu")
        return

    # 3. Просьбы решить за студента
    if any(word in text for word in ["реши за меня", "сделай за меня", "сделай домашку", "реши домашку", "напиши за меня", "выполни за меня"]):
        await message.answer("Я не решаю задания за студентов 🙌\n\nНо помогу разобраться: расскажи, что уже сделал(а) и где застрял(а) — подскажу направление.\n\n🔙 В меню: /menu")
        return
    
    # 4. Поиск по ключевым словам в базе
    keywords_map = {
        "аттестац": "atttestaciya", "зачёт": "atttestaciya", "зачет": "atttestaciya", "экзамен": "atttestaciya",
        "допуск": "dopuski", "пропуск": "dopuski",
        "расписани": "raspisanie", "план": "plan",
        "лекци": "lekcii", "семинар": "lekcii", "мтс": "lekcii",
        "проект": "proekt", "защит": "proekt",
        "стажировк": "stazhirovka", "практик": "stazhirovka",
        "партнёр": "partnery", "партнер": "partnery", "компани": "partnery",
        "гарант": "partnery", "консультант": "partnery", "докзилла": "partnery",
        "правотех": "partnery", "директум": "partnery", "софтсноу": "partnery",
        "актион": "partnery", "кодекс": "partnery", "турбоконтракт": "partnery",
        "автоматизац": "resheniya", "рутин": "resheniya", "дедлайн": "resheniya",
        "цель": "cel", "документ": "documents", "диплом": "documents", "сертификат": "documents",
        "дисциплин": "discipliny", "обучени": "obuchenie", "срок": "obuchenie",
        "зачислени": "zachislenie", "заявк": "zachislenie", "поступлени": "zachislenie",
        "время": "vremya", "заняти": "vremya",
        "запис": "lekcii", "вебинар": "lekcii",
    }
    for keyword, key in keywords_map.items():
        if keyword in text and key in BAZA:
            item = BAZA[key]
            await message.answer(f"**{item['title']}**\n\n{item['text']}\n\n🔙 В меню: /menu", parse_mode="Markdown")
            return
        
        # 5. Приветствия
    if any(word in text for word in ["привет", "здравствуй", "хай", "добрый день", "добрый вечер", "доброе утро", "как дела", "как у тебя", "как твои", "как ты", "как жизнь", "как настроение", "как оно", "как сам", "чё как", "че как", "что делаешь", "чем занят", "делишки", "как делишки"]):
            import random
            otvety = [
                "Привет! 👋 У меня всё отлично. Готов помочь с вопросами по программе «Автоматизация юридических процессов».\n\nНапиши свой вопрос или выбери раздел — /menu",
                "Привет! 😊 Спасибо, что зашёл. Чем могу помочь? Спроси про зачисление, расписание, дисциплины или стажировку.\n\n🔙 В меню: /menu",
                "Привет! Рад тебя видеть. Я тут, чтобы помочь с программой АЮП. Что тебя интересует?\n\n🔙 В меню: /menu",
            ]
            await message.answer(random.choice(otvety))
            return

    # 6. Психологическая поддержка
    if any(word in text for word in ["устал", "устала", "выгорел", "выгорела", "нет сил", "грустно", "тревожно", "паника", "плохое настроение", "депресс", "тяжело на душе", "плохо себя"]):
        await message.answer(
            "Понимаю тебя 💙 Такое бывает у всех — особенно когда учёба идёт валом.\n\n"
            "Ты уже молодец, что не сдаёшься. Иногда надо просто выдохнуть: пауза, сон, чай, прогулка.\n\n"
            "Учёба важна, но твоё здоровье — важнее. Если совсем тяжело — поговори с психологом университета или с близким человеком.\n\n"
            "Я рядом. 🌱\n\n🔙 В меню: /menu"
        )
        return

    # 7. FALLBACK → GigaChat
    await message.answer("🤔 думаю-думаю...")

    messages_for_api = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": message.text}
    ]

    response = ask_gigachat(messages_for_api)

    if response:
        await message.answer(f"{response}\n\n🔙 В меню: /menu")
    else:
        await message.answer(
            "Я помогаю по программе «Автоматизация юридических процессов» 🙌\n\n"
            "Спроси про зачисление, расписание, дисциплины, стажировку или итоговый проект.\n\n"
            "🔙 В меню: /menu"
        )

# ============ ЗАПУСК ============
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())