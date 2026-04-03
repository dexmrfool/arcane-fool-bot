import logging
from telegram import Update
from telegram.ext import ContextTypes
import database
from config import GROUP_CHAT_ID

logger = logging.getLogger(__name__)

async def track_chats_member_updates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tracks when someone leaves the GC for anti-cheat"""
    result = update.chat_member
    if not result:
        return
        
    if result.chat.id != GROUP_CHAT_ID:
        return

    # Checking if member left (status became left, kicked, or restricted)
    was_member = result.old_chat_member.status in ["member", "administrator", "creator", "restricted"]
    is_member = result.new_chat_member.status in ["member", "administrator", "creator", "restricted"]

    if was_member and not is_member:
        # User left the GC
        left_user_id = result.new_chat_member.user.id
        db = await database.get_db()
        
        # Find if this person was invited by someone
        cursor = await db.execute("SELECT id, referrer_user_id, status FROM invites WHERE invited_user_id = ?", (left_user_id,))
        invite_row = await cursor.fetchone()
        
        if invite_row:
            invite_id, referrer_id, invite_status = invite_row
            if invite_status == 'valid':
                # Invalidate invite and deduct 8 XP from referrer
                await db.execute("UPDATE invites SET status = 'invalid' WHERE id = ?", (invite_id,))
                
                referrer_cursor = await db.execute("SELECT xp FROM users WHERE id = ?", (referrer_id,))
                referrer_row = await referrer_cursor.fetchone()
                if referrer_row:
                    new_xp = max(0, referrer_row[0] - 8)
                    await db.execute("UPDATE users SET xp = ? WHERE id = ?", (new_xp, referrer_id))
                
                logger.info(f"User {left_user_id} left GC. Deducted 8 XP from referrer {referrer_id}.")
        
        # We can also deduct XP from the user who left
        left_user_cursor = await db.execute("SELECT xp FROM users WHERE id = ?", (left_user_id,))
        left_user_row = await left_user_cursor.fetchone()
        if left_user_row:
            # Deduct heavily or reset XP if they leave
            new_left_xp = max(0, left_user_row[0] - 50)
            await db.execute("UPDATE users SET xp = ? WHERE id = ?", (new_left_xp, left_user_id))
            
        await db.commit()
