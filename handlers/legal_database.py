from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from handlers.menu import menu_handler
import aiohttp
from bs4 import BeautifulSoup
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

router = Router()
router.name = 'legal_database'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache settings
article_cache: Dict[str, Dict] = {}
cache_timeout = timedelta(hours=6)

class DatabaseStates(StatesGroup):
    choosing_code = State()
    search_method = State()
    waiting_for_article_number = State()
    waiting_for_keyword = State()

LEGAL_CODES = {
    "Конституція України": {
        "id": "254к/96-вр",
        "url": "https://zakon.rada.gov.ua/laws/show/254%D0%BA/96-%D0%B2%D1%80/paran4175",
        "print_url": "https://zakon.rada.gov.ua/laws/show/254%D0%BA/96-%D0%B2%D1%80/print"
    },
    "Цивільний кодекс України": {
        "id": "435-15",
        "url": "https://zakon.rada.gov.ua/laws/show/435-15",
        "print_url": "https://zakon.rada.gov.ua/laws/show/435-15/print"
    },
    "Кримінальний кодекс України": {
        "id": "2341-14",
        "url": "https://zakon.rada.gov.ua/laws/show/2341-14",
        "print_url": "https://zakon.rada.gov.ua/laws/show/2341-14/print"
    },
    "Сімейний кодекс України": {
        "id": "2947-14",
        "url": "https://zakon.rada.gov.ua/laws/show/2947-14",
        "print_url": "https://zakon.rada.gov.ua/laws/show/2947-14/print"
    },
    "Кодекс законів про працю України": {
        "id": "322-08",
        "url": "https://zakon.rada.gov.ua/laws/show/322-08",
        "print_url": "https://zakon.rada.gov.ua/laws/show/322-08/print"
    }
}

async def fetch_page_content(url: str, attempt: int = 0) -> Optional[str]:
    """Fetch page content with retries and proper headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429 and attempt < 3:  # Too Many Requests
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    return await fetch_page_content(url, attempt + 1)
                else:
                    logger.error(f"Failed to fetch page: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Error fetching page: {str(e)}")
        return None

async def parse_articles(html_content: str) -> Dict[str, str]:
    """Parse articles from HTML content with improved accuracy"""
    soup = BeautifulSoup(html_content, 'html.parser')
    articles = {}

    try:
        # Find the main content container
        content = soup.find('div', class_='document-content') or \
                 soup.find('div', class_='txt') or \
                 soup.find('div', id='article')

        if not content:
            logger.error("Could not find content container")
            return {}

        current_article_num = None
        current_article_text = []

        for element in content.find_all(['p', 'div', 'span']):
            text = element.get_text(strip=True)
            if not text:
                continue

            # Check for article header
            article_match = re.match(r'Стаття\s+(\d+(?:[а-яі]|(?:\-\d+)?)?)', text)
            
            if article_match:
                # Save previous article if exists
                if current_article_num and current_article_text:
                    articles[current_article_num] = '\n'.join(current_article_text)
                
                # Start new article
                current_article_num = article_match.group(1)
                current_article_text = [text]
            elif current_article_num:
                # Add text to current article
                current_article_text.append(text)

        # Save last article
        if current_article_num and current_article_text:
            articles[current_article_num] = '\n'.join(current_article_text)

    except Exception as e:
        logger.error(f"Error parsing articles: {str(e)}")
        return {}

    return articles

async def fetch_and_parse_code(code_data: dict) -> Dict[str, str]:
    """Fetch and parse legal code with caching"""
    code_id = code_data['id']
    
    # Check cache
    if code_id in article_cache:
        cache_data = article_cache[code_id]
        if datetime.now() - cache_data['timestamp'] < cache_timeout:
            return cache_data['articles']

    # Try both print and regular URLs
    urls = [code_data['print_url'], code_data['url']]
    
    for url in urls:
        html_content = await fetch_page_content(url)
        if html_content:
            articles = await parse_articles(html_content)
            if articles:
                article_cache[code_id] = {
                    'timestamp': datetime.now(),
                    'articles': articles
                }
                return articles

    return {}

async def search_by_keyword(articles: Dict[str, str], keyword: str) -> List[str]:
    """Search articles by keyword with improved matching"""
    results = []
    search_words = keyword.lower().split()
    
    for article_num, content in articles.items():
        content_lower = content.lower()
        if all(word in content_lower for word in search_words):
            # Format the result
            formatted_content = content
            for word in search_words:
                pattern = re.compile(f'({word})', re.IGNORECASE)
                formatted_content = pattern.sub(r'*\1*', formatted_content)
            
            results.append(f"📑 Стаття {article_num}:\n\n{formatted_content}\n")

    return results

def create_keyboard(items: List[str], row_width: int = 1, include_back: bool = True) -> ReplyKeyboardMarkup:
    """Create a keyboard with given items"""
    keyboard = [[KeyboardButton(text=item)] for item in items]
    if include_back:
        keyboard.append([KeyboardButton(text="↩️ Повернутися до меню")])  # Standardized return text
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@router.message(Command("database"))
@router.message(F.text == "База даних")
async def start_database_search(message: types.Message, state: FSMContext):
    await message.answer(
        "Оберіть кодекс для пошуку:",
        reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
    )
    await state.set_state(DatabaseStates.choosing_code)

@router.message(DatabaseStates.choosing_code)
async def handle_code_selection(message: types.Message, state: FSMContext):
    if message.text == "↩️ Повернутися до меню":
        await state.clear()
        await menu_handler(message)
        return

    if message.text in LEGAL_CODES:
        await state.update_data(selected_code=message.text)
        await message.answer(
            "Оберіть метод пошуку:",
            reply_markup=create_keyboard(
                ["🔢 Пошук за номером статті", "🔍 Пошук за ключовим словом"]
            )
        )
        await state.set_state(DatabaseStates.search_method)
    else:
        await message.answer(
            "Будь ласка, оберіть кодекс із запропонованого списку:",
            reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
        )

@router.message(DatabaseStates.search_method)
async def handle_search_method(message: types.Message, state: FSMContext):
    if message.text == "↩️ Повернутися до меню":
        await message.answer(
            "Оберіть кодекс для пошуку:",
            reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
        )
        await state.set_state(DatabaseStates.choosing_code)
        return

    if message.text == "🔢 Пошук за номером статті":
        await message.answer(
            "Введіть номер статті:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(DatabaseStates.waiting_for_article_number)
    elif message.text == "🔍 Пошук за ключовим словом":
        await message.answer(
            "Введіть ключове слово або фразу для пошуку:",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(DatabaseStates.waiting_for_keyword)
    else:
        await message.answer(
            "Будь ласка, оберіть метод пошуку із запропонованих варіантів:",
            reply_markup=create_keyboard(
                ["🔢 Пошук за номером статті", "🔍 Пошук за ключовим словом"]
            )
        )

@router.message(DatabaseStates.waiting_for_article_number)
async def handle_article_number(message: types.Message, state: FSMContext):
    # Check if input is a valid article number
    if not re.match(r'^\d+$', message.text):
        await message.answer(
            "Будь ласка, введіть числовий номер статті."
        )
        return

    data = await state.get_data()
    code_name = data['selected_code']
    code_data = LEGAL_CODES[code_name]

    # Show loading message
    loading_msg = await message.answer("🔄 Шукаю статтю...")

    try:
        articles = await fetch_and_parse_code(code_data)
        
        # Try different variations of the article number
        article_found = False
        article_number = message.text
        variations = [
            article_number,
            f"{article_number}-1",
            f"{article_number}а",
            f"{article_number}б"
        ]

        for variation in variations:
            if variation in articles:
                article_found = True
                await loading_msg.delete()
                await message.answer(
                    f"📑 {articles[variation]}",
                    reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
                )
                break

        if not article_found:
            await loading_msg.delete()
            await message.answer(
                "❌ Статтю не знайдено. Перевірте номер та спробуйте ще раз.",
                reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
            )

    except Exception as e:
        logger.error(f"Error handling article number: {str(e)}")
        await loading_msg.delete()
        await message.answer(
            "❌ Виникла помилка при пошуку. Спробуйте пізніше.",
            reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
        )

    await state.set_state(DatabaseStates.choosing_code)

@router.message(DatabaseStates.waiting_for_keyword)
async def handle_keyword(message: types.Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer(
            "Будь ласка, введіть щонайменше 3 символи для пошуку."
        )
        return

    data = await state.get_data()
    code_name = data['selected_code']
    code_data = LEGAL_CODES[code_name]

    loading_msg = await message.answer("🔄 Шукаю статті...")

    try:
        articles = await fetch_and_parse_code(code_data)
        results = await search_by_keyword(articles, message.text)

        await loading_msg.delete()

        if results:
            # Split results into chunks to avoid message length limits
            chunk_size = 4000
            current_chunk = []
            current_length = 0

            for result in results:
                if current_length + len(result) > chunk_size:
                    # Send current chunk
                    await message.answer('\n'.join(current_chunk))
                    current_chunk = [result]
                    current_length = len(result)
                else:
                    current_chunk.append(result)
                    current_length += len(result)

            # Send remaining chunk
            if current_chunk:
                await message.answer(
                    '\n'.join(current_chunk),
                    reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
                )
        else:
            await message.answer(
                "❌ Нічого не знайдено за вашим запитом.",
                reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
            )

    except Exception as e:
        logger.error(f"Error handling keyword search: {str(e)}")
        await loading_msg.delete()
        await message.answer(
            "❌ Виникла помилка при пошуку. Спробуйте пізніше.",
            reply_markup=create_keyboard(list(LEGAL_CODES.keys()))
        )

    await state.set_state(DatabaseStates.choosing_code)