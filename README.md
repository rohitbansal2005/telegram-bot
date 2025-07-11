# Gemini Telegram AI Bot

A Telegram bot powered by Google Gemini AI (Generative AI) that answers questions and chats with users. Works in both private chats and groups (when tagged). Like ChatGPT, but for Telegram!

## Features
- AI-powered responses using Google Gemini
- Works in private chats and groups (responds when tagged)
- Simple setup and deployment

## Requirements
- Python 3.11.8
- Telegram Bot Token
- Google Gemini API Key

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd hacker-telegram-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root with the following content:
   ```env
   BOT_TOKEN=your-telegram-bot-token
   GEMINI_API_KEY=your-gemini-api-key
   ```

## Usage

- **Start the bot locally:**
  ```bash
  python bot.py
  ```
- **In a group:** Tag the bot (e.g., `@gembotai_bot`) to get a reply.
- **In private chat:** Just send your message.

## Commands
- `/start` — Introduction message
- `/help` — Usage instructions

## Deployment

- **Heroku (or similar):**
  - The included `Procfile` and `runtime.txt` are ready for deployment.
  - Set the required environment variables (`BOT_TOKEN`, `GEMINI_API_KEY`) in your hosting dashboard.
  - The bot will start with `python bot.py`.

## Testing Gemini API
A simple test script is included:
```bash
python gemini_test.py
```

## Dependencies
- `python-telegram-bot`
- `google-generativeai`
- `python-dotenv`

## License
MIT (add your license if different)

---

*Made with ❤️ using Google Gemini and python-telegram-bot.* 
