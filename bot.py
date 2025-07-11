import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
from dotenv import load_dotenv
import asyncio
import google.generativeai as genai

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def is_allowed_group(update):
    return True  # Allow all groups

# --- AI REPLY ---
async def ai_reply(text):
    if not GEMINI_API_KEY:
        return "AI not available: Gemini API key not set."
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = await asyncio.to_thread(model.generate_content, text)
        if hasattr(response, "text") and response.text:
            return response.text
        else:
            return "Sorry, I couldn't generate a proper reply. Please try again."
    except Exception as e:
        return f"AI error: {e}"

# --- MESSAGE HANDLER ---
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    if not update.message or not update.message.text:
        return

    # Only reply if bot is mentioned in group/supergroup
    if update.effective_chat.type in ["group", "supergroup"]:
        bot_username = (await context.bot.get_me()).username
        mentioned = False
        if update.message.entities:
            for entity in update.message.entities:
                if entity.type == "mention":
                    mention_text = update.message.text[entity.offset:entity.offset+entity.length]
                    if mention_text.lower() == f"@{bot_username.lower()}":
                        mentioned = True
                        break
        if not mentioned:
            return  # Don't reply if not tagged

    await update.message.chat.send_action("typing")
    user_message = update.message.text
    reply = await ai_reply(user_message)
    await update.message.reply_text(reply)

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Hello! I'm an AI-powered chat bot. Tag me in a group or chat with me here to get answers to your questions!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💬 *How to use:*\n- In a group: Tag me (@YourBotUsername) to get an answer.\n- In private chat: Just send your question!\n\nI'm like ChatGPT for Telegram."
    )

# --- MAIN ---
def main():
    load_dotenv()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    logger.info("Gemini AI Bot started. Waiting for events...")
    app.run_polling()

if __name__ == "__main__":
    main() 