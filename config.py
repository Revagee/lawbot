import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")
