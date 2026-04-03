import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatMemberHandler
from config import BOT_TOKEN
import database

from handlers import user_commands, admin_commands, message_tracker, member_updates

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

import os
import asyncio
from aiohttp import web

async def web_server():
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="Bot is running!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", "8080"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Web server started on port {port}")

async def error_handler(update, context):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def post_init(application: Application):
    try:
        await database.init_db()
        asyncio.create_task(web_server())
        logger.info("Bot initialized.")
    except Exception as e:
        logger.critical(f"Initialization error (DB or Web): {e}", exc_info=True)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in the environment or .env file.")
        return

    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Register User Commands
    application.add_handler(CommandHandler("start", user_commands.start_command))
    application.add_handler(CommandHandler("verify", user_commands.verify_command))
    application.add_handler(CommandHandler("profile", user_commands.profile_command))
    application.add_handler(CommandHandler("myxp", user_commands.myxp_command))
    application.add_handler(CommandHandler("invites", user_commands.invites_command))
    application.add_handler(CommandHandler("leaderboard", user_commands.leaderboard_command))
    application.add_handler(CommandHandler("chatrank", user_commands.chatrank_command))
    application.add_handler(CommandHandler("rules", user_commands.rules_command))
    application.add_handler(CommandHandler("status", user_commands.status_command))
    application.add_handler(CommandHandler("help", user_commands.help_command))

    # Register Admin Commands
    application.add_handler(CommandHandler("approve", admin_commands.approve_command))
    application.add_handler(CommandHandler("remove", admin_commands.remove_command))
    application.add_handler(CommandHandler("broadcast", admin_commands.broadcast_command))
    application.add_handler(CommandHandler("end_event", admin_commands.end_event_command))
    application.add_handler(CommandHandler("participants", admin_commands.participants_command))
    
    # Register Group Chat Member Updates (leaving group)
    application.add_handler(ChatMemberHandler(member_updates.track_chats_member_updates, ChatMemberHandler.CHAT_MEMBER))
    
    # Register Message Tracking (XP/Quizzes)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_tracker.handle_message))
    
    application.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    try:
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"FATAL ERROR: {e}", exc_info=True)

if __name__ == '__main__':
    main()
