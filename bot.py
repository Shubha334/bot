import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# --- CONFIG ---
# It's better to use environment variables for security on GitHub
BOT_TOKEN = os.getenv("BOT_TOKEN", "8711712077:AAGttnHmlvabk_fNixHK5wTcYI9jPH-EO94")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@AdultVault")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/AdultVault")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check Join Status
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"✅ Welcome! You have joined the channel.")
            return
    except:
        pass

    # Force Join Keyboard
    keyboard = [[InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
                [InlineKeyboardButton("✅ I have Joined", callback_data="check")]]
    
    await update.message.reply_text(
        "❌ **Access Denied!**\n\nPlease join our channel first to use the bot.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check":
        user_id = query.from_user.id
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
            if member.status in ["member", "administrator", "creator"]:
                await query.edit_message_text("✅ **Success!** Bot started.")
            else:
                await query.answer("❌ You still haven't joined!", show_alert=True)
        except:
            await query.answer("❌ Error checking membership.", show_alert=True)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback))

print("Super Simple Bot is running...")
app.run_polling()
