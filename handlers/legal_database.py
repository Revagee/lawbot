from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
import logging
from bs4 import BeautifulSoup
import re
from typing import List, Tuple, Optional, Dict
from aiogram.filters import Command
from aiogram import F

# Configure logging
logger = logging.getLogger(__name__)

# Initialize router
router = Router()
router.name = 'legal_database'

# Define FSM states
class DatabaseStates(StatesGroup):
    selecting_code = State()
    waiting_for_search_term = State()

# Cache for articles to avoid repeated requests
article_cache: Dict[str, Dict[str, str]] = {}

# Define legal sources with their URLs
LEGAL_SOURCES = {
    "criminal": {
        "name": "Кримінальний кодекс України",
        "url": "https://zakon.rada.gov.ua/laws/show/2341-14#Text"
    },
    "civil": {
        "name": "Цивільний кодекс України",
        "url": "https://zakon.rada.gov.ua/laws/show/435-15#Text"
    },
    "administrative": {
        "name": "Кодекс України про адміністративні правопорушення",
        "url": "https://zakon.rada.gov.ua/laws/show/80731-10#Text"
    }
}

def generate_main_keyboard() -> ReplyKeyboardMarkup:
    """Generate main keyboard with basic options"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="↩️ Назад")],
            [KeyboardButton(text="/menu")]
        ],
        resize_keyboard=True
    )

def generate_codes_keyboard() -> ReplyKeyboardMarkup:
    """Generate keyboard with available legal codes"""
    keyboard = [[KeyboardButton(text=source["name"])] for source in LEGAL_SOURCES.values()]
    keyboard.append([KeyboardButton(text="↩️ Назад")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

async def fetch_and_parse_code(session: aiohttp.ClientSession, code_id: str) -> Dict[str, str]:
    """Fetch and parse entire legal code, storing articles in cache"""
    if code_id in article_cache:
        return article_cache[code_id]
        
    try:
        source = LEGAL_SOURCES[code_id]
        async with session.get(source["url"]) as response:
            if response.status != 200:
                return {}
                
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all article containers
            articles = {}
            
            # Find all text that matches article pattern
            for text in soup.stripped_strings:
                # Match article headers
                article_match = re.match(r'Стаття\s+(\d+)[.\s](.+)', text)
                if article_match:
                    article_num = article_match.group(1)
                    content = article_match.group(2)
                    
                    # Get the parent element
                    parent = None
                    for element in soup.find_all(text=re.compile(f'Стаття\\s+{article_num}[.\\s]')):
                        parent = element.parent
                        if parent:
                            break
                    
                    if parent:
                        # Get all text until next article
                        article_content = []
                        current = parent
                        while current:
                            if current.name == 'div' and re.search(r'Стаття\s+\d+[.\s]', current.get_text()):
                                if not article_content:  # First div is our article
                                    article_content.append(current.get_text())
                                break
                            article_content.append(current.get_text())
                            current = current.next_sibling
                            
                        full_content = ' '.join(article_content)
                        full_content = re.sub(r'\s+', ' ', full_content).strip()
                        articles[article_num] = full_content
            
            article_cache[code_id] = articles
            return articles
                    
    except Exception as e:
        logger.error(f"Error fetching code: {e}")
        return {}

async def search_legal_content(code_id: str, search_term: str) -> List[Tuple[str, str]]:
    """Search for legal content by article number or keywords"""
    async with aiohttp.ClientSession() as session:
        try:
            # First, fetch and parse the entire code if not cached
            articles = await fetch_and_parse_code(session, code_id)
            
            if search_term.isdigit():
                # Direct article number search
                if search_term in articles:
                    return [(search_term, articles[search_term])]
                return []
            else:
                # Keyword search
                results = []
                for article_num, content in articles.items():
                    if search_term.lower() in content.lower():
                        results.append((article_num, content))
                        if len(results) >= 5:  # Limit to 5 results
                            break
                return results
                
        except Exception as e:
            logger.error(f"Error in search_legal_content: {e}")
            
    return []

@router.message(Command("database"))
async def start_database(message: types.Message, state: FSMContext):
    """Handle the /database command"""
    await select_code(message, state)

@router.message(F.text == "База даних")
async def button_database(message: types.Message, state: FSMContext):
    """Handle the 'База даних' button press"""
    await select_code(message, state)

async def select_code(message: types.Message, state: FSMContext):
    """Show available legal codes for selection"""
    await message.answer(
        "Оберіть кодекс для пошуку:",
        reply_markup=generate_codes_keyboard()
    )
    await state.set_state(DatabaseStates.selecting_code)

@router.message(DatabaseStates.selecting_code)
async def handle_code_selection(message: types.Message, state: FSMContext):
    """Handle legal code selection"""
    if message.text == "↩️ Назад":
        await message.answer("Головне меню", reply_markup=generate_main_keyboard())
        await state.clear()
        return

    selected_doc = None
    for code_id, source in LEGAL_SOURCES.items():
        if message.text == source["name"]:
            selected_doc = code_id
            break

    if not selected_doc:
        await message.answer(
            "Будь ласка, оберіть кодекс зі списку.",
            reply_markup=generate_codes_keyboard()
        )
        return

    await state.update_data(selected_document=selected_doc)
    await message.answer(
        "Введіть номер статті або ключові слова для пошуку:",
        reply_markup=generate_main_keyboard()
    )
    await state.set_state(DatabaseStates.waiting_for_search_term)

@router.message(DatabaseStates.waiting_for_search_term)
async def handle_search(message: types.Message, state: FSMContext):
    """Handle search queries"""
    if message.text == "↩️ Назад":
        await select_code(message, state)
        return
        
    data = await state.get_data()
    doc_id = data.get("selected_document")
    
    if not doc_id or doc_id not in LEGAL_SOURCES:
        await message.answer(
            "Помилка пошуку. Спробуйте знову.",
            reply_markup=generate_main_keyboard()
        )
        await state.clear()
        return

    await message.answer("🔍 Шукаю інформацію...")
    
    try:
        search_term = message.text.strip()
        results = await search_legal_content(doc_id, search_term)
        
        if results:
            response = f"Результати пошуку в {LEGAL_SOURCES[doc_id]['name']}:\n\n"
            for article_num, content in results:
                response += f"Стаття {article_num}:\n{content}\n\n"
        else:
            response = f"За вашим запитом '{search_term}' нічого не знайдено в {LEGAL_SOURCES[doc_id]['name']}."
            
        if len(response) > 4096:
            for x in range(0, len(response), 4096):
                await message.answer(response[x:x+4096])
        else:
            await message.answer(response, reply_markup=generate_main_keyboard())
            
    except Exception as e:
        logger.error(f"Error in handle_search: {e}")
        await message.answer(
            "Виникла помилка при пошуку. Спробуйте знову.",
            reply_markup=generate_main_keyboard()
        )
    
    await state.clear()