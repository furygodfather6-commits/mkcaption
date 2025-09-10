# -*- coding: utf-8 -*-
import logging
import os
import sqlite3
import json
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from flask import Flask, request
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Bot,
    InputFile,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --- Flask App Setup ---
# Render par deploy karne ke liye web server zaroori hai.
app = Flask(__name__)

# --- Basic Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables & Constants ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_FILE = "bot_data.db" # Database file ka naam

# --- Database Management ---
def init_db():
    """Database ko initialize karta hai aur zaroori tables banata hai."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # User sessions ko store karne ke liye table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        user_id INTEGER PRIMARY KEY,
        session_data TEXT NOT NULL
    )
    """)
    # User templates ko store karne ke liye table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS templates (
        template_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        template_name TEXT NOT NULL,
        caption TEXT,
        buttons TEXT
    )
    """)
    conn.commit()
    conn.close()

def get_session(user_id: int):
    """Database se user ka session data nikalta hai."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT session_data FROM sessions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

def save_session(user_id: int, session_data: dict):
    """User ke session data ko database me save ya update karta hai."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO sessions (user_id, session_data) VALUES (?, ?)",
        (user_id, json.dumps(session_data)),
    )
    conn.commit()
    conn.close()

def delete_session(user_id: int):
    """Database se user ka session delete karta hai."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- Bot Helper Functions ---

def get_file_details(message: Message) -> dict | None:
    """Message se file_id, file_type, aur caption nikalta hai."""
    details = {"caption": message.caption or ""}
    file_type, file_id = None, None
    if message.photo:
        file_type, file_id = "photo", message.photo[-1].file_id
    elif message.video:
        file_type, file_id = "video", message.video.file_id
    elif message.document:
        file_type, file_id = "document", message.document.file_id
    elif message.audio:
        file_type, file_id = "audio", message.audio.file_id
    
    if file_type and file_id:
        details.update({"file_type": file_type, "file_id": file_id})
        return details
    return None

def build_main_keyboard(session: dict) -> InlineKeyboardMarkup:
    """Editing ke liye main interactive keyboard banata hai."""
    keyboard = [
        [InlineKeyboardButton("✏️ Caption Edit Karein", callback_data="edit_caption_menu")],
        [InlineKeyboardButton("💅 Text Style Karein", callback_data="style_menu")],
        [InlineKeyboardButton("➕ URL Button Jodein", callback_data="add_button")],
    ]
    if session.get("file_type") == "photo":
        keyboard.append([InlineKeyboardButton("💧 Watermark Lagayein", callback_data="add_watermark")])
    keyboard.extend([
        [InlineKeyboardButton("🔖 Templates", callback_data="templates_menu")],
        [InlineKeyboardButton("✅ Ho Gaya", callback_data="done")],
    ])
    return InlineKeyboardMarkup(keyboard)

async def resend_with_keyboard(context: ContextTypes.DEFAULT_TYPE, session: dict):
    """User ke media ko naye caption aur keyboard ke saath bhejta ya edit karta hai."""
    user_id = session['user_id']
    chat_id = session["chat_id"]
    message_id = session.get("message_id")
    file_id = session["file_id"]
    file_type = session["file_type"]
    caption = session.get("caption", "")
    buttons = session.get("buttons", [])

    dynamic_buttons = [[InlineKeyboardButton(text, url=url) for text, url in buttons]] if buttons else []
    
    reply_markup = build_main_keyboard(session) # Default keyboard
    # Combine dynamic buttons with the static control keyboard
    if dynamic_buttons:
        reply_markup = InlineKeyboardMarkup(dynamic_buttons + reply_markup.inline_keyboard)

    try:
        send_method_map = {
            "photo": context.bot.send_photo, "video": context.bot.send_video,
            "document": context.bot.send_document, "audio": context.bot.send_audio,
        }
        if message_id is None:
            # Watermark ke case me file InputFile object hoga
            file_to_send = session.get("watermarked_file", file_id)
            
            sent_message = await send_method_map[file_type](
                chat_id=chat_id,
                photo=file_to_send if file_type == 'photo' else file_id,
                video=file_id, document=file_id, audio=file_id,
                caption=caption, reply_markup=reply_markup, parse_mode='HTML'
            )
            session["message_id"] = sent_message.message_id
            if "watermarked_file" in session:
                del session["watermarked_file"] # Temp file ko session se hata dein
        else:
            await context.bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id, caption=caption,
                reply_markup=reply_markup, parse_mode='HTML'
            )
        save_session(user_id, session) # Har action ke baad session save karein
    except Exception as e:
        logger.error(f"resend_with_keyboard me error: {e}")
        await context.bot.send_message(chat_id, text=f"Ek error aa gaya hai: {e}\nKripya file dobara bhejein.")
        delete_session(user_id)

# --- Command & Message Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html(
        "👋 **Advanced Caption Editor Bot me aapka swagat hai!**\n\n"
        "Shuru karne ke liye koi bhi photo, video, document, ya audio bhejein. "
        "Mai aapko caption edit karne aur interactive buttons jodne me madad karunga.\n\n"
        "/cancel ka istemal karke aap kabhi bhi editing process rok sakte hain."
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if get_session(user_id):
        await update.message.reply_text("Aap pehle se hi ek editing session me hain. Kripya use poora karein ya /cancel karein.")
        return

    file_details = get_file_details(update.message)
    if not file_details:
        await update.message.reply_text("Maaf kijiye, mai sirf photos, videos, documents, ya audio files process kar sakta hoon.")
        return

    session = {
        "user_id": user_id, "chat_id": update.message.chat_id,
        **file_details, "buttons": [], "state": "awaiting_main_choice", "message_id": None
    }
    save_session(user_id, session)
    await resend_with_keyboard(context, session)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Jab bot user se text input ka intezar kar raha ho, tab is function ko handle karta hai."""
    user_id = update.effective_user.id
    session = get_session(user_id)
    if not session: return

    state = session.get("state")
    text = update.message.text
    
    # Text input ke alag-alag states ko handle karna
    if state == "awaiting_watermark_text":
        await update.message.reply_text("Watermark lagaya ja raha hai, kripya intezar karein...")
        try:
            # File download karna
            file = await context.bot.get_file(session['file_id'])
            file_bytes = await file.download_as_bytearray()
            
            # Watermark lagana
            image_stream = BytesIO(file_bytes)
            img = Image.open(image_stream).convert("RGBA")
            
            txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)
            
            # Font size set karna
            font_size = int(img.width / 15)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()
            
            # Text position
            x, y = int(img.width / 2), int(img.height / 2)
            
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 128), anchor="ms")
            
            out = Image.alpha_composite(img, txt_layer)
            
            # Processed image ko save karna
            final_image_stream = BytesIO()
            out.convert("RGB").save(final_image_stream, format='JPEG')
            final_image_stream.seek(0)
            
            # Nayi file bhejna
            sent_message = await context.bot.send_photo(
                chat_id=session['chat_id'],
                photo=InputFile(final_image_stream, filename="watermarked.jpg"),
                caption=session.get('caption', ''),
                reply_markup=build_main_keyboard(session)
            )
            # Session update karna
            session['file_id'] = sent_message.photo[-1].file_id
            session['message_id'] = sent_message.message_id
            
        except Exception as e:
            logger.error(f"Watermark lagane me error: {e}")
            await update.message.reply_text("Watermark lagane me koi samasya aa gayi.")
    
    elif state == "awaiting_style_selection":
        selected_text = session.pop("selected_text", "")
        if "<b>" in text:
            session["caption"] = session["caption"].replace(selected_text, f"<b>{selected_text}</b>")
        elif "<i>" in text:
            session["caption"] = session["caption"].replace(selected_text, f"<i>{selected_text}</i>")

    session["state"] = "awaiting_main_choice"
    save_session(user_id, session)
    await resend_with_keyboard(context, session)


# --- Callback Query Handler (buttons ke liye) ---

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    session = get_session(user_id)
    if not session:
        await query.edit_message_text("Yeh editing session expire ho gaya hai. Kripya ek nayi file bhejein.")
        return

    action = query.data

    if action == "add_watermark":
        session["state"] = "awaiting_watermark_text"
        save_session(user_id, session)
        await query.message.reply_text("Watermark ke liye text bhejein.")
        return
        
    elif action == "style_menu":
        session["state"] = "awaiting_style_selection"
        save_session(user_id, session)
        await query.message.reply_text("Caption se wo text copy karke bhejein jise aap style karna chahte hain.")
        return
        
    elif action == "done":
        final_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text, url=url) for text, url in session.get("buttons", [])]]
        ) if session.get("buttons") else None
        
        await query.edit_message_reply_markup(reply_markup=final_markup)
        await query.message.reply_text("Sab ho gaya!")
        delete_session(user_id)
        return

    # Baaki actions ke liye keyboard ko resend karna
    await resend_with_keyboard(context, session)

# --- Flask Webhook Route ---
@app.route("/webhook", methods=["POST"])
async def webhook():
    """Telegram se updates receive karne ke liye Webhook endpoint."""
    if request.method == "POST":
        # Bot ko initialize karna
        bot = Bot(token=TOKEN)
        # Application context ke saath update ko process karna
        async with Application.builder().bot(bot).build() as application:
            # Command Handlers
            application.add_handler(CommandHandler("start", start_command))
            # File Handler
            application.add_handler(MessageHandler(
                (filters.PHOTO | filters.VIDEO | filters.DOCUMENT | filters.AUDIO) & ~filters.COMMAND,
                handle_file
            ))
            # Text Input Handler
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
            # Callback Query Handler
            application.add_handler(CallbackQueryHandler(button_callback))

            # Update ko process karna
            update_data = request.get_json(force=True)
            update = Update.de_json(data=update_data, bot=bot)
            await application.process_update(update)
            
            return "ok"
    return "error"

# Health check route
@app.route("/")
def index():
    return "Bot chal raha hai!"

# --- Main Bot Execution ---
if __name__ == "__main__":
    init_db()
    # Yeh hissa sirf local testing ke liye hai, Render gunicorn ka istemal karega.
    # Production me, Gunicorn is file ko import karega aur 'app' object ka istemal karega.
    # Local me chalane ke liye: python caption_editor_bot.py
    # Lekin dhyan rahe, local me webhook kaam nahi karega bina ngrok jaise tool ke.
    logger.info("Flask server local par shuru ho raha hai...")
    app.run(host="0.0.0.ax", port=int(os.environ.get("PORT", 8080)))


