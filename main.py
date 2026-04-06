import os
import telebot
from flask import Flask, request
from openai import OpenAI

# 1. Load Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
HF_TOKEN = os.environ.get("HF_TOKEN")

# Ensure tokens are provided
if not BOT_TOKEN or not HF_TOKEN:
    raise ValueError("BOT_TOKEN and HF_TOKEN must be set in environment variables.")

# 2. Initialize Telegram Bot and Flask App
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# 3. Initialize OpenAI Client (Pointed to Hugging Face router)
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=HF_TOKEN,
)

# 4. Telegram Bot Handlers
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am an AI assistant powered by DeepSeek. How can I help you today?")

@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    try:
        # Send a "typing..." action to Telegram
        bot.send_chat_action(message.chat.id, 'typing')

        # Call Hugging Face OpenAI-compatible API
        chat_completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-R1:novita",
            messages=[
                {
                    "role": "user",
                    "content": message.text,
                }
            ]
        )
        
        # Extract the reply and send it back to the user
        reply_text = chat_completion.choices[0].message.content
        bot.reply_to(message, reply_text)

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Sorry, I encountered an error while processing your request.")

# 5. Flask Routes for Telegram Webhook
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook_handler():
    """Receives updates from Telegram and passes them to the bot."""
    update_data = request.stream.read().decode('utf-8')
    update = telebot.types.Update.de_json(update_data)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    """A simple health check route for Render."""
    return "Bot is running successfully!", 200

# 6. Webhook Setup
# Render automatically provides the RENDER_EXTERNAL_URL environment variable.
render_url = os.environ.get('RENDER_EXTERNAL_URL')

if render_url:
    # Set the webhook to the Render URL so Telegram knows where to send messages
    bot.remove_webhook()
    bot.set_webhook(url=f"{render_url}/{BOT_TOKEN}")

# 7. Local Testing Fallback
if __name__ == "__main__":
    if not render_url:
        print("Running locally using standard polling...")
        bot.remove_webhook()
        bot.infinity_polling()
    else:
        # Bind to the PORT environment variable provided by Render
        port = int(os.environ.get('PORT', 5000))
        app.run(host="0.0.0.0", port=port)
