import logging
import json
import os
from telegram import Update, ChatPermissions, Poll
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, PollAnswerHandler
)
from datetime import datetime, timedelta
import time
from collections import defaultdict
from dotenv import load_dotenv
import asyncio
import google.generativeai as genai

# --- CONFIG ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BANNED_WORDS_FILE = "banned_words.txt"
WARNINGS_FILE = "warnings.json"
# For local testing, you can set these in your terminal before running: 
# set BOT_TOKEN=your-telegram-token

# Configure Gemini API from env variable
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    raise ValueError("GEMINI_API_KEY environment variable not set!")

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- DATA FILES ---
def load_banned_words():
    if not os.path.exists(BANNED_WORDS_FILE):
        with open(BANNED_WORDS_FILE, "w") as f:
            f.write("badword\nspam\nabuse")
    with open(BANNED_WORDS_FILE, "r") as f:
        return [w.strip().lower() for w in f if w.strip()]

def load_warnings():
    if not os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "w") as f:
            json.dump({}, f)
    with open(WARNINGS_FILE, "r") as f:
        return json.load(f)

def save_warnings(warnings):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(warnings, f)

BANNED_WORDS = load_banned_words()

# --- GROUP RESTRICTION ---
ALLOWED_GROUP_IDS = [-1002136570924]

def is_allowed_group(update):
    return update.effective_chat.id in ALLOWED_GROUP_IDS

# --- SMART REPLIES ---
def smart_reply(text):
    text = text.lower()
    greetings = ["hello", "hi", "anyone here"]
    if any(greet in text for greet in greetings):
        return "💻 SYSTEM ONLINE: Welcome, coder! Ask me anything..."
    # Coding Q&A
    if "error" in text or "unexpected token" in text:
        return "🛠️ DEBUG MODE: It looks like you're facing a code error. Paste your code and I'll help!"
    if "best laptop" in text:
        return "💻 SYSTEM RECOMMEND: For coding, try MacBook Air M2 or Lenovo ThinkPad X1 Carbon."
    if "dsa roadmap" in text:
        return "📚 DSA ROADMAP: 1. Arrays 2. Linked List 3. Stack/Queue 4. Trees 5. Graphs 6. DP. Practice daily!"
    if "python" in text:
        return "🐍 PYTHON TIP: Use list comprehensions for cleaner code!"
    if "javascript" in text:
        return "🟨 JS TIP: Use === instead of == for strict equality."
    if "ai" in text:
        return "🤖 AI INSIGHT: Start with Python, learn ML basics, then try TensorFlow or PyTorch."
    return None

# --- MODERATION ---
async def handle_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return
    user = update.effective_user
    text = update.message.text.lower()
    for word in BANNED_WORDS:
        if word in text:
            try:
                await update.message.delete()
            except Exception:
                pass
            warnings = load_warnings()
            user_id = str(user.id)
            count = warnings.get(user_id, 0) + 1
            warnings[user_id] = count
            save_warnings(warnings)
            logger.info(f"Warning {count}/3 for user {user_id} ({user.username})")
            if count == 1:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    reply_to_message_id=update.message.message_id,
                    text="⚠️ SYSTEM ALERT: You broke the group rules. This is warning 1/3."
                )
            elif count == 2:
                until = datetime.now() + timedelta(hours=1)
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until
                    )
                except Exception:
                    pass
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔇 USER MUTED: 2/3 violations"
                )
            elif count >= 3:
                try:
                    await context.bot.ban_chat_member(
                        chat_id=update.effective_chat.id,
                        user_id=user.id
                    )
                except Exception:
                    pass
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⛔ USER BANNED: Rule violation limit exceeded."
                )
            return True
    return False

# --- POLL/QUIZ ---
QUIZ_QUESTIONS = [
    {
        "question": "What does HTML stand for?",
        "options": ["Hyper Text Markup Language", "Home Tool Markup Language", "Hyperlinks and Text Markup Language"],
        "correct": 0
    },
    {
        "question": "Which is a Python data type?",
        "options": ["int", "number", "decimal"],
        "correct": 0
    },
    {
        "question": "What is the output of 2 ** 3 in Python?",
        "options": ["6", "8", "9"],
        "correct": 1
    },
    {
        "question": "Which is used for comments in JS?",
        "options": ["// comment", "# comment", "<!-- comment -->"],
        "correct": 0
    },
    {
        "question": "DSA: What is FIFO?",
        "options": ["Stack", "Queue", "Tree"],
        "correct": 1
    }
]

async def start_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Polls only work in groups.")
        return
    for idx, q in enumerate(QUIZ_QUESTIONS):
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Q{idx+1}: {q['question']}",
            options=q["options"],
            type=Poll.QUIZ,
            correct_option_id=q["correct"],
            is_anonymous=False,
            open_period=30
        )
    logger.info(f"Poll started in group {update.effective_chat.id}")

# --- MATERIALS ---
MATERIALS = {
    "python": "https://realpython.com/cheat-sheet-pdf/ (Python Cheat Sheet PDF)",
    "javascript": "https://web.stanford.edu/class/cs142/cheatsheet.pdf (JS Cheat Sheet PDF)",
    "dsa": "https://www.geeksforgeeks.org/printable-dsa-cheat-sheet/ (DSA Sheet)",
    "ai": "https://stanford.edu/~shervine/teaching/cs-229/cheatsheet-supervised-learning.pdf (AI PDF)"
}

AUTO_DELETE_DELAY = 45  # seconds

async def auto_delete_message(context, chat_id, message_id, delay=AUTO_DELETE_DELAY):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.error(f"Auto-delete failed: {e}")

async def send_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        msg = await update.message.reply_text("❌ This bot is private and will now leave this group.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        await context.bot.leave_chat(update.effective_chat.id)
        return
    if len(context.args) == 0:
        msg = await update.message.reply_text("Usage: /material [topic]\nExample: /material python")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        return
    topic = context.args[0].lower()
    material = MATERIALS.get(topic)
    if material:
        msg = await update.message.reply_text(f"📂 MATERIAL [{topic.title()}]: {material}")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
    else:
        msg = await update.message.reply_text("❌ No material found for this topic.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))

# --- HANDLERS ---
async def ai_reply(text):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(text)
        return response.text
    except Exception as e:
        return f"[AI error: {e}]"

# Placeholder for MCQ quiz generation (Gemini logic removed)
async def generate_mcq_questions():
    # Implement quiz question generation using an external service or API key from environment
    # Return a list of dicts: [{"question": ..., "options": [...], "correct": ...}, ...]
    return []

user_message_times = defaultdict(list)  # user_id -> list of message timestamps
SPAM_TIME_WINDOW = 10  # seconds
SPAM_MESSAGE_LIMIT = 5  # max messages allowed in window

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        msg = await update.message.reply_text("❌ This bot is private and will now leave this group.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        await context.bot.leave_chat(update.effective_chat.id)
        return
    if not update.message or not update.message.text:
        return

    # --- MODERATION CHECK (add this) ---
    if await handle_moderation(update, context):
        return

    user_id = update.effective_user.id
    now = time.time()
    user_message_times[user_id] = [t for t in user_message_times[user_id] if now - t < SPAM_TIME_WINDOW]
    user_message_times[user_id].append(now)

    if len(user_message_times[user_id]) > SPAM_MESSAGE_LIMIT:
        msg = await update.message.reply_text("⚠️ SYSTEM ALERT: Please do not spam! This is a warning.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        return  # Don't process further if spam detected

    user_message = update.message.text
    await update.message.chat.send_action("typing")
    reply = await ai_reply(user_message)
    msg = await update.message.reply_text(reply)
    context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))

user_scores = {}

async def start_ai_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        await update.message.reply_text("❌ This bot is private and will now leave this group.")
        await context.bot.leave_chat(update.effective_chat.id)
        return
    global user_scores
    user_scores = {}  # Reset scores for new quiz
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Polls only work in groups.")
        return

    questions = await generate_mcq_questions()
    if not questions:
        await update.message.reply_text("⚠️ AI couldn't generate quiz questions. Try again.")
        return

    context.chat_data["quiz_questions"] = questions
    context.chat_data["quiz_index"] = 0
    context.chat_data["quiz_active"] = True
    context.chat_data["quiz_answers"] = {}

    await send_next_poll(update, context)

async def send_next_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.chat_data.get("quiz_index", 0)
    questions = context.chat_data.get("quiz_questions", [])
    if idx >= len(questions):
        await show_leaderboard(update, context)
        context.chat_data["quiz_active"] = False
        return

    q = questions[idx]
    msg = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=f"Q{idx+1}: {q['question']}",
        options=q["options"],
        type=Poll.QUIZ,
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=30
    )
    context.chat_data["current_poll_id"] = msg.poll.id

async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        return
    if not context.chat_data.get("quiz_active"):
        return
    poll_id = update.poll_answer.poll_id
    user_id = update.poll_answer.user.id
    idx = context.chat_data.get("quiz_index", 0)
    questions = context.chat_data.get("quiz_questions", [])
    if idx >= len(questions):
        return
    correct = questions[idx]["correct"]
    answer = update.poll_answer.option_ids[0] if update.poll_answer.option_ids else None
    if answer is None:
        return
    if user_id not in user_scores:
        user_scores[user_id] = 0
    if answer == correct:
        user_scores[user_id] += 1
    # Next question
    context.chat_data["quiz_index"] = idx + 1
    await send_next_poll(update, context)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not user_scores:
        await update.message.reply_text("No answers received.")
        return
    sorted_scores = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)
    leaderboard = ""
    for i, (uid, score) in enumerate(sorted_scores):
        try:
            user = await context.bot.get_chat(uid)
            name = user.first_name
        except Exception:
            name = str(uid)
        leaderboard += f"{i+1}. {name}: {score} correct\n"
    await update.message.reply_text(f"🏆 Quiz Leaderboard:\n{leaderboard}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        msg = await update.message.reply_text("❌ This bot is private and will now leave this group.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        await context.bot.leave_chat(update.effective_chat.id)
        return
    help_text = (
        "🤖 *HACKER Bot Features:*\n\n"
        "/start - Bot introduction\n"
        "/help - Show this help message\n"
        "/poll - Start a real-time AI coding quiz (5 questions, leaderboard)\n"
        "/material [topic] - Get coding materials (e.g. /material python)\n"
        "\n"
        "💬 *AI Chat*: Just send any message, bot will reply with AI answer.\n"
        "🛡️ *Moderation*: Banned words, spam protection, auto warnings/mute/ban\n"
        "🏆 *Quiz Leaderboard*: See who answered most questions correctly!\n"
        "\n"
        "_Try it in your group!_"
    )
    msg = await update.message.reply_text(help_text, parse_mode="Markdown")
    context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed_group(update):
        msg = await update.message.reply_text("❌ This bot is private and will now leave this group.")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        await context.bot.leave_chat(update.effective_chat.id)
        return
    if update.effective_chat.type not in ["group", "supergroup"]:
        msg = await update.message.reply_text("Add me to a group to use my features!")
        context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))
        return
    msg = await update.message.reply_text(
        "💻 SYSTEM ONLINE: HACKER bot at your service! Ask me anything..."
    )
    context.application.create_task(auto_delete_message(context, msg.chat_id, msg.message_id))

# --- MAIN ---
def main():
    load_dotenv()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("poll", start_ai_poll))
    app.add_handler(CommandHandler("material", send_material))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.add_handler(PollAnswerHandler(poll_answer_handler))
    app.add_handler(CommandHandler("help", help_command))
    logger.info("Gemini AI Bot started. Waiting for events...")
    app.run_polling()

if __name__ == "__main__":
    main() 