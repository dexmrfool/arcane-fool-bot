import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
import database
from config import GROUP_CHAT_ID, CHANNEL_ID

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referral_id = args[0] if args else None
    
    db = await database.get_db()
    cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user.id,))
    exists = await cursor.fetchone()
    
    if not exists:
        # Check if referral id is valid
        ref_id_int = None
        if referral_id and referral_id.isdigit():
            ref_cur = await db.execute("SELECT id FROM users WHERE id = ?", (int(referral_id),))
            if await ref_cur.fetchone():
                ref_id_int = int(referral_id)
                
        await db.execute('''
            INSERT INTO users (id, username, first_name, status, xp, invite_count, message_count, referrer_id)
            VALUES (?, ?, ?, 'pending', 0, 0, 0, ?)
        ''', (user.id, user.username, user.first_name, ref_id_int))
        await db.commit()
        
    await update.message.reply_text(
        "🔒 Verification Required\nJoin the official Group Chat and Channel to participate.\n"
        "After joining, type /verify"
    )

async def check_membership(bot, chat_id, user_id):
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ['member', 'administrator', 'creator', 'restricted']
    except BadRequest:
        return False
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check memberships
    in_gc = await check_membership(context.bot, GROUP_CHAT_ID, user_id)
    in_channel = await check_membership(context.bot, CHANNEL_ID, user_id)
    
    if in_gc and in_channel:
        db = await database.get_db()
        await db.execute("UPDATE users SET status = 'pending_approval' WHERE id = ?", (user_id,))
        await db.commit()
        await update.message.reply_text("✅ Verification submitted! Wait for an admin to approve you.")
    else:
        missing = []
        if not in_gc: missing.append("Group Chat")
        if not in_channel: missing.append("Channel")
        await update.message.reply_text(f"❌ You still need to join: {', '.join(missing)}")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = await database.get_db()
    
    # Needs window function or sorting to find rank
    cursor = await db.execute("SELECT id, xp, invite_count, message_count FROM users ORDER BY xp DESC")
    users = await cursor.fetchall()
    
    rank = None
    xp = 0
    invites = 0
    msgs = 0
    
    for i, row in enumerate(users):
        if row[0] == user_id:
            rank = i + 1
            xp = row[1]
            invites = row[2]
            msgs = row[3]
            break
            
    if rank is None:
        await update.message.reply_text("You are not registered. Use /start first.")
        return
        
    await update.message.reply_text(
        f"📊 **Your Profile**\n"
        f"XP: {xp}\n"
        f"Invites: {invites}\n"
        f"Messages: {msgs}\n"
        f"Rank: #{rank}"
    )

async def myxp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = await database.get_db()
    cursor = await db.execute("SELECT xp FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    xp = row[0] if row else 0
    await update.message.reply_text(f"Your XP: {xp}")

async def invites_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = await database.get_db()
    cursor = await db.execute("SELECT count(*) FROM invites WHERE referrer_user_id = ? AND status = 'valid'", (user_id,))
    row = await cursor.fetchone()
    count = row[0] if row else 0
    await update.message.reply_text(f"Your valid invites: {count}")

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await database.get_db()
    cursor = await db.execute("SELECT first_name, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = await cursor.fetchall()
    
    msg = "🏆 **Leaderboard (By XP)**\n\n"
    for i, row in enumerate(rows):
        msg += f"{i+1}. {row[0] or 'User'} - {row[1]} XP\n"
    
    await update.message.reply_text(msg)

async def chatrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = await database.get_db()
    cursor = await db.execute("SELECT first_name, message_count FROM users ORDER BY message_count DESC LIMIT 10")
    rows = await cursor.fetchall()
    
    msg = "💬 **Chat Rank (By Messages)**\n\n"
    for i, row in enumerate(rows):
        msg += f"{i+1}. {row[0] or 'User'} - {row[1]} msgs\n"
    
    await update.message.reply_text(msg)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📜 **Giveaway Rules:**\n- Stay active to earn XP\n- Don't spam\n- Leaving the group will deduct your XP")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = await database.get_db()
    cursor = await db.execute("SELECT status FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    status = row[0] if row else "unregistered"
    await update.message.reply_text(f"Your status: {status.upper()}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **Available Commands**\n"
        "/start - Activate bot and verification\n"
        "/verify - Submit verification\n"
        "/profile - View your full stats\n"
        "/myxp - Check your total XP\n"
        "/invites - View your referral stats\n"
        "/leaderboard - Show top users based on XP\n"
        "/chatrank - Show top users based on chat activity\n"
        "/rules - View giveaway rules\n"
        "/status - Check your verification status\n"
        "/help - Show all available commands"
    )
    await update.message.reply_text(help_text)
