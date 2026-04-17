import os
import sqlite3
import secrets
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8711712077:AAFf8u2vrgak6Nbp2VYQhICCMGVQOeWwfOg")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@AdultVault")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/AdultVault")
ADMIN_ID = 7146755377
BOT_USERNAME = "AdultVault69bot"

# --- DB SETUP (Persistent Path for Railway/VPS) ---
# If you use a Volume on Railway, set DB_PATH to something like "/data/users.db"
DB_PATH = os.getenv("DB_PATH", "users.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, file_id TEXT, type TEXT, name TEXT)")
conn.commit()

# --- HELPERS ---
def generate_unique_id(length=10):
    """Generates a random, hard-to-guess ID."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

async def check_join(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

async def send_content(bot, user_id, media_id):
    cursor.execute("SELECT file_id, type, name FROM media WHERE id=?", (media_id,))
    res = cursor.fetchone()
    if res:
        file_id, m_type, name = res
        caption = f"✨ **File:** {name}"
        if m_type == "photo": await bot.send_photo(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif m_type == "video": await bot.send_video(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif m_type == "audio": await bot.send_audio(user_id, file_id, caption=caption, parse_mode="Markdown")
        elif m_type == "animation": await bot.send_animation(user_id, file_id, caption=caption, parse_mode="Markdown")
        else: await bot.send_document(user_id, file_id, caption=caption, parse_mode="Markdown")
    else:
        await bot.send_message(user_id, "❌ Sorry, this content is no longer available.")

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    media_id = args[0] if args else None

    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", 
                   (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    if await check_join(context.bot, user_id):
        if media_id:
            await send_content(context.bot, user_id, media_id)
        else:
            await update.message.reply_text("✅ **Welcome! (V3 Secure Running)**\n\nUse a link to access content.", parse_mode="Markdown")
    else:
        context.user_data["pending_id"] = media_id
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ I have Joined", callback_data="check_joined")]]
        await update.message.reply_text("❌ **Join our channel first to access content!**", 
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("📁 Add Media", callback_data="admin_add"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_cast")],
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"), InlineKeyboardButton("🛑 Stop Action", callback_data="admin_stop")]
    ]
    await update.message.reply_text("🔐 **Admin Panel**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "check_joined":
        if await check_join(context.bot, user_id):
            media_id = context.user_data.get("pending_id")
            if media_id:
                await send_content(context.bot, user_id, media_id)
                await query.edit_message_text("✅ Access granted! Sending your content...")
            else:
                await query.edit_message_text("✅ Access granted!")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
            
    elif user_id == ADMIN_ID:
        if data == "admin_add":
            context.user_data["action"] = "add_media"
            await query.edit_message_text("📁 **Continuous Upload Mode Enabled!**\nSend media to get secure links.", parse_mode="Markdown")
        elif data == "admin_stop":
            context.user_data["action"] = None
            await query.edit_message_text("✅ All admin actions stopped.", parse_mode="Markdown")
        elif data == "admin_cast":
            context.user_data["action"] = "broadcast"
            await query.edit_message_text("📢 **Broadcast Mode Enabled!**", parse_mode="Markdown")
        elif data == "admin_stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            await query.edit_message_text(f"📊 **Total Bot Users:** {count}", parse_mode="Markdown")

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    action = context.user_data.get("action")
    msg = update.message

    if action == "add_media":
        file_id = None
        m_type = "document"
        name = "File"

        if msg.photo:
            file_id = msg.photo[-1].file_id
            m_type = "photo"
            name = msg.caption if msg.caption else f"Photo_{datetime.now().strftime('%M%S')}"
        elif msg.video:
            file_id = msg.video.file_id
            m_type = "video"
            name = msg.caption if msg.caption else (msg.video.file_name if msg.video.file_name else "Video")
        elif msg.audio:
            file_id = msg.audio.file_id
            m_type = "audio"
            name = msg.caption if msg.caption else (msg.audio.file_name if msg.audio.file_name else "Audio")
        elif msg.animation:
            file_id = msg.animation.file_id
            m_type = "animation"
            name = msg.caption if msg.caption else "GIF"
        elif msg.document:
            file_id = msg.document.file_id
            m_type = "document"
            name = msg.caption if msg.caption else (msg.document.file_name if msg.document.file_name else "File")
        
        if file_id:
            # Generate a truly unique and random ID
            link_id = generate_unique_id(12)
            
            # Save to DB
            cursor.execute("INSERT INTO media (id, file_id, type, name) VALUES (?, ?, ?, ?)", 
                           (link_id, file_id, m_type, name))
            conn.commit()
            
            share_link = f"https://t.me/{BOT_USERNAME}?start={link_id}"
            await msg.reply_text(f"✅ **Saved:** {name}\n🔗 **Secure Link:** `{share_link}`", parse_mode="Markdown")
        else:
            await msg.reply_text("❌ Please send a Photo, Video, Audio, or Document.")

    elif action == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        count = 0
        for user in users:
            try:
                await msg.copy(chat_id=user[0])
                count += 1
            except: pass
        await msg.reply_text(f"✅ Broadcast sent to {count} users.")
        context.user_data["action"] = None

# --- APP ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_all))

print("Final Secure Bot is running...")
app.run_polling()
