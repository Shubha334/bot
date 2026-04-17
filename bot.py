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
BOT_USERNAME = "AdultVault69bot" # Update this with your bot's username

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

    if await check_join(context.bot, user_id):
        if media_id:
            await send_content(context.bot, user_id, media_id)
        else:
            await update.message.reply_text("✅ Welcome! Send a link to get content.")
    else:
        # Force Join
        context.user_data["pending_id"] = media_id
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ I have Joined", callback_data="check_joined")]]
        await update.message.reply_text("❌ **Join our channel first to access content!**", 
                                       reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def on_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    msg = update.message
    m_type = "photo" if msg.photo else "video"
    file_id = msg.photo[-1].file_id if msg.photo else msg.video.file_id
    
    cursor.execute("INSERT INTO media (file_id, type) VALUES (?, ?)", (file_id, m_type))
    conn.commit()
    new_id = cursor.lastrowid
    
    share_link = f"https://t.me/{BOT_USERNAME}?start={new_id}"
    await msg.reply_text(f"✅ **Media Saved!**\n\nShare this link:\n`{share_link}`", parse_mode="Markdown")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_joined":
        user_id = query.from_user.id
        if await check_join(context.bot, user_id):
            media_id = context.user_data.get("pending_id")
            if media_id:
                await send_content(context.bot, user_id, media_id)
                await query.edit_message_text("✅ Thank you for joining! Sending your content...")
            else:
                await query.edit_message_text("✅ Thank you for joining! Use a link to get content.")
        else:
            await query.answer("❌ You haven't joined yet!", show_alert=True)

# --- APP ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, on_media))

print("File Store Bot is running...")
app.run_polling()
