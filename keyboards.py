from aiogram.types import InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup

def create_pagination_keyboard(current_page, total_pages, callback_prefix="page_"):
    """Создает клавиатуру пагинации."""
    keyboard = InlineKeyboardMarkup(row_width=3)
    buttons = []

    if current_page > 1:
        buttons.append(InlineKeyboardButton("⬅️", callback_data=f"{callback_prefix}{current_page - 1}"))

    buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="current_page"))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton("➡️", callback_data=f"{callback_prefix}{current_page + 1}"))

    keyboard.add(*buttons)
    return keyboard


def create_topic_selection_keyboard(topics, page, items_per_page=10):
    """Создает клавиатуру для выбора темы с пагинацией"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(topics))
    
    # Добавляем кнопки с темами
    for i in range(start_idx, end_idx):
        keyboard.add(InlineKeyboardButton(
            text=topics[i],
            callback_data=f"topic_{i+1}"
        ))
    
    # Добавляем кнопки навигации
    navigation = []
    if page > 1:
        navigation.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
    if end_idx < len(topics):
        navigation.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
    
    if navigation:
        keyboard.row(*navigation)
    
    # Добавляем кнопку возврата в главное меню
    keyboard.add(InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_main"))
    
    return keyboard