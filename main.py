import math
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import pandas as pd
from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove 
import os
import logging
import aiofiles  
import urllib.parse
from aiogram.utils.exceptions import BadRequest
#------------------------------------------------------Основная часть-------------------------------------------------
# Настройка логирования
logging.basicConfig(
    encoding="utf-8",
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='bot_log.log'
)
logger = logging.getLogger(__name__)

# Константы
EXCEL_FILE = 'users_data.xlsx'
BOT_TOKEN = "7791083296:AAEQ-qd6JLhFOhhuTrf8ismg7Bb857u_nh8"
TOPICS_FILE = 'topics.txt'
ADMIN_CHAT_ID="857663686" #442532106
ALONE_FILE = 'alone.xlsx'
IMAGE_FOLDER = 'images'
files = [f for f in os.listdir(IMAGE_FOLDER) if f.endswith('.jpg') or f.endswith('.png')]
topics_dict = {}

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# --- Состояния FSM ---
class UserStates(StatesGroup):
    FullnameState = State()
    GroupState = State()
    TopicState = State()
    AnswerState = State()
    ExampleState = State()
    SearchState=State()

# --- Функции для работы с файлами ---
#<<<-Exel->>>
def create_excel_file():
    """Создает Excel файл с заголовками, если он не существует."""
    try:
        if not os.path.exists(EXCEL_FILE):
            df = pd.DataFrame(columns=["ФИО", "TG_ID", "Тема", "Группа"])
            df.to_excel(EXCEL_FILE, index=False)
            logger.info("Создан новый Excel файл")
        else:
            logger.info("Файл эксель уже создан")
    except Exception as e:
        logger.error(f"Ошибка при создании Excel файла: {e}")
def is_user_in_excel(user_id):
    """Проверяет, зарегистрирован ли пользователь."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        return str(user_id) in df['TG_ID'].astype(str).values
    except Exception as e:
        logger.error(f"Ошибка при проверке пользователя: {e}")
        return False
def add_user_to_excel(fio, tg_id):
    """Добавляет нового пользователя в Excel."""
    try:
        # Проверяем, существует ли файл, и создаем новый DataFrame, если нет
        df = pd.read_excel(EXCEL_FILE) if os.path.exists(EXCEL_FILE) else pd.DataFrame(columns=["ФИО", "TG_ID", "Тема", "Группа"])
        new_row = pd.DataFrame([[fio, tg_id, "", ""]], columns=["ФИО", "TG_ID", "Тема", "Группа"])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(EXCEL_FILE, index=False)
        logger.info(f"Добавлен новый пользователь: {tg_id}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя: {e}")
        raise e
def add_group_to_excel(user_id, group): 
    """Добавляет группу пользователя в Excel файл."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        if user_id in df['TG_ID'].values:
            df.loc[df['TG_ID'] == user_id, 'Группа'] = group 
            df.to_excel(EXCEL_FILE, index=False)
            logger.info(f"Добавлена группа {group} для пользователя {user_id}")
            return True
        return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении группы: {e}")
        return False
def get_user_info(user_id: int) -> dict:
    """
    Получает информацию о пользователе из основного файла регистрации
    """
    try:
        df = pd.read_excel(EXCEL_FILE)  # Используем константу EXCEL_FILE
        user_row = df[df['TG_ID'] == user_id].iloc[0]
        
        return {
            'full_name': user_row['ФИО'],
            'group': user_row['Группа']
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о пользователе: {e}")
        return None
def has_user_topic(tg_id):
    """Проверяет, выбрал ли пользователь тему."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        user_data = df[df['TG_ID'] == tg_id]
        if user_data.empty:
            return False
        return pd.notna(user_data.iloc[0]['Тема'])
    except Exception as e:
        logger.error(f"Ошибка при проверке темы пользователя: {e}")
        return False
def add_to_alone_file(user_data: dict) -> bool:
    """
    Добавляет информацию об одиночном участнике в файл alone.xlsx
    """
    try:
        # Если файл не существует, создаем его с заголовками
        if not os.path.exists('alone.xlsx'):
            df = pd.DataFrame(columns=['ФИО', 'TG_ID', 'Группа', 'Тема'])
            df.to_excel('alone.xlsx', index=False)

        # Читаем существующий файл
        df = pd.read_excel('alone.xlsx')

        # Создаем новую строку с правильными ключами
        new_row = pd.DataFrame({
            'ФИО': [user_data['full_name']],
            'TG_ID': [user_data['tg_id']],  # Изменено на TG_ID
            'Группа': [user_data['group']],
            'Тема': [user_data['selected_topic']]
        })

        # Добавляем новую строку
        df = pd.concat([df, new_row], ignore_index=True)

        # Сохраняем обновленный файл
        df.to_excel('alone.xlsx', index=False)
        return True

    except Exception as e:
        logger.error(f"Ошибка при добавлении в alone.xlsx: {e}")
        return False

#<<<-Txt->>>
async def add_topic_to_user(tg_id, topic):
    """Добавляет выбранную тему пользователю."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        if not df[df['TG_ID'] == tg_id].empty:
            df.loc[df['TG_ID'] == tg_id, 'Тема'] = topic
            df.to_excel(EXCEL_FILE, index=False)
            State
            logger.info(f"Добавлена тема для пользователя {tg_id}: {topic}")
            
            return True
        else:
            logger.warning(f"Пользователь {tg_id} не найден в файле")
            return False
    except Exception as e:
        logger.error(f"Ошибка при добавлении темы: {e}")
        return False    
async def load_topics():
    """Загружает список доступных тем."""
    try:
        if not os.path.exists(TOPICS_FILE):
            logger.warning(f"Файл тем не найден: {TOPICS_FILE}")
            return []
        
        async with aiofiles.open(TOPICS_FILE, mode='r', encoding='utf-8') as file:
            topics = await file.readlines()
        return [topic.strip() for topic in topics if topic.strip()]
    except Exception as e:
        logger.error(f"Ошибка при загрузке тем: {e}")
        return []
async def remove_topic_from_file(topic):
    """Удаляет выбранную тему из файла."""
    try:
        async with aiofiles.open(TOPICS_FILE, mode='r', encoding='utf-8') as file:
            topics = await file.readlines()
        
        topics = [t.strip() for t in topics if t.strip() != topic]
        
        async with aiofiles.open(TOPICS_FILE, mode='w', encoding='utf-8') as file:
            await file.write('\n'.join(topics))
        logger.info(f"Тема удалена из файла: {topic}")
    except Exception as e:
        logger.error(f"Ошибка при удалении темы: {e}")       
async def set_commands(bot: Bot):
    """Установка команд бота."""
    commands = [
        types.BotCommand(command="/start", description="Начать работу"),
        types.BotCommand(command="/help", description="Список команд"),
        types.BotCommand(command="/registr", description="Регистрация"),
        types.BotCommand(command="/profile", description="Мой профиль"),
        types.BotCommand(command="/topics", description="Выбрать тему"),
        types.BotCommand(command="/answer", description="Вопрос-ответ"),
        types.BotCommand(command="/contorg", description="Связь с координатором"),
        types.BotCommand(command="/example", description="Примеры проектов"),
    ]
    await bot.set_my_commands(commands)
async def read_questions_from_file(file_path: str) -> list:
    """Читает вопросы и ответы из файла."""
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не найден")
            return []

        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            content = await file.read()
            raw_blocks = content.split('<')

            questions = []
            for block in raw_blocks:
                block = block.strip()
                if block:
                    parts = block.split('\n', 1)
                    if len(parts) == 2:
                        question = parts[0].strip()
                        answer = parts[1].strip()
                        questions.append((question, answer))

            logger.info(f"Загружено {len(questions)} вопросов из файла")
            return questions

    except Exception as e:
        logger.error(f"Ошибка при чтении файла вопросов: {e}")
        return []
async def find_topics_by_keywords(keywords):
    try:
        with open('topics.txt', 'r', encoding='utf-8') as file:
            all_topics = file.readlines()
        
        matching_topics = []
        for topic in all_topics:
            topic = topic.strip()
            if any(keyword.lower() in topic.lower() for keyword in keywords):
                matching_topics.append(topic)
        
        logger.info(f'Найдено {len(matching_topics)} тем по ключевым словам: {keywords}')
        return matching_topics

    except FileNotFoundError:
        logger.error('Файл topics.txt не найден.')
        return []
    except Exception as e:
        logger.error(f'Ошибка при обработке файла: {e}')
        return []
    
#<<<-Image->>>
async def show_image(message: types.Message):
    try:
        async with dp.current_state().proxy() as data:
            image_path = os.path.join(data['image_dir'], f"{data['current_image']}.jpg")
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Изображение {image_path} не найдено")
            # Храним message_id для последующего удаления
            async with dp.current_state().proxy() as data:
                data['message_id'] = (await message.answer_photo(types.InputFile(image_path), 
                                                                  caption=f"{data['current_image']} / {data['total_images']}", 
                                                                  reply_markup=get_nav_keyboard(data['current_image'], data['total_images'])))['message_id']
    except Exception as e:
        logger.error(f"Ошибка при показе изображения: {e}")

#<<<--Обработчики пагинаций и отдельных функций-->>>
async def show_search_results_page(message, topics: list, page: int):
    """Показывает страницу с результатами поиска."""
    items_per_page = 7
    total_pages = (len(topics) + items_per_page - 1) // items_per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(topics))

    topics_text = "🔍 Результаты поиска:\n\n"
    for i in range(start_idx, end_idx):
        topics_text += f"{i + 1}. {topics[i]}\n"

    keyboard = InlineKeyboardMarkup(row_width=7)
    
    # Кнопки с номерами тем
    buttons = [
        InlineKeyboardButton(str(i + 1), callback_data=f"select_search_topic_{i + 1}")
        for i in range(start_idx, end_idx)
    ]
    keyboard.add(*buttons)

    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"search_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="search_current_page"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"search_page_{page+1}"))
    keyboard.row(*nav_buttons)

    # Кнопка "Назад"
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="search_back_to_main"))

    if isinstance(message, types.Message):
        await message.answer(topics_text, reply_markup=keyboard)
    elif isinstance(message, types.CallbackQuery):
        await message.message.edit_text(topics_text, reply_markup=keyboard)
async def show_topics_page(message: types.Message, topics: list, page: int):
    """Показывает страницу с темами."""
    items_per_page = 10
    total_pages = (len(topics) + items_per_page - 1) // items_per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(topics))

    topics_text = "📚 Доступные темы:\n\n"
    for i in range(start_idx, end_idx):
        topics_text += f"{i + 1}. {topics[i]}\n"

    keyboard = InlineKeyboardMarkup(row_width=5)
    
    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="current_page"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"page_{page+1}"))
    keyboard.row(*nav_buttons)

    # Кнопки с номерами тем
    buttons = []
    for i in range(start_idx, end_idx):
        topic_number = str(i + 1)
        buttons.append(InlineKeyboardButton(topic_number, callback_data=f"select_topic_{topic_number}"))
    keyboard.add(*buttons)

    # Кнопка "Назад"
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main"))

    keyboard.add(InlineKeyboardButton("🔍 Поиск темы", callback_data="show_search_hint"))

    await message.answer(topics_text, reply_markup=keyboard)
def get_nav_keyboard(current_image, total_images):
    try:
        keyboard = types.InlineKeyboardMarkup()
        if current_image > 1:
            keyboard.insert(types.InlineKeyboardButton("⬅️", callback_data=f"nav:left:{current_image-1}"))
        if current_image < total_images:
            keyboard.insert(types.InlineKeyboardButton("➡️", callback_data=f"nav:right:{current_image+1}"))
        keyboard.insert(types.InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
        return keyboard
    except Exception as e:
        logger.error(f"Ошибка при генерации навигационной клавиатуры: {e}")
        return None

# Обработчики команд
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} вызвал команду /start")
    welcome_text = """
Добро пожаловать в наш бот по выбору проектов по дисциплине 'Обучение служением'!

Мы рады, что вы заинтересованы в применении своих знаний и навыков для служения другим.

Что предлагает наш бот? 

• Широкий выбор проектов по различным направлениям
• Возможность применения знаний на практике
• Шанс служить обществу и развивать свои навыки

Начинайте свой путь!
Нажмите /help что бы ознакомиться с инструкцией

Мы поможем вам найти идеальный проект!
"""

    try:
        await message.answer(welcome_text)
        logger.info(f"Отправлено приветственное сообщение пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.message_handler(commands=['contorg'])
async def cont_command(message: types.Message):
    cont_text="Что бы связаться с организатором перейдите по этой ссылке: [НАЖМИТЕ ТУТ](https://t.me/@balandina_vy)"
    try:
        await message.answer(cont_text, parse_mode="Markdown")
        logger.info(f"Отправлена команда CONTORG пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке CONTORG: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = """
ℹ️ Порядок действий:

1️⃣ Регистрация (/registr)
   • Введите ваше ФИО
   • Укажите группу обучения

2️⃣ Проверка профиля (/profile)
   • Убедитесь, что все данные указаны верно
   • Проверьте правильность выбранной темы

3️⃣ Примеры проектов (/example)
   • Ознакомьтесь с примерами проектов по дисциплине 'Обучение служением'

4️⃣ Ответы на частозадаваемые вопросы (/answer)
   • Получите ответы на часто задаваемые вопросы

👥 Связь с координатором (/contorg)
   • Обратитесь к координатору для получения помощи или консультации

5️⃣ Выбор темы (/topics)
   • Просмотрите доступные темы
   • Выберите интересующую вас тему
   • Подтвердите выбор
❗️ Важно: После выбора темы изменить её будет невозможно
"""

    try:
        await message.answer(help_text)
        logger.info(f"Отправлена команда HELP пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке HELP: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.message_handler(commands=['example'], state=None)
async def example_here(message: types.Message):
    try:
        async with dp.current_state().proxy() as data:
            data['image_dir'] = 'images/'
            data['current_image'] = 1
            data['total_images'] = len([name for name in os.listdir(data['image_dir']) if name.endswith('.jpg')]) 
            if data['total_images'] == 0:
                raise FileNotFoundError("Нет изображений в директории")
        
        await UserStates.ExampleState.set()
        await show_image(message)
    except FileNotFoundError as e:
        await message.answer("Нет изображений для показа.")
        logger.error(f"Ошибка: {e}")
    except Exception as e:
        await message.answer("Произошла ошибка. Пожалуйста, повторите попытку.")
        logger.error(f"Ошибка при обработке команды /example: {e}")
@dp.callback_query_handler(lambda call: call.data.startswith("nav") or call.data == "back_to_menu", state=UserStates.ExampleState)
async def navigate_images(callback: types.CallbackQuery, state: FSMContext):
    try:
        # Проверка возврата в главное меню
        if callback.data == "back_to_menu":
            await state.finish()
            await callback.message.delete() 
            await callback.answer()
            return

        # Получение направления и номера новой картинки
        direction, new_image = callback.data.split(":")[1:]
        
        # Работа с состоянием
        async with state.proxy() as data:
            data['current_image'] = int(new_image)
            image_path = os.path.join(data['image_dir'], f"{data['current_image']}.jpg")
            
            # Проверка существования файла
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Изображение {image_path} не найдено")
            
            # Обновление сообщения с новым изображением
            await callback.message.edit_media(
                types.InputMediaPhoto(
                    types.InputFile(image_path)
                ),
                reply_markup=get_nav_keyboard(data['current_image'], data['total_images'])
            )
        
        # Ответ на callback
        await callback.answer()

    except FileNotFoundError as e:
        await callback.message.answer("Изображение не найдено. Пожалуйста, повторите попытку.")
        logger.error(f"Ошибка: {e}")
    
    except BadRequest as e:
        await callback.message.answer("Ошибка при редактировании сообщения. Пожалуйста, повторите попытку.")
        logger.error(f"Ошибка при редактировании сообщения: {e}")
    
    except Exception as e:
        await callback.message.answer("Произошла ошибка. Пожалуйста, повторите попытку.")
        logger.error(f"Ошибка при навигации: {e}")

@dp.message_handler(commands=['registr'])
async def registration_command(message: types.Message):
    logger.info(f"Вызвана команда /registr пользователем {message.from_user.id}")
    if is_user_in_excel(message.from_user.id):
        await message.answer("❗️ Вы уже зарегистрированы.")
        return

    await message.answer("👤 Для регистрации введите ваше ФИО (Фамилия Имя Отчество)")
    await UserStates.FullnameState.set()
@dp.message_handler(state=UserStates.FullnameState)
async def process_fullname(message: types.Message, state: FSMContext):
    fullname = message.text.strip()
    
    if len(fullname.split()) != 3:
        await message.answer("❗️ Пожалуйста, введите полное ФИО (Фамилия Имя Отчество)")
        return

    try:
        add_user_to_excel(fullname, message.from_user.id)
        await message.answer("✅ ФИО успешно сохранено\n\nТеперь введите вашу группу (например: ПИ 1-1)")
        await UserStates.GroupState.set()
    except Exception as e:
        await message.answer("❌ Произошла ошибка при сохранении данных")
        logger.error(f"Ошибка при сохранении ФИО: {e}")
@dp.message_handler(state=UserStates.GroupState)
async def user_group_here(message: types.Message, state: FSMContext):
    """Обработчик ввода группы"""
    group = message.text.strip()
    
    if len(group.split()) != 2:
        await message.answer("❗️ Пожалуйста, введите группу в формате 'ПИ 1-1'")
        return

    try:
        if add_group_to_excel(message.from_user.id, group):
            await message.answer(
                "✅ Группа успешно добавлена!\n\n"
                "Теперь вы можете:\n"
                "- Посмотреть свой профиль: /profile\n"
                "- Ознакомиться с примерами проектов: /example\n"
                "- Обратиться к часто задаваемым вопросам: /answer"
            )
            await state.finish()
        else:
            await message.answer("❌ Ошибка: пользователь не найден в базе данных")
            await state.finish()
    except Exception as e:
        logger.error(f"Ошибка при сохранении группы: {e}")
        await message.answer("❌ Произошла ошибка при сохранении группы")
        await state.finish()

@dp.message_handler(commands=['profile'])
async def profile_command(message: types.Message):
    logger.info(f"Вызвана команда /profile пользователем {message.from_user.id}")
    try:
        df = pd.read_excel(EXCEL_FILE)
        user_data = df[df['TG_ID'] == message.from_user.id]
        
        if user_data.empty:
            await message.answer("❌ Вы не зарегистрированы! Используйте /registr для регистрации.")
            return
            
        user = user_data.iloc[0]
        profile_text = (
            "👤 Ваш профиль:\n\n"
            f"ФИО: {user['ФИО']}\n"
            f"Группа: {user['Группа'] if pd.notna(user['Группа']) else 'Не указана'}\n"
            f"Тема: {user['Тема'] if pd.notna(user['Тема']) else 'Не выбрана'}"
        )
        
        await message.answer(profile_text)
    except Exception as e:
        logger.error(f"Ошибка при получении профиля: {e}")
        await message.answer("❌ Произошла ошибка при получении данных профиля")

@dp.message_handler(commands=['topics'])
async def topics_command(message: types.Message, state: FSMContext):
    """Обработчик команды выбора темы."""
    try:
        if not is_user_in_excel(message.from_user.id):
            await message.answer("❌ Сначала необходимо зарегистрироваться! Используйте /registr")
            return

        if has_user_topic(message.from_user.id):
            await message.answer("❌ Вы уже выбрали тему. Изменить её невозможно.")
            return

        topics = await load_topics()
        if not topics:
            await message.answer("📢 На данный момент нет доступных тем.")
            return

        await UserStates.TopicState.set()
        await state.update_data(topics=topics)
        await show_topics_page(message, topics, 1)

    except Exception as e:
        logger.error(f"Ошибка в команде topics: {e}")
        await message.answer("❌ Произошла ошибка при загрузке тем.")
        await state.finish()
@dp.callback_query_handler(
    lambda c: (
        c.data.startswith('page_') or 
        c.data.startswith('select_topic_') or 
        c.data == "back_to_main" or 
        c.data == "show_search_hint"
    ), 
    state=UserStates.TopicState
)
async def process_topics_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик callback-запросов для тем."""
    try:
        data = await state.get_data()
        topics = data.get('topics', [])

        if callback.data == "back_to_main":
            await state.finish()
            return
        
        elif callback.data == 'show_search_hint':
            await callback.message.answer(
                "Если вы хотите найти конкретную тему, воспользуйтесь командой /search",
                reply_markup=ReplyKeyboardRemove()
            )
            await callback.answer()
            await state.finish()
            return

        if callback.data.startswith('page_'):
            page = int(callback.data.split('_')[1])
            await show_topics_page(callback.message, topics, page)
            await callback.answer()
            return

        if callback.data.startswith('select_topic_'):
            topic_number = int(callback.data.split('_')[2])
            topic_index = topic_number - 1

            if 0 <= topic_index < len(topics):
                selected_topic = topics[topic_index]
                
                team_keyboard = InlineKeyboardMarkup()
                team_keyboard.add(
                    InlineKeyboardButton("Да", callback_data=f"has_team_{topic_index}"),
                    InlineKeyboardButton("Нет", callback_data=f"no_team_{topic_index}")
                )

                await callback.message.edit_text(
                    f"Вы выбрали тему:\n{selected_topic}\n\nУ вас есть команда?",
                    reply_markup=team_keyboard
                )
            else:
                await callback.answer("❌ Некорректный номер темы")

    except Exception as e:
        logger.error(f"Ошибка при обработке callback темы: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")
        
@dp.callback_query_handler(lambda c: c.data.startswith(('has_team_', 'no_team_')), state=UserStates.TopicState)
async def process_team_response(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик ответа о наличии команды"""
    try:
        data = await state.get_data()
        topics = data.get('topics', [])
        topic_index = int(callback.data.split('_')[2])
        selected_topic = topics[topic_index]
        user_id = callback.from_user.id
        
        user_info = get_user_info(user_id) 
        if not user_info:
            await callback.answer("Ошибка получения информации о пользователе")
            return

        if callback.data.startswith('has_team_'):
            if await add_topic_to_user(user_id, selected_topic):
                    await remove_topic_from_file(selected_topic)
                    await callback.message.edit_text(
                        f"✅ Тема успешно забронирована!\n"
                        f"📌 Ваша тема: {selected_topic}"
                    )
            else:
                await callback.message.edit_text("❌ Ошибка при бронировании темы")
        
        else:  # no_team
            user_data = {
                'tg_id': user_id,
                'full_name': user_info['full_name'],
                'group': user_info['group'],
                'selected_topic': selected_topic
            }
            
            if add_to_alone_file(user_data):
                if await add_topic_to_user(user_id, selected_topic):
                    await callback.message.edit_text(
                        f"✅ Тема успешно забронирована!\n"
                        f"📌 Ваша тема: {selected_topic}\n"
                        f"ℹ️ Вы добавлены в список одиночных участников"
                    )
                    
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🆕 Новый одиночный участник!\n"
                        f"TG ID: {user_id}\n"
                        f"ФИО: {user_info['full_name']}\n"
                        f"Группа: {user_info['group']}\n"
                        f"Выбранная тема: {selected_topic}"
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при бронировании темы")
            else:
                await callback.message.edit_text("❌ Ошибка при добавлении в список одиночных участников")

        await state.finish()

    except Exception as e:
        logger.error(f"Ошибка при обработке ответа о команде: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при обработке запроса")
        await state.finish()

@dp.message_handler(commands=['answer'])
async def answer_command(message: types.Message, state: FSMContext):
    """Обработчик команды просмотра вопросов и ответов."""
    try:
        questions = await read_questions_from_file('answer.txt')
        if not questions:
            await message.answer("📢 На данный момент нет доступных вопросов и ответов.")
            return

        await UserStates.AnswerState.set()
        await state.update_data(questions=questions)
        await message.delete()  # Удаляем предыдущее сообщение
        await show_questions_page(message, questions, 1)

    except Exception as e:
        logger.error(f"Ошибка в команде answer: {e}")
        await message.answer("❌ Произошла ошибка при загрузке вопросов.")
        await state.finish()
async def show_questions_page(message: types.Message, questions: list, page: int):
    """Показывает страницу с вопросами и ответами."""
    items_per_page = 3
    total_pages = (len(questions) + items_per_page - 1) // items_per_page
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(questions))

    questions_text = "📚 Часто задаваемые вопросы:\n\n"
    questions_text += "Если вы хотите задать свой вопрос, воспользуйтесь командой /contorg\n\n"
    
    for i in range(start_idx, end_idx):
        q, a = questions[i]
        questions_text += f"❓ Вопрос: {q}\n💬 Ответ: {a}\n\n{'─' * 30}\n\n"

    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️", callback_data=f"answer_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="current_page"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️", callback_data=f"answer_page_{page+1}"))
    keyboard.row(*nav_buttons)

    # Кнопка "Назад"
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_main_from_answers"))

    # Удаляем предыдущее сообщение перед отправкой нового
    try:
        await message.delete()
    except:
        pass  # Если сообщение уже удалено, игнорируем ошибку

    # Отправляем новое сообщение
    msg = await message.answer(questions_text, reply_markup=keyboard)

    # Обновляем сообщение при навигации
    @dp.callback_query_handler(lambda c: c.data.startswith('answer_page_') or c.data == "back_to_main_from_answers", state=UserStates.AnswerState)
    async def process_answer_callback(callback: types.CallbackQuery, state: FSMContext):
        """Обработчик callback-запросов для вопросов и ответов."""
        try:
            data = await state.get_data()
            questions = data.get('questions', [])

            if callback.data == "back_to_main_from_answers":
                await state.finish()
                return

            if callback.data.startswith('answer_page_'):
                page = int(callback.data.split('_')[2])
                await show_questions_page(callback.message, questions, page)
                await callback.answer()
                return

        except Exception as e:
            logger.error(f"Ошибка при обработке callback ответов: {e}")
            await callback.answer("❌ Произошла ошибка при обработке запроса")
            await state.finish()

@dp.message_handler(commands=['search'])
async def search_command(message: types.Message, state: FSMContext):
    """Обработчик команды поиска тем по ключевым словам."""
    try:
        user_id = message.from_user.id

        if not is_user_in_excel(user_id):
            await message.answer("❌ Сначала необходимо зарегистрироваться! Используйте /registr")
            return

        if has_user_topic(user_id):
            await message.answer("❌ У вас уже есть выбранная тема. Вы не можете использовать поиск.")
            return

        await message.answer("Введите ключевые слова для поиска тем (разделите их пробелами):")
        await UserStates.SearchState.set()

    except Exception as e:
        logger.error(f"Ошибка в команде search: {e}")
        await message.answer("❌ Произошла ошибка при обработке команды.")
        await state.finish()
@dp.callback_query_handler(lambda c: c.data.startswith('search_page_') or c.data.startswith('select_search_topic_') or c.data == "search_back_to_main", state=UserStates.SearchState)
async def process_search_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик callback-запросов для результатов поиска."""
    try:
        if callback.data == "search_back_to_main":
            await callback.message.delete()
            await state.finish()
            return

        if has_user_topic(callback.from_user.id):
            await callback.message.edit_text("❌ У вас уже есть выбранная тема. Поиск отменен.")
            await state.finish()
            return

        data = await state.get_data()
        topics = data.get('topics', [])

        if callback.data.startswith('search_page_'):
            page = int(callback.data.split('_')[2])
            await show_search_results_page(callback, topics, page)
            await callback.answer()
        elif callback.data.startswith('select_search_topic_'):
            topic_number = int(callback.data.split('_')[3])
            topic_index = topic_number - 1
            if 0 <= topic_index < len(topics):
                selected_topic = topics[topic_index]
                
                # Создаем клавиатуру для вопроса о команде
                team_keyboard = InlineKeyboardMarkup()
                team_keyboard.row(
                    InlineKeyboardButton("Да", callback_data=f"search_has_team_{topic_index}"),
                    InlineKeyboardButton("Нет", callback_data=f"search_no_team_{topic_index}")
                )

                await callback.message.edit_text(
                    f"Вы выбрали тему:\n{selected_topic}\n\nУ вас есть команда?",
                    reply_markup=team_keyboard
                )
            else:
                await callback.answer("❌ Некорректный номер темы")
        else:
            await callback.answer("Неизвестное действие")

    except Exception as e:
        logger.error(f"Ошибка при обработке callback поиска: {e}")
        await callback.answer("Произошла ошибка при обработке запроса")
@dp.callback_query_handler(lambda c: c.data.startswith(('search_has_team_', 'search_no_team_')), state=UserStates.SearchState)
async def process_search_team_response(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик ответа о наличии команды для найденной темы"""
    try:
        if has_user_topic(callback.from_user.id):
            await callback.message.edit_text("❌ У вас уже есть выбранная тема. Операция отменена.")
            await state.finish()
            return

        data = await state.get_data()
        topics = data.get('topics', [])
        topic_index = int(callback.data.split('_')[3])
        selected_topic = topics[topic_index]
        user_id = callback.from_user.id
        
        user_info = get_user_info(user_id)
        if not user_info:
            await callback.answer("Ошибка получения информации о пользователе")
            return

        if callback.data.startswith('search_has_team_'):
            if await add_topic_to_user(user_id, selected_topic):
                await remove_topic_from_file(selected_topic)
                await callback.message.edit_text(
                    f"✅ Тема успешно забронирована!\n"
                    f"📌 Ваша тема: {selected_topic}"
                )
            else:
                await callback.message.edit_text("❌ Ошибка при бронировании темы")
        
        else:  # search_no_team
            user_data = {
                'tg_id': user_id,
                'full_name': user_info['full_name'],
                'group': user_info['group'],
                'selected_topic': selected_topic
            }
            
            if add_to_alone_file(user_data):
                if await add_topic_to_user(user_id, selected_topic):
                    await callback.message.edit_text(
                        f"✅ Тема успешно забронирована!\n"
                        f"📌Ваша тема: {selected_topic}\n"
                        f"ℹ️ Вы добавлены в список одиночных участников"
                    )
                    
                    await bot.send_message(
                        ADMIN_CHAT_ID,
                        f"🆕 Новый одиночный участник (через поиск)!\n"
                        f"TG ID: {user_id}\n"
                        f"ФИО: {user_info['full_name']}\n"
                        f"Группа: {user_info['group']}\n"
                        f"Выбранная тема: {selected_topic}"
                    )
                else:
                    await callback.message.edit_text("❌ Ошибка при бронировании темы")
            else:
                await callback.message.edit_text("❌ Ошибка при добавлении в список одиночных участников")

        await state.finish()

    except Exception as e:
        logger.error(f"Ошибка при обработке ответа о команде (поиск): {e}")
        await callback.message.edit_text("❌ Произошла ошибка при обработке запроса")
        await state.finish()
@dp.message_handler(state=UserStates.SearchState)
async def process_search_keywords(message: types.Message, state: FSMContext):
    """Обработчик ввода ключевых слов для поиска."""
    try:
        if has_user_topic(message.from_user.id):
            await message.answer("❌ У вас уже есть выбранная тема. Поиск отменен.")
            await state.finish()
            return

        keywords = message.text.split()
        if not keywords:
            await message.answer("❌ Вы не ввели ключевые слова. Попробуйте еще раз.")
            return

        matching_topics = await find_topics_by_keywords(keywords)
        if not matching_topics:
            await message.answer("📢 По вашему запросу не найдено тем.")
            await state.finish()
            return

        await state.update_data(topics=matching_topics)
        await show_search_results_page(message, matching_topics, 1)

    except Exception as e:
        logger.error(f"Ошибка при обработке ключевых слов: {e}")
        await message.answer("❌ Произошла ошибка при поиске тем.")
        await state.finish()    

#<<--Обработчик неизвестной команды-->>
@dp.message_handler(lambda message: message.text.startswith('/'))
async def unknown_command(message: types.Message):
    command_info = message.get_command_info()
    if command_info:
        command = command_info.command
        if not dp.message_handlers.get(command, None):
            await message.answer("❌ Неизвестная команда...\nИспользуйте /help для просмотра списка доступных команд.")
            logger.warning(f"Пользователь {message.from_user.id} ввел неизвестную команду: {command}")
    else:
        logger.info(f"Пользователь {message.from_user.id} отправил сообщение, начинающееся с '/', но без команды: {message.text}")

#<<---До отправки команды старт--->
async def on_startup(_):
    try:
        create_excel_file()  
        await set_commands(bot)  
        logger.info("Бот запущен")
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {e}")

#<<---Запуск бота--->>
if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup) 
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
