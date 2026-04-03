import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import database
from config import ADMIN_IDS

logger = logging.getLogger(__name__)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    try:
        user_id_to_approve = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /approve USER_ID")
        return
        
    db = await database.get_db()
    cursor = await db.execute("SELECT status, referrer_id FROM users WHERE id = ?", (user_id_to_approve,))
    row = await cursor.fetchone()
    
    if not row:
        await update.message.reply_text("User not found in database.")
        return
        
    status, referrer_id = row
    if status == 'approved':
        await update.message.reply_text("User is already approved.")
        return
        
    # Update status to approved
    await db.execute("UPDATE users SET status = 'approved', join_time = CURRENT_TIMESTAMP WHERE id = ?", (user_id_to_approve,))
    
    # If they were referred by someone, record the invite and give referrer XP
    if referrer_id:
        try:
            await db.execute("INSERT INTO invites (referrer_user_id, invited_user_id) VALUES (?, ?)", (referrer_id, user_id_to_approve))
            # Give referrer 8 XP
            ref_cursor = await db.execute("SELECT xp FROM users WHERE id = ?", (referrer_id,))
            ref_row = await ref_cursor.fetchone()
            if ref_row:
                await db.execute("UPDATE users SET xp = ? WHERE id = ?", (ref_row[0] + 8, referrer_id))
        except Exception as e:
            logger.error(f"Error handling referral for {user_id_to_approve}: {e}")
            
    await db.commit()
    
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id_to_approve}"
    
    try:
        await context.bot.send_message(
            chat_id=user_id_to_approve,
            text=f"🎉 Approved!\nHere is your invite link: {invite_link}"
        )
        await update.message.reply_text(f"User {user_id_to_approve} approved and notified.")
    except BadRequest:
        await update.message.reply_text(f"User {user_id_to_approve} approved, but could not send them a message (they might have blocked the bot).")

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    try:
        user_id_to_remove = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /remove USER_ID")
        return
        
    db = await database.get_db()
    # Set status to removed, xp to 0
    await db.execute("UPDATE users SET status = 'removed', xp = 0 WHERE id = ?", (user_id_to_remove,))
    # Mark user's invites as invalid
    await db.execute("UPDATE invites SET status = 'invalid' WHERE referrer_user_id = ?", (user_id_to_remove,))
    await db.commit()
    
    await update.message.reply_text(f"User {user_id_to_remove} has been removed and disqualified.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
        
    message = " ".join(context.args)
    db = await database.get_db()
    cursor = await db.execute("SELECT id FROM users WHERE status != 'removed'")
    users = await cursor.fetchall()
    
    success_count = 0
    for row in users:
        try:
            await context.bot.send_message(chat_id=row[0], text=message)
            success_count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"Broadcast sent to {success_count} users.")

async def end_event_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    await database.set_global('event_active', 'false')
    await update.message.reply_text("🛑 Event has ended! XP and chats are now frozen.")

async def participants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
        
    db = await database.get_db()
    cursor = await db.execute("SELECT count(*) FROM users WHERE status = 'approved'")
    row = await cursor.fetchone()
    count = row[0] if row else 0
    await update.message.reply_text(f"Total Approved Participants: {count}")
