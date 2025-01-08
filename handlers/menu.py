from aiogram import Router, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# Initialize Router properly
router = Router()
router.name = 'menu'

@router.message(Command("menu"))
async def menu_handler(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Юридичний тренер")],
            [KeyboardButton(text="Словник")],
            [KeyboardButton(text="База даних")],
            [KeyboardButton(text="Підготовка до іспитів")],
        ],
        resize_keyboard=True
    )
    await message.answer("Оберіть розділ:", reply_markup=keyboard)