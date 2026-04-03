import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Event flags
EVENT_ACTIVE = True
