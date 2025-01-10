from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

router = Router()
router.name = 'menu'

def get_main_keyboard():
    """Create main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Юридичний тренер")],
            [KeyboardButton(text="Словник")],
            [KeyboardButton(text="База даних")],
            [KeyboardButton(text="Підготовка до іспитів")],
        ],
        resize_keyboard=True
    )

@router.message(Command("menu"))
@router.message(lambda m: m.text in ["Повернутися до меню", "↩️ Повернутися до меню"])
async def menu_handler(message: types.Message):
    """Handle all returns to main menu"""
    await message.answer("Оберіть розділ:", reply_markup=get_main_keyboard())
