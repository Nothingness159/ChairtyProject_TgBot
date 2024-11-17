from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import pandas as pd
import os
import logging
import aiofiles  
import asyncio
from keyboards import *
from aiogram.types import InlineKeyboardButton
import os
import pandas as pd
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton



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
BOT_TOKEN = "7753196829:AAE6G8mobolxxyA4ntnjfe4VX5VCCh9LGYI"
TOPICS_FILE = 'topics.txt'
ADMIN_CHAT_ID="857663686"
ALONE_FILE = 'alone.xlsx'

# --- Состояния FSM ---
class UserStates(StatesGroup):
    FullnameState = State()
    GroupState = State()
    TopicState = State()
    AnswerState = State()

# --- Функции для работы с Excel ---
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

async def add_topic_to_user(tg_id, topic):
    """Добавляет выбранную тему пользователю."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        if not df[df['TG_ID'] == tg_id].empty:
            df.loc[df['TG_ID'] == tg_id, 'Тема'] = topic
            df.to_excel(EXCEL_FILE, index=False)
            logger.info(f"Добавлена тема для пользователя {tg_id}: {topic}")
            
            # Асинхронный вызов remove_topic_from_file
            await remove_topic_from_file(topic)
            
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
    ]
    await bot.set_my_commands(commands)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Глобальный словарь для хранения тем
topics_dict = {}


# Обработчики команд

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} вызвал команду /start")
    welcome_text = """
👋 Добро пожаловать в нашего бота!

Чтобы начать, используйте команды:
- /help - для получения списка доступных команд.
- /registr - для регистрации.
- /topics - для выбора темы.
- /profile - для просмотра вашего профиля.
- /answer - для получения ответов на часто задаваемые вопросы.
"""
    try:
        await message.answer(welcome_text)
        logger.info(f"Отправлено приветственное сообщение пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке приветственного сообщения: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    help_text = """
ℹ️ Порядок действий:

1️⃣ Регистрация (/registr)
   - Введите ваше ФИО
   - Укажите группу обучения

2️⃣ Выбор темы (/topics)
   - Просмотрите доступные темы
   - Выберите интересующую вас тему
   - Подтвердите выбор
❗️ Важно: После выбора темы изменить её будет невозможно

3️⃣ Проверка профиля (/profile)
   - Убедитесь, что все данные указаны верно
   - Проверьте правильность выбранной темы

4️⃣ Ответы на частозадаваемые вопросы (/answer)
    - Получите ответы на часто задаваемые вопросы
    - Связь с администрацией
"""

    try:
        await message.answer(help_text)
        logger.info(f"Отправлена команда HELP пользователю {message.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке HELP: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже.")

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
                "- Выбрать тему: /topics"
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

    await message.answer(topics_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('page_') or c.data.startswith('select_topic_') or c.data == "back_to_main", state=UserStates.TopicState)
async def process_topics_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик callback-запросов для тем."""
    try:
        data = await state.get_data()
        topics = data.get('topics', [])

        if callback.data == "back_to_main":
            await state.finish()
            await callback.message.edit_text("Вы вернулись в главное меню.")
            return

        if callback.data.startswith('page_'):
            page = int(callback.data.split('_')[1])
            await callback.message.edit_text("Загрузка...")
            await show_topics_page(callback.message, topics, page)
            await callback.answer()
            return

        if callback.data.startswith('select_topic_'):
            topic_number = int(callback.data.split('_')[2])
            topic_index = topic_number - 1

            if 0 <= topic_index < len(topics):
                selected_topic = topics[topic_index]
                
                # Создаем клавиатуру для вопроса о команде
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
        
        user_info = get_user_info(user_id)  # Функция получения информации о пользователе
        if not user_info:
            await callback.answer("Ошибка получения информации о пользователе")
            return

        if callback.data.startswith('has_team_'):
            
            # Если есть команда - просто бронируем тему
            if await add_topic_to_user(user_id, selected_topic):
                    await callback.message.edit_text(
                        f"✅ Тема успешно забронирована!\n"
                        f"📌 Ваша тема: {selected_topic}"
                    )
            else:
                await callback.message.edit_text("❌ Ошибка при бронировании темы")
        
        else:  # no_team
            # Добавляем в файл alone.xlsx и бронируем тему
            user_data = {
                'tg_id': user_id,
                'full_name': user_info['full_name'],
                'group': user_info['group'],
                'selected_topic': selected_topic
            }
            
            if add_to_alone_file(user_data):
                if add_topic_to_user(user_id, selected_topic):
                    await callback.message.edit_text(
                        f"✅ Тема успешно забронирована!\n"
                        f"📌 Ваша тема: {selected_topic}\n"
                        f"ℹ️ Вы добавлены в список одиночных участников"
                    )
                    
                    # Отправляем уведомление администратору
                    # Отправляем уведомление администратору
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
            'TG_ID': [user_data['tg_id']], 
            'Группа': [user_data['group']],
            'Тема': [user_data['selected_topic']]
        })


        df = pd.concat([df, new_row], ignore_index=True)


        df.to_excel('alone.xlsx', index=False)
        return True

    except Exception as e:
        logger.error(f"Ошибка при добавлении в alone.xlsx: {e}")
        return False


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
    questions_text += "Если вы хотите задать свой вопрос, обратитесь к админу @Nothingness105\n\n"
    
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

    await message.answer(questions_text, reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('answer_page_') or c.data == "back_to_main_from_answers", state=UserStates.AnswerState)
async def process_answer_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик callback-запросов для вопросов и ответов."""
    try:
        data = await state.get_data()
        questions = data.get('questions', [])

        if callback.data == "back_to_main_from_answers":
            await state.finish()
            await callback.message.edit_text("Вы вернулись в главное меню.")
            return

        if callback.data.startswith('answer_page_'):
            page = int(callback.data.split('_')[2])
            await callback.message.edit_text("Загрузка...")
            await show_questions_page(callback.message, questions, page)
            await callback.answer()
            return

    except Exception as e:
        logger.error(f"Ошибка при обработке callback ответов: {e}")
        await callback.answer("❌ Произошла ошибка при обработке запроса")
        await state.finish()

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

@dp.message_handler(lambda message: message.text.startswith('/'))
async def unknown_command(message: types.Message):
    command = message.get_command(pure=True)
    if not dp.has_handler_for(message.text):
        await message.answer("❌ Неизвестная команда...\nИспользуйте /help для просмотра списка доступных команд.")

@dp.errors_handler()
async def errors_handler(update, exception):
    logger.error(f"Произошла ошибка при обработке обновления {update}: {exception}")
    return True


async def on_startup(_):
    """Функция, которая выполняется при запуске бота."""
    try:
        create_excel_file()  # Создаем Excel файл, если он не существует
        await set_commands(bot)  # Устанавливаем команды бота
        logger.info("Бот запущен")
    except Exception as e:
        logger.error(f"Ошибка при инициализации: {e}")


if __name__ == '__main__':
    try:
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup) 
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")