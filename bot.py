from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import sqlite3
from datetime import datetime

BOT_TOKEN = "8711712077:AAGttnHmlvabk_fNixHK5wTcYI9jPH-EO94"
CHANNEL = "@AdultVault"
ADMIN_ID = 7146755377  # replace with your Telegram ID

conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    join_date TEXT,
    is_vip INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    media_type TEXT,
    category TEXT
)
""")
conn.commit()

def save_user(user):
    cursor.execute("INSERT OR IGNORE INTO users(user_id, username, join_date) VALUES (?, ?, ?)",
                   (user.id, user.username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

def is_banned(user_id):
    cursor.execute("SELECT banned FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def get_user_data(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

def get_random_media(category):
    cursor.execute("SELECT file_id, media_type FROM media WHERE category=? ORDER BY RANDOM() LIMIT 1", (category,))
    return cursor.fetchone()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    if is_banned(user.id):
        await update.message.reply_text("🚫 You are banned.")
        return

    # Check join channel
    try:
        member = await context.bot.get_chat_member(CHANNEL, user.id)
        if member.status not in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"❌ Join channel first: https://t.me/{CHANNEL.replace('@', '')}")
            return
    except:
        pass # Handle case where bot is not admin in channel

    keyboard = [
        [InlineKeyboardButton("📸 Photos", callback_data="cat_Photos"), InlineKeyboardButton("🎥 Videos", callback_data="cat_Videos")],
        [InlineKeyboardButton("💎 Premium", callback_data="cat_Premium")],
        [InlineKeyboardButton("👤 My Profile", callback_data="my_profile"), InlineKeyboardButton("🆘 Help", callback_data="help")]
    ]

    await update.message.reply_text(
        f"🔥 *Welcome to Adult Vault*\n\nExplore our collections below. VIP members get access to the Premium section!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="users"), InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📁 Add Media", callback_data="add_media")],
        [InlineKeyboardButton("💎 Make VIP", callback_data="make_vip"), InlineKeyboardButton("🆓 Rem VIP", callback_data="remove_vip")],
        [InlineKeyboardButton("🚫 Ban", callback_data="ban"), InlineKeyboardButton("✅ Unban", callback_data="unban")],
        [InlineKeyboardButton("🔍 User Info", callback_data="info")]
    ]

    await update.message.reply_text("🔐 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("cat_"):
        category = data.split("_")[1]
        user = get_user_data(user_id)
        
        if category == "Premium" and not user[3]: # user[3] is is_vip
            await query.message.reply_text("🚫 This section is for VIP members only! Contact Admin to upgrade.")
            return

        media = get_random_media(category)
        if not media:
            await query.message.reply_text("😔 Sorry, no content in this category yet.")
            return

        file_id, media_type = media
        if media_type == "photo":
            await context.bot.send_photo(user_id, file_id, caption=f"✨ Category: {category}")
        elif media_type == "video":
            await context.bot.send_video(user_id, file_id, caption=f"✨ Category: {category}")

    elif data == "my_profile":
        user = get_user_data(user_id)
        status = "💎 VIP" if user[3] else "🆓 Regular"
        text = (
            f"👤 *Your Profile*\n\n"
            f"🆔 ID: `{user[0]}`\n"
            f"📅 Joined: {user[2]}\n"
            f"🌟 Status: {status}\n"
        )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]]))

    elif data == "help":
        await query.edit_message_text("🆘 *How to use*\n\n1. Select a category.\n2. Get random media.\n3. For VIP, contact @Admin.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_start")]]))

    elif data == "back_start":
        keyboard = [
            [InlineKeyboardButton("📸 Photos", callback_data="cat_Photos"), InlineKeyboardButton("🎥 Videos", callback_data="cat_Videos")],
            [InlineKeyboardButton("💎 Premium", callback_data="cat_Premium")],
            [InlineKeyboardButton("👤 My Profile", callback_data="my_profile"), InlineKeyboardButton("🆘 Help", callback_data="help")]
        ]
        await query.edit_message_text("🔥 *Welcome to Adult Vault*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    # Admin actions
    elif update.effective_user.id == ADMIN_ID:
        context.user_data["action"] = data
        if data == "users":
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip=1")
            vip_count = cursor.fetchone()[0]
            await query.edit_message_text(f"📊 Stats:\nTotal Users: {count}\nVIP Users: {vip_count}")
        elif data == "broadcast":
            await query.edit_message_text("📢 Send message to broadcast (Text/Photo/Video):")
        elif data == "ban":
            await query.edit_message_text("🚫 Send user ID to ban:")
        elif data == "unban":
            await query.edit_message_text("✅ Send user ID to unban:")
        elif data == "info":
            await query.edit_message_text("🔍 Send user ID to get info:")
        elif data == "add_media":
            await query.edit_message_text("📁 Send the Photo or Video you want to add:")
        elif data == "make_vip":
            await query.edit_message_text("💎 Send user ID to make VIP:")
        elif data == "remove_vip":
            await query.edit_message_text("🆓 Send user ID to remove VIP:")

    elif data.startswith("setcat_"):
        category = data.split("_")[1]
        file_id = context.user_data.get("pending_file_id")
        media_type = context.user_data.get("pending_media_type")
        
        if file_id and media_type:
            cursor.execute("INSERT INTO media (file_id, media_type, category) VALUES (?, ?, ?)", (file_id, media_type, category))
            conn.commit()
            await query.edit_message_text(f"✅ Media added successfully to {category}!")
            context.user_data["pending_file_id"] = None
            context.user_data["pending_media_type"] = None
            context.user_data["action"] = None
        else:
            await query.edit_message_text("❌ Error: No pending media found.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    action = context.user_data.get("action")
    msg = update.message

    if action == "broadcast":
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        count = 0
        for user in users:
            try:
                await msg.copy(chat_id=user[0])
                count += 1
            except:
                pass
        await msg.reply_text(f"✅ Broadcast sent to {count} users")
        context.user_data["action"] = None

    elif action == "add_media":
        file_id = None
        media_type = None
        
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_type = "photo"
        elif msg.video:
            file_id = msg.video.file_id
            media_type = "video"
            
        if file_id:
            context.user_data["pending_file_id"] = file_id
            context.user_data["pending_media_type"] = media_type
            context.user_data["action"] = "select_category"
            
            keyboard = [
                [InlineKeyboardButton("Photos", callback_data="setcat_Photos"), InlineKeyboardButton("Videos", callback_data="setcat_Videos")],
                [InlineKeyboardButton("Premium", callback_data="setcat_Premium")]
            ]
            await msg.reply_text("✅ Media received! Now select a category:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await msg.reply_text("❌ Please send a Photo or Video.")

    elif action == "ban":
        try:
            user_id = int(msg.text)
            cursor.execute("UPDATE users SET banned=1 WHERE user_id=?", (user_id,))
            conn.commit()
            await msg.reply_text("🚫 User banned")
        except:
            await msg.reply_text("❌ Invalid ID")
        context.user_data["action"] = None

    elif action == "unban":
        try:
            user_id = int(msg.text)
            cursor.execute("UPDATE users SET banned=0 WHERE user_id=?", (user_id,))
            conn.commit()
            await msg.reply_text("✅ User unbanned")
        except:
            await msg.reply_text("❌ Invalid ID")
        context.user_data["action"] = None

    elif action == "make_vip":
        try:
            user_id = int(msg.text)
            cursor.execute("UPDATE users SET is_vip=1 WHERE user_id=?", (user_id,))
            conn.commit()
            await msg.reply_text("💎 User is now VIP")
            try:
                await context.bot.send_message(user_id, "🎉 Congratulations! You have been upgraded to VIP status.")
            except: pass
        except:
            await msg.reply_text("❌ Invalid ID")
        context.user_data["action"] = None

    elif action == "remove_vip":
        try:
            user_id = int(msg.text)
            cursor.execute("UPDATE users SET is_vip=0 WHERE user_id=?", (user_id,))
            conn.commit()
            await msg.reply_text("🆓 VIP status removed")
        except:
            await msg.reply_text("❌ Invalid ID")
        context.user_data["action"] = None

    elif action == "info":
        try:
            user_id = int(msg.text)
            user = get_user_data(user_id)
            if user:
                text = f"ID: `{user[0]}`\nUsername: @{user[1]}\nJoined: {user[2]}\nVIP: {'Yes' if user[3] else 'No'}\nBanned: {'Yes' if user[4] else 'No'}"
                await msg.reply_text(text, parse_mode="Markdown")
            else:
                await msg.reply_text("User not found")
        except:
            await msg.reply_text("❌ Invalid ID")
        context.user_data["action"] = None

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | (filters.TEXT & ~filters.COMMAND), handle_message))

app.run_polling()
