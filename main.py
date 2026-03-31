#!/usr/bin/env python3
"""
Telegram Media Downloader Bot - Somali Language (BULLETPROOF FIX V5)
Downloads media from YouTube, TikTok, Instagram, Facebook, X/Twitter
Features: Dynamic Welcome, Interactive Menu, Broadcast System, Auto-restart
"""

import logging
import re
import os
import sys
import json
import time
import asyncio
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import NetworkError, TimedOut, RetryAfter, Forbidden
from downloader import download_media

# ============================================================
# CONFIGURATION & PERSISTENCE
# ============================================================
# IMPORTANT: Set these environment variables in your hosting provider
TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
OWNER_ID = int(os.environ.get("OWNER_ID", "0")) # Set your Telegram User ID here
DOWNLOAD_DIR = "downloads"
DATA_DIR = "data"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
USERS_FILE = os.path.join(DATA_DIR, "users.txt")
MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
KEEP_ALIVE_PORT = int(os.environ.get("PORT", 8080))
ENABLE_KEEP_ALIVE = os.environ.get("ENABLE_KEEP_ALIVE", "true").lower() == "true"
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# Default configuration
DEFAULT_CONFIG = {
    "welcome_text": (
        "Hey {name} welcome to {botname} you can download social media videos from here 🚀\n\n"
        "📥 Waxaan kaa caawin karaa inaad soo dejiso fiidiyowyada iyo codadka "
        "boggaga sida:\n"
        "• YouTube\n• TikTok\n• Instagram\n• Facebook\n• X (Twitter)\n\n"
        "📌 Sida loo isticmaalo:\n"
        "1️⃣ Ii soo dir xiriiriye (link) bogga aad rabto\n"
        "2️⃣ Dooro inaad ku soo dejiso fiidiyoow ama cod\n"
        "3️⃣ Waan kuu soo diri doonaa file-ka!"
    ),
    "welcome_image": None, # File ID or local path
    "update_channel_url": "https://t.me/YourUpdateChannel",
    "owner_contact_url": "https://t.me/YourUsername" # Replace with your Telegram link
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Ensure all default keys are present
                for key, value in DEFAULT_CONFIG.items():
                    if key not in data:
                        data[key] = value
                return data
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config_to_save):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_to_save, f, indent=4)

# Load global config once
config = load_config()

def add_user(user_id):
    user_id = str(user_id)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write(user_id + "\n")
        return
    
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    
    if user_id not in users:
        with open(USERS_FILE, "a") as f:
            f.write(user_id + "\n")

def get_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return f.read().splitlines()

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ============================================================
# SOMALI MESSAGES
# ============================================================
MSG = {
    "choose": "📥 Fadlan dooro qaabka aad rabto inaad ku soo dejiso:",
    "btn_video": "🎬 Soo deji Fiidiyoow",
    "btn_audio": "🎵 Soo deji Cod",
    "btn_help": "❓ Caawinaad",
    "btn_owner": "👨‍💻 Milkiilaha",
    "btn_update": "📢 Wararka",
    "downloading": "⏳ Waan soo dejinayaa, fadlan sug...",
    "success_video": "✅ Fiidiyowgaaga waa diyaar!",
    "success_audio": "✅ Codkaaga waa diyaar!",
    "failed": "❌ Waan ka xumahay, soo dejintu way guul darreysatay. Fadlan hubi link-ga oo isku day mar kale.",
    "invalid_link": "⚠️ Link-ga aad soo dirtay ma ahan mid la aqoonsan yanay. Fadlan ii soo dir link ka YouTube, TikTok, Instagram, Facebook, ama X.",
    "error": "❌ Qalad ayaa dhacay. Fadlan isku day mar kale.",
    "too_large": "⚠️ File-ku aad buu u weyn yahay (>50MB). Telegram-gu ma oggolaanayo. Waxaan isku dayaa mid yar...",
    "too_large_fail": "❌ File-ku aad buu u weyn yanay oo Telegram-gu ma diri karo. Fadlan isku day link kale.",
    "processing": "🔄 Waan habeynayaa file-ka...",
    "help_text": (
        "📖 *Hagaha Isticmaalka:*\n\n"
        "1. Nuqul ka soo qaado (Copy) link-ga fiidiyowga aad rabto.\n"
        "2. Ku soo dheji (Paste) halkan oo soo dir.\n"
        "3. Dooro 'Fiidiyoow' ama 'Cod'.\n"
        "4. Sug dhowr ilbiriqsi inta uu bot-ku soo dejinayo.\n\n"
        "✅ Waxaan taageernaa: YouTube, TikTok, Instagram, FB, iyo X."
    ),
    "broadcast_start": "📢 Baahinta fariinta waa la bilaabay...",
    "broadcast_done": "✅ Baahinta waa la dhameeyay! Waxee loo diray {success} qof, {fail} qofna way ku guuldareysatay.",
    "not_owner": "❌ Qalad: Amarkan waxaa iska leh milkiilaha bot-ka oo kaliya.",
    "welcome_updated": "✅ Fariinta soo dhaweynta waa la cusbooneysiiyay!",
    "image_updated": "✅ Sawirka soo dhaweynta waa la cusbooneysiiyay!",
    "url_updated": "✅ Link-ga kanaalka waa la cusbooneysiiyay!",
    "owner_url_updated": "✅ Link-ga milkiilaha waa la cusbooneysiiyay!",
}

# Supported URL patterns
SUPPORTED_PATTERNS = [
    r"(https?://)?(www\.)?(youtube\.com|youtu\.be)",
    r"(https?://)?(www\.|vm\.)?tiktok\.com",
    r"(https?://)?(www\.)?instagram\.com",
    r"(https?://)?(www\.)?(facebook\.com|fb\.watch)",
    r"(https?://)?(www\.)?(twitter\.com|x\.com)",
]
URL_REGEX = r"https?://[^\s]+"

def is_supported_url(url: str) -> bool:
    for pattern in SUPPORTED_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def get_main_keyboard():
    # Reload config to get latest URLs
    current_config = load_config()
    keyboard = [
        [InlineKeyboardButton(MSG["btn_help"], callback_data="help")],
        [InlineKeyboardButton(MSG["btn_owner"], url=current_config["owner_contact_url"])],
        [InlineKeyboardButton(MSG["btn_update"], url=current_config["update_channel_url"])]
    ]
    return InlineKeyboardMarkup(keyboard)

# ============================================================
# BOT HANDLERS
# ============================================================
async def start(update: Update, context) -> None:
    user = update.effective_user
    add_user(user.id)
    
    # Reload fresh config
    current_config = load_config()
    welcome_template = current_config.get("welcome_text", DEFAULT_CONFIG["welcome_text"])
    
    # --- ROBUST BOT NAME FETCHING ---
    # Way 1: Use your bot's known name as a fallback
    bot_name = "hurdaay" 
    
    try:
        # Way 2: Try to get it from the bot object
        bot_info = await context.bot.get_me()
        if bot_info and bot_info.first_name:
            bot_name = bot_info.first_name
    except Exception as e:
        logger.error(f"Could not fetch bot name: {e}")
    
    # Get User Name
    user_name = user.first_name or "Macaamiil"
    
    # --- BULLETPROOF REPLACEMENT ---
    # We use a loop and multiple variations to ensure it never misses
    final_text = welcome_template
    
    # Replace {name}
    for tag in ["{name}", "{NAME}", "{Name}"]:
        final_text = final_text.replace(tag, user_name)
        
    # Replace {botname}
    for tag in ["{botname}", "{BOTNAME}", "{BotName}"]:
        final_text = final_text.replace(tag, bot_name)
    
    # Final regex pass just in case of weird spacing or formatting
    final_text = re.sub(r"\{name\}", user_name, final_text, flags=re.IGNORECASE)
    final_text = re.sub(r"\{botname\}", bot_name, final_text, flags=re.IGNORECASE)
    
    reply_markup = get_main_keyboard()
    
    # Send Image if configured
    if current_config.get("welcome_image"):
        try:
            await update.message.reply_photo(
                photo=current_config["welcome_image"],
                caption=final_text,
                reply_markup=reply_markup
            )
            return
        except Exception as e:
            logger.error(f"Error sending welcome photo: {e}")
    
    # Default to text message
    await update.message.reply_text(final_text, reply_markup=reply_markup)

async def handle_message(update: Update, context) -> None:
    if not update.message or not update.message.text:
        return

    text = update.message.text
    match = re.search(URL_REGEX, text)

    if match:
        url = match.group(0)
        if is_supported_url(url):
            context.user_data["current_url"] = url
            keyboard = [
                [InlineKeyboardButton(MSG["btn_video"], callback_data="video")],
                [InlineKeyboardButton(MSG["btn_audio"], callback_data="audio")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(MSG["choose"], reply_markup=reply_markup)
        else:
            await update.message.reply_text(MSG["invalid_link"])
    else:
        # If it's not a URL and not a command, just show welcome/help
        await start(update, context)

async def button_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "help":
        await query.message.reply_text(MSG["help_text"], parse_mode="Markdown")
        return

    url = context.user_data.get("current_url")
    if not url:
        await query.edit_message_text(text=MSG["error"])
        return

    download_type = query.data
    if download_type not in ("video", "audio"):
        return

    await query.edit_message_text(text=MSG["downloading"])

    file_path = None
    try:
        file_path = await asyncio.to_thread(download_media, url, download_type, DOWNLOAD_DIR)

        if not file_path or not os.path.exists(file_path):
            await query.edit_message_text(text=MSG["failed"])
            return

        file_size = os.path.getsize(file_path)

        if file_size > MAX_TELEGRAM_FILE_SIZE:
            await query.edit_message_text(text=MSG["too_large"])
            if download_type == "video":
                os.remove(file_path)
                file_path = await asyncio.to_thread(download_media, url, "video_small", DOWNLOAD_DIR)
                if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) > MAX_TELEGRAM_FILE_SIZE:
                    await query.edit_message_text(text=MSG["too_large_fail"])
                    if file_path and os.path.exists(file_path): os.remove(file_path)
                    return
            else:
                await query.edit_message_text(text=MSG["too_large_fail"])
                os.remove(file_path)
                return

        await query.edit_message_text(text=MSG["processing"])

        chat_id = query.message.chat_id
        with open(file_path, "rb") as f:
            if "video" in download_type:
                await context.bot.send_video(chat_id=chat_id, video=f, caption=MSG["success_video"])
            else:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption=MSG["success_audio"])

        await query.edit_message_text(text="✅ Soo dejinta waa la dhameeyay!")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        await query.edit_message_text(text=MSG["failed"])
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# ============================================================
# OWNER COMMANDS
# ============================================================
async def set_welcome(update: Update, context) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(MSG["not_owner"])
        return
    
    new_text = " ".join(context.args)
    if not new_text:
        await update.message.reply_text("📌 Isticmaalka: /setwelcome [fariinta cusub]\nPlaceholders: {name}, {botname}")
        return
    
    # Reload current config, update welcome_text, and save
    current_config = load_config()
    current_config["welcome_text"] = new_text
    save_config(current_config)
    await update.message.reply_text(MSG["welcome_updated"])

async def set_welcome_image(update: Update, context) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(MSG["not_owner"])
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("📌 Fadlan u jawaab (reply) sawir adigoo isticmaalaya amarka /setimage")
        return
    
    photo_id = update.message.reply_to_message.photo[-1].file_id
    current_config = load_config()
    current_config["welcome_image"] = photo_id
    save_config(current_config)
    await update.message.reply_text(MSG["image_updated"])

async def set_channel(update: Update, context) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(MSG["not_owner"])
        return
    
    if not context.args:
        await update.message.reply_text("📌 Isticmaalka: /setchannel [URL]")
        return
    
    current_config = load_config()
    current_config["update_channel_url"] = context.args[0]
    save_config(current_config)
    await update.message.reply_text(MSG["url_updated"])

async def set_owner_contact(update: Update, context) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(MSG["not_owner"])
        return
    
    if not context.args:
        await update.message.reply_text("📌 Isticmaalka: /setownerlink [URL]")
        return
    
    current_config = load_config()
    current_config["owner_contact_url"] = context.args[0]
    save_config(current_config)
    await update.message.reply_text(MSG["owner_url_updated"])

async def broadcast(update: Update, context) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(MSG["not_owner"])
        return
    
    msg_to_send = " ".join(context.args)
    if not msg_to_send:
        await update.message.reply_text("📌 Isticmaalka: /broadcast [fariinta]")
        return
    
    users = get_users()
    await update.message.reply_text(MSG["broadcast_start"])
    
    success, fail = 0, 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=msg_to_send)
            success += 1
            await asyncio.sleep(0.05) # Avoid flood limits
        except Forbidden:
            fail += 1 # User blocked bot
        except Exception as e:
            logger.error(f"Broadcast failed for {user_id}: {e}")
            fail += 1
            
    await update.message.reply_text(MSG["broadcast_done"].format(success=success, fail=fail))

async def error_handler(update, context) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

# ============================================================
# KEEP-ALIVE WEB SERVER
# ============================================================
def start_keep_alive_server():
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class KeepAliveHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot is running!")
        def log_message(self, format, *args): pass
    server = HTTPServer(("0.0.0.0", KEEP_ALIVE_PORT), KeepAliveHandler)
    server.serve_forever()

# ============================================================
# MAIN RUNNER
# ============================================================
def run_bot():
    while True:
        try:
            if ENABLE_KEEP_ALIVE:
                threading.Thread(target=start_keep_alive_server, daemon=True).start()

            application = Application.builder().token(TOKEN).build()

            # User Handlers
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CallbackQueryHandler(button_callback))
            
            # Owner Handlers
            application.add_handler(CommandHandler("setwelcome", set_welcome))
            application.add_handler(CommandHandler("setimage", set_welcome_image))
            application.add_handler(CommandHandler("setchannel", set_channel))
            application.add_handler(CommandHandler("setownerlink", set_owner_contact))
            application.add_handler(CommandHandler("broadcast", broadcast))
            
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            
            application.add_error_handler(error_handler)

            logger.info("Bot started...")
            application.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
