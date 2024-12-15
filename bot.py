import os
import random
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import piexif
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import tempfile

# Dein Bot-Token hier einfügen
TELEGRAM_BOT_TOKEN = '7774391850:AAGzHbtELHP1XSPgbS3XncNfBDMrySMEgEQ'

# Liste der erlaubten Nutzer-IDs
ALLOWED_USERS = [2028801909, 8143592902]

# Zustände des ConversationHandlers
PROCESS_COUNT, REPEAT_COUNT, PHOTO = range(3)

def start_keyboard():
    keyboard = [[InlineKeyboardButton("Start", callback_data='start')]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("type the number of processes you want to apply (1-10). If something not works -> /cancel")
    else:
        await update.message.reply_text("type the number of processes you want to apply (1-10). If something not works -> /cancel")
    return PROCESS_COUNT

async def get_process_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    try:
        process_count = int(update.message.text)
        if process_count < 1 or process_count > 10:
            raise ValueError("Process count out of range")
        context.user_data['process_count'] = process_count
        await update.message.reply_text("type the number of pictures you need. If something not works -> /cancel")
        return REPEAT_COUNT
    except ValueError:
        await update.message.reply_text("send a number between 1 and 10")
        return PROCESS_COUNT

async def get_repeat_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    try:
        repeat_count = int(update.message.text)
        context.user_data['repeat_count'] = repeat_count
        await update.message.reply_text(f"now send me the picture")
        return PHOTO
    except ValueError:
        await update.message.reply_text("send a number")
        return REPEAT_COUNT

def apply_random_processes(image, process_count):
    for _ in range(process_count):
        process = random.choice([
            lambda img: ImageEnhance.Brightness(img).enhance(random.uniform(0.5, 1.5)),
            lambda img: ImageEnhance.Contrast(img).enhance(random.uniform(0.5, 1.5)),
            lambda img: ImageEnhance.Sharpness(img).enhance(random.uniform(0.5, 2.0)),
            lambda img: ImageEnhance.Color(img).enhance(random.uniform(0.5, 1.5)),
            lambda img: img.rotate(random.uniform(-45, 45)),
            lambda img: img.crop((10, 10, img.width - 10, img.height - 10)),
            lambda img: img.filter(ImageFilter.GaussianBlur(random.uniform(0.5, 2.0))),
            lambda img: ImageOps.sepia(img),
            lambda img: ImageOps.grayscale(img),
            lambda img: ImageOps.invert(img)
        ])
        image = process(image)
    return image

def deg_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60) * 3600
    return [(d, 1), (m, 1), (int(s * 100), 100)]

def process_image(image, repeat_count, process_count):
    def random_us_coordinates():
        lat = random.uniform(24.396308, 49.384358)
        lon = random.uniform(-125.0, -66.93457)
        return lat, lon

    images = []
    for i in range(repeat_count):
        img = image.copy()
        img = apply_random_processes(img, process_count)

        try:
            exif_dict = piexif.load(img.info.get("exif", b""))
        except Exception:
            exif_dict = {"Exif": {}, "GPS": {}}

        exif_dict["Exif"] = {}

        lat, lon = random_us_coordinates()
        lat_ref = "N" if lat >= 0 else "S"
        lon_ref = "E" if lon >= 0 else "W"

        exif_dict["GPS"] = {
            piexif.GPSIFD.GPSLatitude: deg_to_dms(abs(lat)),
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLongitude: deg_to_dms(abs(lon)),
            piexif.GPSIFD.GPSLongitudeRef: lon_ref
        }

        new_exif_data = piexif.dump(exif_dict)
        with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
            img.save(temp_file, "jpeg", exif=new_exif_data)
            images.append(temp_file.name)

    return images

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        photo_path = temp_file.name

    with Image.open(photo_path) as img:
        repeat_count = context.user_data.get('repeat_count', 1)
        process_count = context.user_data.get('process_count', 1)
        edited_images = process_image(img, repeat_count, process_count)

        for edited_image in edited_images:
            await update.message.reply_photo(photo=open(edited_image, 'rb'))

    await update.message.reply_text("done. restart with /start.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text(f"ask for permission with ur id: {user_id}")
        return ConversationHandler.END

    await update.message.reply_text("abort mission. restart with /start.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PROCESS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_process_count)],
            REPEAT
        }
