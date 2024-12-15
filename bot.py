import os
import random
from PIL import Image, ImageEnhance
import piexif
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
import tempfile

# Dein Bot-Token hier einfügen
TELEGRAM_BOT_TOKEN = '7774391850:AAGzHbtELHP1XSPgbS3XncNfBDMrySMEgEQ'

# Liste der erlaubten Nutzer-IDs
ALLOWED_USERS = [2028801909, 8143592902]

# Zustände des ConversationHandlers
REPEAT_COUNT, PHOTO = range(2)

def start_keyboard():
    keyboard = [[InlineKeyboardButton("Start", callback_data='start')]]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("type the number of pictures u need. If something not works -> /cancel")
    else:
        await update.message.reply_text("type the number of pictures u need. If something not works -> /cancel")
    return REPEAT_COUNT

async def get_repeat_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        repeat_count = int(update.message.text)
        context.user_data['repeat_count'] = repeat_count
        await update.message.reply_text(f"now send me the picture")
        return PHOTO
    except ValueError:
        await update.message.reply_text("send me a number")
        return REPEAT_COUNT

def deg_to_dms(deg):
    d = int(deg)
    m = int((deg - d) * 60)
    s = (deg - d - m / 60) * 3600
    return [(d, 1), (m, 1), (int(s * 100), 100)]

def process_image(image, repeat_count):
    def random_us_coordinates():
        lat = random.uniform(24.396308, 49.384358)
        lon = random.uniform(-125.0, -66.93457)
        return lat, lon

    images = []
    for i in range(repeat_count):
        img = image.copy()

        brightness_factor = random.uniform(0.95, 1.05)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness_factor)

        contrast_factor = random.uniform(0.98, 1.02)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast_factor)

        sharpness_factor = random.uniform(0.8, 2.0)
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(sharpness_factor)

        max_pixel_change = 6
        new_width = img.width + random.randint(-max_pixel_change, max_pixel_change)
        new_height = img.height + random.randint(-max_pixel_change, max_pixel_change)
        new_width = max(1, new_width)
        new_height = max(1, new_height)
        img = img.resize((new_width, new_height), Image.LANCZOS)

        color_factor = random.uniform(0.9, 1.1)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(color_factor)

        rotation_angle = random.uniform(-0.05, 0.05)
        img = img.rotate(rotation_angle)

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
    photo_file = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(suffix='.jpeg', delete=False) as temp_file:
        await photo_file.download_to_drive(temp_file.name)
        photo_path = temp_file.name

    with Image.open(photo_path) as img:
        repeat_count = context.user_data.get('repeat_count', 1)
        edited_images = process_image(img, repeat_count)

        for edited_image in edited_images:
            await update.message.reply_photo(photo=open(edited_image, 'rb'))

    await update.message.reply_text("done. restart with /start.")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("abort mission. restart with /start.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REPEAT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_repeat_count)],
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(start, pattern='start'))

    application.run_polling()

if __name__ == "__main__":
    main()
