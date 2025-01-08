from aiogram import Router, types
from aiogram.filters import Command

# Initialize Router
router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    """
    Handles the /start command.
    """
    welcome_text = (
        "👋 Вітаю, {username}!\n\n"
        "Я ваш юридичний помічник. Ось що я можу:\n"
        "1️⃣ Юридичний тренер.\n"
        "2️⃣ Словник юридичних термінів.\n"
        "3️⃣ Правова база даних.\n"
        "4️⃣ Підготовка до іспитів.\n\n"
        "Натисніть /menu, щоб почати!"
    )
    await message.answer(
        welcome_text.format(username=message.from_user.first_name or "користувачу")
    )
