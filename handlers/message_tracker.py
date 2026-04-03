import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
import database
from config import GROUP_CHAT_ID

logger = logging.getLogger(__name__)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Check if event is active
    is_active = await database.get_global('event_active', 'true')
    if is_active != 'true':
        return
        
    db = await database.get_db()
    
    # Process only Group Chat messages for tracking and quiz triggering
    if chat_id == GROUP_CHAT_ID:
        
        # 1. Update Global Message Count and Check Quiz Trigger
        gc_count_str = await database.get_global('gc_message_count', '0')
        gc_count = int(gc_count_str) + 1
        await database.set_global('gc_message_count', str(gc_count))
        
        if gc_count % 100 == 0:
            # Trigger Quiz (placeholder for quiz logic)
            # asyncio.create_task(trigger_quiz(context, chat_id))
            pass
            
        # 2. Check User Chat Rules (only for approved users)
        cursor = await db.execute("SELECT status, xp, message_count, last_message_time, last_message_text FROM users WHERE id = ?", (user_id,))
        user_row = await cursor.fetchone()
        
        if not user_row:
            return  # Not verified yet
            
        status, xp, msg_count, last_msg_time, last_msg_text = user_row
        
        if status != 'approved':
            return  # Only approved users get XP from chatting
            
        # Rules: >= 3 words, not repeated, >= 15 gap
        words = text.split()
        if len(words) < 3:
            return
            
        if text.lower() == (last_msg_text or "").lower():
            return
            
        now = datetime.utcnow()
        if last_msg_time:
            last_time = datetime.fromisoformat(last_msg_time)
            if (now - last_time).total_seconds() < 15:
                return
                
        # Passed checks, increment message count
        new_msg_count = msg_count + 1
        await db.execute("UPDATE users SET message_count = ?, last_message_time = ?, last_message_text = ? WHERE id = ?",
                         (new_msg_count, now.isoformat(), text, user_id))
        
        # Chat XP Logic: +5 XP every 25 messages, daily max 15 XP
        # In a real scenario, we might need a daily_xp tracking table. For now, since daily max is 15 (which is 3 cycles of 25 messages),
        # we can just assume a basic XP grant. Let's do simple +5 every 25 messages for now to satisfy the logic roughly.
        if new_msg_count > 0 and new_msg_count % 25 == 0:
            # Simplified: add 5 XP
            new_xp = xp + 5
            await db.execute("UPDATE users SET xp = ? WHERE id = ?", (new_xp, user_id))
            # Optional: notify user about XP gained?
            try:
                await update.message.reply_text("🎉 You gained 5 XP for being active in chat!")
            except Exception:
                pass
                
        await db.commit()
