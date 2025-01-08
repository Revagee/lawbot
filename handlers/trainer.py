from aiogram import Router, types
from aiogram import F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
import logging

logger = logging.getLogger(__name__)

router = Router()
router.name = 'trainer'

class TrainerStates(StatesGroup):
    waiting_for_answer = State()

questions = [
    {
        "question": "Яке джерело права є основним в Україні?",
        "options": [
            "Конституція України",
            "Судовий прецедент",
            "Міжнародні угоди",
            "Звичаєве право"
        ],
        "correct": 0,
        "explanation": "Конституція України є основним джерелом права в Україні та має найвищу юридичну силу."
    },
    {
        "question": "Що таке юридична особа?",
        "options": [
            "Фізична особа з правами",
            "Організація, що має права і обов'язки",
            "Державний орган",
            "Приватний підприємець"
        ],
        "correct": 1,
        "explanation": "Юридична особа - це організація, яка має відокремлене майно, може від свого імені набувати майнових і особистих немайнових прав і нести обов'язки."
    },
    {
        "question": "Який орган здійснює конституційне судочинство в Україні?",
        "options": [
            "Верховний Суд",
            "Конституційний Суд України",
            "Вищий антикорупційний суд",
            "Верховна Рада України"
        ],
        "correct": 1,
        "explanation": "Конституційний Суд України є єдиним органом конституційної юрисдикції в Україні."
    },
    {
        "question": "Яка форма державного правління в Україні?",
        "options": [
            "Президентська республіка",
            "Парламентська республіка",
            "Змішана республіка",
            "Конституційна монархія"
        ],
        "correct": 2,
        "explanation": "Україна є змішаною (парламентсько-президентською) республікою."
    },
    {
        "question": "Який термін повноважень Президента України?",
        "options": [
            "4 роки",
            "5 років",
            "6 років",
            "7 років"
        ],
        "correct": 1,
        "explanation": "Згідно з Конституцією України, Президент України обирається строком на 5 років."
    },
    {
        "question": "Хто є джерелом влади в Україні згідно з Конституцією?",
        "options": [
            "Президент",
            "Верховна Рада",
            "Народ України",
            "Кабінет Міністрів"
        ],
        "correct": 2,
        "explanation": "Згідно зі статтею 5 Конституції України, носієм суверенітету і єдиним джерелом влади в Україні є народ."
    },
    {
        "question": "З якого віку настає кримінальна відповідальність в Україні?",
        "options": [
            "З 14 років",
            "З 16 років",
            "З 18 років",
            "З 21 року"
        ],
        "correct": 1,
        "explanation": "Загальний вік кримінальної відповідальності в Україні - 16 років, хоча за деякі тяжкі злочини відповідальність настає з 14 років."
    },
    {
        "question": "Який орган приймає закони в Україні?",
        "options": [
            "Президент України",
            "Верховна Рада України",
            "Кабінет Міністрів України",
            "Конституційний Суд України"
        ],
        "correct": 1,
        "explanation": "Єдиним органом законодавчої влади в Україні є парламент - Верховна Рада України."
    }
]

def generate_keyboard(options):
    """
    Створює клавіатуру з варіантами відповідей
    """
    buttons = [[KeyboardButton(text=option)] for option in options]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

async def start_training(message: types.Message, state: FSMContext):
    """
    Початок тренування
    """
    logger.info(f"Starting training for user {message.from_user.id}")
    await state.update_data(current_question=0, correct_answers=0, user_answers=[])
    question = questions[0]
    
    await message.answer(
        f"❓ {question['question']}",
        reply_markup=generate_keyboard(question["options"])
    )
    await state.set_state(TrainerStates.waiting_for_answer)
    logger.info(f"Training started for user {message.from_user.id}, first question sent")

@router.message(Command("trainer"))
async def cmd_start_trainer(message: types.Message, state: FSMContext):
    await start_training(message, state)

@router.message(F.text == "Юридичний тренер")
async def button_start_trainer(message: types.Message, state: FSMContext):
    await start_training(message, state)

@router.message(TrainerStates.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Перевірка відповіді користувача
    """
    data = await state.get_data()
    current_question = data.get("current_question", 0)
    correct_answers = data.get("correct_answers", 0)
    user_answers = data.get("user_answers", [])
    question = questions[current_question]

    # Зберігаємо відповідь користувача
    user_answers.append({
        "question": question["question"],
        "user_answer": message.text,
        "correct_answer": question["options"][question["correct"]],
        "is_correct": message.text == question["options"][question["correct"]]
    })

    # Перевіряємо відповідь
    is_correct = message.text == question["options"][question["correct"]]
    if is_correct:
        correct_answers += 1
        await message.answer("✅ Правильно!\n\n" + question["explanation"])
    else:
        await message.answer(
            f"❌ Неправильно!\nПравильна відповідь: {question['options'][question['correct']]}\n\n" + 
            question["explanation"]
        )

    # Переходимо до наступного питання
    current_question += 1
    await state.update_data(
        current_question=current_question, 
        correct_answers=correct_answers,
        user_answers=user_answers
    )

    if current_question < len(questions):
        next_question = questions[current_question]
        await message.answer(
            f"❓ {next_question['question']}",
            reply_markup=generate_keyboard(next_question["options"])
        )
    else:
        # Формуємо підсумок
        percentage = (correct_answers / len(questions)) * 100
        summary = [
            f"🎉 Вітаємо! Ви завершили тренування!\n",
            f"📊 Ваш результат: {correct_answers} правильних відповідей з {len(questions)}",
            f"Відсоток правильних відповідей: {percentage:.1f}%\n",
            "📝 Огляд відповідей:\n"
        ]
        
        # Додаємо всі питання та відповіді
        for i, answer in enumerate(user_answers, 1):
            summary.append(f"\n{i}. {answer['question']}")
            summary.append(f"❔ Ваша відповідь: {answer['user_answer']}")
            if answer['is_correct']:
                summary.append("✅ Правильно!")
            else:
                summary.append(f"❌ Неправильно. Правильна відповідь: {answer['correct_answer']}")

        summary.append("\nНатисніть /menu, щоб повернутися до головного меню.")

        # Відправляємо підсумок
        await message.answer(
            "\n".join(summary),
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="/menu")]],
                resize_keyboard=True
            )
        )
        await state.clear()