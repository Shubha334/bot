import os
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- CONFIG ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8711712077:AAGttnHmlvabk_fNixHK5wTcYI9jPH-EO94")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@AdultVault")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/AdultVault")
ADMIN_ID = 7146755377
BOT_USERNAME = "AdultVault69bot"

# --- DB SETUP ---
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS media (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, type TEXT)")
conn.commit()

# --- HELPERS ---
async def check_join(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

async def send_content(bot, user_id, media_id):
    cursor.execute("SELECT file_id, type FROM media WHERE id=?", (media_id,))
    res = cursor.fetchone()
    if res:
        file_id, m_type = res
        if m_type == "photo": await bot.send_photo(user_id, file_id, caption="✨ Here is your photo!")
        else: await bot.send_video(user_id, file_id, caption="✨ Here is your video!")
    else:
        await bot.send_message(user_id, "❌ Sorry, this content is no longer available.")

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    media_id = args[0] if args else None

    # Save user to DB
    cursor.execute("INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)", 
                   (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

    if await check_join(context.bot, user_id):
        if media_id:
            await send_content(context.bot, user_id, media_id)
        else:
            await update.message.reply_text("✅ Welcome! Join our channel to get the latest updates.")
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
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")]
    ]
    await update.message.reply_text("🔐 **Admin Panel**\nChoose an action:", 
                                   reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

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
                await query.edit_message_text("✅ Thank you for joining! Sending your content...")
            else:
                await query.edit_message_text("✅ Thank you for joining! Use a link to get content.")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)
            
    elif user_id == ADMIN_ID:
        if data == "admin_add":
            context.user_data["action"] = "add_media"
            await query.edit_message_text("📁 **Upload Mode:** Send the Photo or Video you want to save.", parse_mode="Markdown")
        elif data == "admin_cast":
            context.user_data["action"] = "broadcast"
            await query.edit_message_text("📢 **Broadcast Mode:** Send the message (Text/Photo/Video) you want to send to all users.", parse_mode="Markdown")
        elif data == "admin_stats":
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            await query.edit_message_text(f"📊 **Total Bot Users:** {count}", parse_mode="Markdown")

async def handle_media_or_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    action = context.user_data.get("action")
    msg = update.message

    if action == "add_media":
        if msg.photo or msg.video:
            m_type = "photo" if msg.photo else "video"
            file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id
            cursor.execute("INSERT INTO media (file_id, type) VALUES (?, ?)", (file_id, m_type))
            conn.commit()
            new_id = cursor.lastrowid
            share_link = f"https://t.me/{BOT_USERNAME}?start={new_id}"
            await msg.reply_text(f"✅ **Media Saved!**\n\nLink: `{share_link}`", parse_mode="Markdown")
            context.user_data["action"] = None
        else:
            await msg.reply_text("❌ Please send a Photo or Video.")

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
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.TEXT & ~filters.COMMAND, handle_media_or_text))

print("Admin File Store Bot is running...")
app.run_polling()
